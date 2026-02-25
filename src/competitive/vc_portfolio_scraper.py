"""
VC Portfolio Scraper

Scrapes portfolio pages from known VC funds; finds or creates companies (universe)
and records holdings in company_vc_holdings.

Two ingestion paths:
  - LLM-assisted (use_llm=True): fetch page text (Playwright or httpx), ask LLM to extract
    company names and descriptions. Works across React/bespoke layouts. Preferred.
  - CSS selector (legacy): httpx or Playwright + CSS selectors. Fragile on modern VC sites.

Called by:
  - scripts/canonical/run_daily_pipeline.py (add vc_portfolio step)
  - or run standalone: python -m src.competitive.vc_portfolio_scraper
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from src.core.database import get_async_db
from src.core.utils import normalize_name, fuzzy_match_company
from src.competitive.database import VCFirmModel
from src.competitive.vc_portfolio_models import CompanyVCHoldingModel
from src.universe.database import CompanyModel

logger = logging.getLogger(__name__)

# Max characters of page text to send to LLM (avoid token limits)
LLM_PAGE_TEXT_MAX_CHARS = 32_000


def _extract_domain(url: Optional[str]) -> Optional[str]:
    if not url or not url.strip():
        return None
    u = url.strip().lower()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        parsed = urlparse(u)
        host = (parsed.netloc or "").strip()
        if host and "." in host:
            return host
    except Exception:
        pass
    return None

# ── Scraping Config per VC ─────────────────────────────────────────────────────
# use_llm=True: fetch page text and extract via LLM (works across React/bespoke layouts). Preferred.
# use_llm=False: legacy CSS selector path (fragile on most modern VC sites).
VC_PORTFOLIO_PAGES = {
    "Expeditions": {"url": "https://expeditionsfund.com/portfolio", "use_llm": True},
    "Vsquared Ventures": {"url": "https://www.vsquared.vc/portfolio", "use_llm": True},
    "OTB Ventures": {"url": "https://www.otb.vc/portfolio", "use_llm": True},
    "IQ Capital": {"url": "https://iqcapital.vc/companies", "use_llm": True},
    "Molten Ventures": {"url": "https://www.moltenventures.com/portfolio", "use_llm": True},
    "Air Street Capital": {"url": "https://www.airstreet.com/portfolio", "use_llm": True},
    "Alpine Space Ventures": {"url": "https://alpinespace.vc/", "use_llm": True},
}

# Dual-use keyword signals to auto-flag companies
DUAL_USE_KEYWORDS = [
    "defense", "defence", "military", "autonomous", "drone", "UAV",
    "surveillance", "intelligence", "cybersecurity", "cyber security",
    "satellite", "ISR", "space", "quantum", "radar", "sonar",
    "government", "NATO", "MoD", "ministry of defence", "dual-use",
    "dual use", "security", "threat detection", "battlefield",
    "robotics", "autonomous systems", "electronic warfare",
]


def _detect_dual_use(text: str) -> tuple[bool, float]:
    """Returns (is_dual_use, confidence 0-1)"""
    text_lower = text.lower()
    hits = sum(1 for kw in DUAL_USE_KEYWORDS if kw.lower() in text_lower)
    if hits == 0:
        return False, 0.0
    confidence = min(hits / 3, 1.0)  # 3+ hits = max confidence
    return True, round(confidence, 2)


def _filter_and_normalize_companies(fund_name: str, companies: list[dict]) -> list[dict]:
    """Apply fund-specific filtering and name normalization."""
    out = []
    seen = set()
    for co in companies:
        name = co["name"]
        href = (co.get("website") or "").lower()

        if fund_name == "Expeditions":
            if "expeditionsfund" in href:
                continue
            name = re.sub(r"\s*Acquired\s*$", "", name, flags=re.IGNORECASE).strip()
        elif fund_name == "IQ Capital":
            name = name.replace("Learn more about ", "").strip()
            if not name or name == "Learn more":
                continue
        elif fund_name == "Alpine Space Ventures":
            if " | " in name:
                name = name.split(" | ")[0].strip()
        elif fund_name == "Molten Ventures":
            if "/portfolio/" not in href:
                continue
            path = urlparse(co.get("website") or "").path.strip("/")
            parts = [p for p in path.split("/") if p]
            if parts and parts[-1] not in ("all", "exits", "new", "spotlight"):
                slug = parts[-1]
                name = slug.replace("-", " ").title()

        if len(name) < 3 or len(name) > 100:
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({**co, "name": name})
    return out[:50]


async def _get_page_text(url: str) -> str:
    """Fetch page and return visible text (Playwright first for JS-rendered sites, else httpx)."""
    text = ""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30_000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            await browser.close()
    except Exception as e:
        logger.debug("Playwright fetch failed for %s: %s; trying httpx", url, e)
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; RADAR/1.0)"})
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
                text = (soup.get_text(separator="\n", strip=True) or "")
        except Exception as e2:
            logger.warning("Page fetch failed for %s: %s", url, e2)
    return (text or "")[:LLM_PAGE_TEXT_MAX_CHARS]


def _parse_llm_companies_json(raw: str) -> list[dict]:
    """Parse LLM response into list of {name, description}. Handles ```json blocks."""
    raw = (raw or "").strip()
    for start in ("```json", "```"):
        if start in raw:
            idx = raw.find(start)
            raw = raw[idx + len(start):].lstrip()
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "companies" in data:
            return data["companies"]
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass
    return []


async def _extract_companies_via_llm(page_text: str, fund_name: str) -> list[dict]:
    """Call LLM to extract portfolio company names and descriptions from page text."""
    from src.core.config import settings
    from openai import AsyncOpenAI

    if not page_text or len(page_text.strip()) < 100:
        logger.warning("Page text too short for LLM extraction")
        return []

    prompt = f"""You are extracting a list of portfolio companies from a VC fund's portfolio page.

Fund name: {fund_name}

Below is the visible text from the portfolio page (may be messy HTML-derived text).

Extract every company name that appears as a portfolio company. For each company include:
- name: exact or best-effort company name (required)
- description: one-line description or sector if visible (optional)

Ignore navigation items, footer links, "View all", "Learn more", and generic text. Only include actual portfolio company names.

Return a JSON array of objects with keys "name" and optionally "description". Example:
[{{"name": "Acme Corp", "description": "Cybersecurity software"}}, {{"name": "Beta Ltd"}}]

Page text:
---
{page_text}
---

Return only the JSON array. No markdown, no explanation."""

    try:
        client = AsyncOpenAI(
            api_key=settings.openai_api_key or "ollama",
            base_url=settings.openai_api_base or "http://localhost:11434/v1",
            timeout=settings.llm_request_timeout,
        )
        model = getattr(settings, "browsing_model", None) or settings.llm_model or "gpt-4o-mini"
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4096,
        )
        raw = response.choices[0].message.content
        items = _parse_llm_companies_json(raw)
        companies = []
        seen_norm = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or "").strip()
            if len(name) < 2 or len(name) > 150:
                continue
            name_norm = normalize_name(name)
            if name_norm in seen_norm:
                continue
            seen_norm.add(name_norm)
            description = (item.get("description") or "").strip()[:500]
            is_dual_use, confidence = _detect_dual_use(name + " " + description)
            companies.append({
                "name": name,
                "website": None,
                "description": description or None,
                "is_dual_use": is_dual_use,
                "dual_use_confidence": confidence,
                "source": "llm",
                "source_url": None,
            })
        logger.info("LLM extracted %d companies for %s", len(companies), fund_name)
        return companies[:80]
    except Exception as e:
        logger.warning("LLM extraction failed for %s: %s", fund_name, e)
        return []


async def _scrape_with_llm(url: str, fund_name: str) -> list[dict]:
    """Fetch portfolio page and extract companies via LLM. Works across React/bespoke layouts."""
    page_text = await _get_page_text(url)
    if not page_text:
        return []
    return await _extract_companies_via_llm(page_text, fund_name)


async def _scrape_with_httpx(url: str, selector: str) -> list[dict]:
    """Scrape portfolio page with httpx (for static sites)."""
    companies = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RADAR/1.0; research)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.select(selector)

        for el in elements[:50]:  # Cap at 50 per fund
            name = el.get_text(strip=True)
            href = el.get("href", "")
            if href and not href.startswith("http"):
                href = urljoin(url, href)

            if len(name) < 3 or len(name) > 100:
                continue

            # Try to get description from nearby text
            parent = el.find_parent(["div", "article", "li"])
            description = ""
            if parent:
                description = parent.get_text(" ", strip=True)[:500]

            is_dual_use, confidence = _detect_dual_use(name + " " + description)

            companies.append({
                "name": name,
                "website": href if href.startswith("http") else None,
                "description": description[:255] if description else None,
                "is_dual_use": is_dual_use,
                "dual_use_confidence": confidence,
                "source": "website",
                "source_url": url,
            })
    except Exception as e:
        logger.warning("httpx scrape failed for %s: %s", url, e)

    return companies


async def _scrape_with_playwright(url: str, selector: str) -> list[dict]:
    """Scrape JS-rendered portfolio page with Playwright."""
    companies = []
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30_000, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            elements = await page.query_selector_all(selector)
            for el in elements[:50]:
                name = (await el.text_content() or "").strip()
                href = await el.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = urljoin(url, href)

                if len(name) < 3 or len(name) > 100:
                    continue

                # Try to grab description from parent
                parent_text = ""
                try:
                    parent = await el.evaluate("el => el.closest('div, article, li')?.textContent")
                    parent_text = (parent or "")[:500]
                except Exception:
                    pass

                is_dual_use, confidence = _detect_dual_use(name + " " + parent_text)

                companies.append({
                    "name": name,
                    "website": href if href.startswith("http") else None,
                    "description": parent_text[:255] if parent_text else None,
                    "is_dual_use": is_dual_use,
                    "dual_use_confidence": confidence,
                    "source": "website",
                    "source_url": url,
                })

            await browser.close()
    except Exception as e:
        logger.warning("Playwright scrape failed for %s: %s", url, e)

    return companies


async def scrape_and_upsert_portfolio(fund_name: str) -> int:
    """
    Scrape one VC fund's portfolio page; find or create companies (universe) and upsert holdings.
    Returns count of new holdings added.
    """
    config = VC_PORTFOLIO_PAGES.get(fund_name)
    if not config:
        logger.info("No scraping config for fund: %s — skipping", fund_name)
        return 0

    if config.get("use_llm", True):
        companies = await _scrape_with_llm(config["url"], fund_name)
    else:
        selector = config.get("selector", "a[href*='/portfolio'], .company-name")
        if config.get("use_playwright", False):
            companies = await _scrape_with_playwright(config["url"], selector)
        else:
            companies = await _scrape_with_httpx(config["url"], selector)

    if not config.get("use_llm", True):
        companies = _filter_and_normalize_companies(fund_name, companies)
    if not companies:
        logger.warning("No companies scraped for %s", fund_name)
        return 0

    async with get_async_db() as session:
        result = await session.execute(select(VCFirmModel).where(VCFirmModel.name == fund_name))
        firm = result.scalar_one_or_none()
        if not firm:
            logger.warning("VC firm '%s' not in DB — run seed_vc_funds.py first", fund_name)
            return 0

        # Load existing companies for matching (name_norm, domain)
        rows = (await session.execute(
            select(CompanyModel.id, CompanyModel.name, CompanyModel.website)
        )).all()
        by_name_norm = {}
        by_domain = {}
        for row in rows:
            cid, name, website = row[0], row[1], row[2]
            if name:
                key = normalize_name(name)
                if key and key not in by_name_norm:
                    by_name_norm[key] = cid
            if website:
                d = _extract_domain(website)
                if d and d not in by_domain:
                    by_domain[d] = cid

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        source_url = config["url"]
        upserted = 0

        for co in companies:
            name_norm = normalize_name(co["name"])
            domain = _extract_domain(co.get("website"))

            company_id = None
            if name_norm and name_norm in by_name_norm:
                company_id = by_name_norm[name_norm]
            elif domain and domain in by_domain:
                company_id = by_domain[domain]

            if company_id is None:
                # Fuzzy match to avoid duplicates (e.g. "Acme Ltd" vs "Acme Limited")
                match = fuzzy_match_company(co["name"], [(r[0], r[1]) for r in rows], threshold=80)
                if match:
                    company_id, _score = match
                    if name_norm:
                        by_name_norm[name_norm] = company_id
                    if domain:
                        by_domain[domain] = company_id
            if company_id is None:
                # Create new company
                sector = co.get("sector_tags")
                sector_str = sector[0] if isinstance(sector, list) and sector else None
                company = CompanyModel(
                    name=co["name"],
                    website=co.get("website"),
                    description=(co.get("description") or "")[:2000] if co.get("description") else None,
                    sector=sector_str,
                    discovered_via="vc_portfolio",
                    is_dual_use=co.get("is_dual_use", False),
                    dual_use_confidence=co.get("dual_use_confidence"),
                )
                session.add(company)
                await session.flush()
                company_id = company.id
                by_name_norm[name_norm] = company_id
                if domain:
                    by_domain[domain] = company_id
            else:
                # Update company VC-related fields from scrape
                comp = (await session.execute(select(CompanyModel).where(CompanyModel.id == company_id))).scalar_one()
                if co.get("description") and not comp.description:
                    comp.description = (co["description"] or "")[:2000]
                if co.get("website") and not comp.website:
                    comp.website = co["website"]
                comp.is_dual_use = comp.is_dual_use or co.get("is_dual_use", False)
                comp.dual_use_confidence = max(comp.dual_use_confidence or 0, co.get("dual_use_confidence", 0))

            # Upsert holding
            existing_hold = await session.execute(
                select(CompanyVCHoldingModel).where(
                    CompanyVCHoldingModel.company_id == company_id,
                    CompanyVCHoldingModel.vc_firm_id == firm.id,
                )
            )
            hold = existing_hold.scalar_one_or_none()
            if hold:
                hold.source_url = source_url
                hold.last_scraped_at = now
            else:
                hold = CompanyVCHoldingModel(
                    company_id=company_id,
                    vc_firm_id=firm.id,
                    source_url=source_url,
                    source=co.get("source", "website"),
                    first_seen_at=now,
                    last_scraped_at=now,
                )
                session.add(hold)
                upserted += 1

        await session.commit()
        logger.info("Scraped %s: %d new holdings upserted", fund_name, upserted)
        return upserted


async def scrape_all_funds() -> dict[str, int]:
    """Scrape all configured VC fund portfolio pages."""
    results = {}
    for fund_name in VC_PORTFOLIO_PAGES:
        count = await scrape_and_upsert_portfolio(fund_name)
        results[fund_name] = count
        await asyncio.sleep(2)  # Be polite
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = asyncio.run(scrape_all_funds())
    for fund, count in results.items():
        print(f"  {fund}: {count} new companies")
