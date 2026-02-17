"""
Web Monitor for Competitive Radar.
Detects changes in company websites, focusing on text content and visual diffs.
"""
import asyncio
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
from playwright.async_api import async_playwright

from src.competitive.database import MonitoringTargetModel, DetectedChangeModel
from src.core.database import get_sync_db

logger = logging.getLogger(__name__)

class WebMonitor:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    def _calculate_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def check_target(self, target: MonitoringTargetModel) -> Optional[DetectedChangeModel]:
        """
        Check a single target for changes.
        """
        logger.info(f"Checking {target.company_name} ({target.target_type})...")
        page = await self.context.new_page()
        change = None
        
        try:
            await page.goto(target.url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2) # Stabilize
            
            # Extract content based on type
            if target.selector:
                # Targeted check (e.g. pricing table)
                try:
                    element = page.locator(target.selector).first
                    content = await element.inner_text()
                except:
                    logger.warning(f"Selector {target.selector} not found on {target.url}")
                    content = await page.inner_text("body") # Fallback
            else:
                # Full page check
                content = await page.inner_text("body")
            
            # Hash comparison
            current_hash = self._calculate_hash(content)
            
            if target.last_content_hash and current_hash != target.last_content_hash:
                logger.info(f"CHANGE DETECTED for {target.company_name}")
                
                # Create change record
                # Ideally we compute a diff, for now we save the raw text or a summary
                change = DetectedChangeModel(
                    target_id=target.id,
                    change_type="content_update",
                    description=f"Content changed on {target.target_type} page.",
                    diff_content=content[:500] + "...", # Store snippet for now
                    severity="medium"
                )
                
                # Update target
                target.last_content_hash = current_hash
                target.last_checked = datetime.utcnow()
                
                # Persist
                with get_sync_db() as session:
                    session.add(change)
                    session.merge(target) # Update target state
                
            else:
                logger.info("No change detected.")
                # Update checked time anyway
                target.last_checked = datetime.utcnow()
                with get_sync_db() as session:
                    session.merge(target)
                    target.last_content_hash = current_hash # Update in memory/DB if first run
                
        except Exception as e:
            logger.error(f"Error checking {target.url}: {e}")
        finally:
            await page.close()
            
        return change

    async def run_monitor_loop(self):
        """
        Fetch all active targets and check them.
        """
        with get_sync_db() as session:
            targets = session.query(MonitoringTargetModel).filter_by(is_active=1).all()
        
        logger.info(f"Starting monitor loop for {len(targets)} targets.")
        for t in targets:
            await self.check_target(t)

