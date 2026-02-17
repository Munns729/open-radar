import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.competitive.linkedin_scraper import LinkedInScraper

async def setup_linkedin():
    print("===================================================")
    print("      LinkedIn Authentication Setup Helper")
    print("===================================================")
    print("This script will launch a browser window.")
    print("1. Please log in to your LinkedIn account manually.")
    print("2. Wait until you are redirected to your Feed.")
    print("3. The script will detect the login and save your session.")
    print("===================================================\n")
    
    scraper = LinkedInScraper(headless=False)
    await scraper.setup_session()
    
    try:
        await scraper.login_manual()
        print("\n✅ Session saved successfully!")
        print("You can now use the Relationship Manager features that require LinkedIn.")
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(setup_linkedin())
