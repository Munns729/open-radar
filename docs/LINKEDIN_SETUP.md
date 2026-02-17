# LinkedIn Integration Setup

The Relationship Manager module can enrich contact data and find warm intro paths using your personal LinkedIn account.

To enable this feature, you need to perform a one-time authentication step to save your session.

## Prerequisites
- A valid LinkedIn account
- Google Chrome installed (or Chromium)

## One-Time Setup

1. **Run the Setup Script**
   Open your terminal in the project root and run:
   ```powershell
   python scripts/setup_linkedin_auth.py
   ```
   
   *Note: If `playwright` complains about missing browsers, run `playwright install chromium` first.*

2. **Log In Manually**
   - A browser window will open controlled by the script.
   - Enter your LinkedIn credentials and log in.
   - Wait until you are redirected to the main Feed page (`linkedin.com/feed`).

3. **Wait for Confirmation**
   - The script will detect the successful login.
   - It will save your session cookies to `data/linkedin_session/storage_state.json`.
   - The browser window will close automatically.

## Usage
Once authenticated, the `LinkedInEnricher` (used in **Module 5**) will automatically use your saved session to:
- Enrich contact profiles with job titles and locations.
- Calculate connection strengths.
- Find visualization paths in the Network Graph.

You do **not** need to keep the browser open; the system runs in "headless" mode in the background for actual tasks.
