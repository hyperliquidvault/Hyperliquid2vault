import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

# Vault page you requested
VAULT_URL = "https://app.hyperliquid.xyz/vaults/0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

# Alert threshold
THRESHOLD = 60000

# Email receiver
EMAIL_TO = "latuihf@gmail.com"

# SMTP credentials from GitHub Secrets
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")



def parse_amount(text):
    """Convert values like 60k, 1.2M, 50000 into numbers."""
    if not text:
        return 0
    t = text.lower().replace(",", "").replace("$", "").replace("usdc", "").strip()
    match = re.match(r"([\d\.]+)([kmb]?)", t)
    if not match:
        return 0
    num, suf = match.groups()
    num = float(num)
    if suf == "k": num *= 1000
    if suf == "m": num *= 1_000_000
    if suf == "b": num *= 1_000_000_000
    return num


def send_email(subject, body):
    """Send email to the alert recipient."""
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def check_positions():
    """Load vault, extract positions, compare threshold, send alert."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(VAULT_URL, timeout=60000)
        page.wait_for_load_state("networkidle")

        rows = page.locator("tr").all()

        alerts = []
        for row in rows:
            txt = row.inner_text().split()
            if len(txt) < 2:
                continue

            coin = txt[0]
            raw_value = txt[-1]
            value = parse_amount(raw_value)

            if value >= THRESHOLD:
                alerts.append((coin, value, raw_value))

        browser.close()

    if alerts:
        body = "Positions exceeding 60,000 USDC:\n\n"
        for coin, value, raw in alerts:
            body += f"{coin}: {value:,.2f} USDC (raw: {raw})\n"

        send_email("Vault Alert - Position Exceeded 60k", body)


if __name__ == "__main__":
    check_positions()
  
