# Remote Access Guide

You can access the Investor Radar dashboard from your phone or another computer.

## Option 1: Home Network (WiFi)
**Best for:** Accessing from your phone while at home. Faster speed.

1.  On your main computer, run `run_remote_server.bat`.
2.  Find your computer's local IP address:
    - Open a terminal and type `ipconfig`.
    - Look for **IPv4 Address** (e.g., `192.168.1.15`).
3.  On your phone, open Chrome/Safari and go to:
    `http://192.168.1.15:8000/dashboard`
    *(Replace `192.168.1.15` with your actual IP)*

## Option 2: Public Internet (Anywhere)
**Best for:** Accessing when you are away from home (4G/5G).

1.  On your main computer, run `run_public_access.bat`.
2.  Wait a moment for the **Public URL** to appear in the console.
    - It will look like: `https://a1b2-c3d4.ngrok-free.app`
3.  Open that URL on your phone.

> **Note:** If `run_public_access.bat` fails (ERR_NGROK_4018), you need an auth token:
> 1.  Sign up at [dashboard.ngrok.com](https://dashboard.ngrok.com/signup).
> 2.  Copy your Authtoken.
> 3.  Run in terminal: `ngrok config add-authtoken <YOUR_TOKEN>`
> 4.  Try running `run_public_access.bat` again.

## Remote Control
From the dashboard on your phone, you can:
- **View Stats**: See live discovery numbers.
- **Start Scans**: Use the "Remote Control" panel at the top.
    - Select Sources (e.g., Wikipedia)
    - Enter Target Countries
    - Tap "START SCAN"
