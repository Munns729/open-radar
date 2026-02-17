import asyncio
import os
import json
from openai import AsyncOpenAI
from playwright.async_api import async_playwright
from src.core.config import settings

client = AsyncOpenAI(
    api_key=settings.moonshot_api_key,
    base_url=settings.kimi_api_base
)

async def ask_agent(html_snippet: str):
    """Ask LLM to find the search input and button selectors."""
    prompt = f"""
    You are a browser automation expert. Analyze the following HTML snippet from a website homepage.
    Your goal is to identify the CSS selectors for:
    1. The main search input field (where user types 'Cybersecurity').
    2. The search submit button (often an icon or button next to the input).

    HTML Snippet:
    {html_snippet}

    Return a JSON object with keys 'input_selector' and 'button_selector'.
    If you are unsure, provide your best guess based on common patterns and classes.
    """
    
    response = await client.chat.completions.create(
        model=settings.kimi_model,
        messages=[
            {"role": "system", "content": "You are a helpful browser automation assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

async def run_agent():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        page = await context.new_page()
        # Manual Evasion
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Agent navigating to GoodFirms...")
        try:
            await page.goto("https://www.goodfirms.co", wait_until="commit", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(5)
            
            # Get simplified HTML for LLM
            # We focus on the search form area to reduce token usage
            # Heuristic: search form is likely near the top or contains 'search'
            full_html = await page.content()
            
            # Simple extraction of relevant chunk
            # Find 'search' keyword and context
            idx = full_html.find("placeholder=\"What are you looking for?\"")
            if idx == -1:
                idx = full_html.find("search")
            
            start = max(0, idx - 1000)
            end = min(len(full_html), idx + 2000)
            snippet = full_html[start:end]
            
            print("Sending HTML snippet to LLM Agent...")
            strategies = await ask_agent(snippet)
            print(f"Agent identified strategies: {strategies}")
            
            input_sel = strategies.get("input_selector")
            btn_sel = strategies.get("button_selector")
            
            if input_sel:
                print(f"Typing into {input_sel}...")
                await page.fill(input_sel, "Cybersecurity France")
                await asyncio.sleep(1)
            
            if btn_sel:
                print(f"Clicking {btn_sel}...")
                # Ensure visible
                try:
                    await page.wait_for_selector(btn_sel, state="visible", timeout=5000)
                    await page.click(btn_sel)
                except:
                    print("Button not visible, trying force click or evaluating JS click...")
                    await page.evaluate(f"document.querySelector('{btn_sel}').click()")
            
            await asyncio.sleep(5)
            print(f"Final URL: {page.url}")
            await page.screenshot(path="data/debug/agent_result.png")
            print("Screenshot saved to data/debug/agent_result.png")
            
        except Exception as e:
            print(f"Agent error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_agent())
