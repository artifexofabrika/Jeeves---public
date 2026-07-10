"""
email_skill.py – Autonomous email secretary for Jeeves (Phi‑3‑mini edition).
Fetches recent emails, classifies, replies to FAQs, forwards personal emails,
and logs every action. Uses message‑ID for deduplication.
"""
import imaplib
import smtplib
import email
import json
import os
import datetime
import re
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import keychain

ACTION_LOG = os.path.expanduser("~/email_actions.json")
YOUR_PROTON_EMAIL = "randy.d.wolf@proton.me"
WELLNESS_LLM_URL = "http://127.0.0.1:8081/v1/chat/completions"

def get_credentials():
    """Return (server, username, password) from the keychain."""
    entry = keychain.load("Email")
    server = entry.get("key", "")
    password = entry.get("secret", "")
    username = entry.get("passphrase", "")
    return server, username, password

def _ask_llm(prompt, max_tokens=50, temperature=0.0):
    """Send a prompt to the wellness/email LLM and return the raw text response."""
    try:
        resp = requests.post(
            WELLNESS_LLM_URL,
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return "ERROR"
    except Exception:
        return "ERROR"

def fetch_recent_emails():
    """Connect to the IMAP server and return a list of recent (last 1 day) email dicts."""
    server, username, password = get_credentials()
    if not server or not username or not password:
        print("Email credentials not found.")
        return []

    mail = imaplib.IMAP4_SSL(server, 993)
    mail.login(username, password)
    mail.select("INBOX")

    since = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f"SINCE {since}")
    if status != "OK" or not messages[0]:
        mail.logout()
        return []

    # Load already-processed message IDs
    processed_ids = set()
    if os.path.exists(ACTION_LOG):
        try:
            with open(ACTION_LOG, 'r') as f:
                for entry in json.load(f):
                    mid = entry.get("message_id", "")
                    if mid:
                        processed_ids.add(mid)
        except:
            pass

    emails = []
    for num in messages[0].split():
        status, data = mail.fetch(num, "(RFC822)")
        if status != "OK":
            continue
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Unique message ID
        msg_id = msg.get("Message-ID", "").strip()
        if not msg_id:
            # fallback: use a combination of subject, sender, and date
            subj = decode_header(msg["Subject"])[0]
            if isinstance(subj, bytes):
                subj = subj.decode('utf-8', errors='replace')
            elif isinstance(subj, str):
                pass
            else:
                subj = str(subj)
            msg_id = f"{subj}-{msg.get('From', 'unknown')}-{msg.get('Date', '')}"

        if msg_id and msg_id in processed_ids:
            continue  # already processed

        # Decode subject
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8", errors="replace")

        sender = msg.get("From", "unknown")

        # Extract body snippet
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")[:1000]
                        break
            if not body:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            import re
                            html = payload.decode("utf-8", errors="replace")
                            body = re.sub(r'<[^>]+>', '', html).strip()[:1000]
                            break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")[:1000]

        emails.append({
            "message_id": msg_id,
            "subject": subject,
            "sender": sender,
            "snippet": body,
        })

    mail.logout()
    return emails

def classify_email(subject, sender, body):
    """Return one of: FAQ, PERSONAL, SPAM, OTHER using the Phi‑3‑mini model."""
    combined = (subject + " " + body).lower()
    # Hard spam keywords – only flag the most obvious junk
    hard_spam = ["buy now", "click here", "winner", "prize", "congratulations",
                 "earn money", "work from home", "casino", "lottery", "viagra",
                 "weight loss", "free trial", "act now", "limited offer"]
    if any(kw in combined for kw in hard_spam):
        return "SPAM"

    # Check for personal address (user name from persona file)
    persona_file = os.path.expanduser("~/jeeves_persona.txt")
    user_name = ""
    if os.path.exists(persona_file):
        try:
            with open(persona_file, "r") as f:
                for line in f:
                    if line.strip().startswith("USER_NAME"):
                        user_name = line.split("=", 1)[-1].strip()
        except:
            pass
    if user_name and user_name.lower() in combined:
        return "PERSONAL"

    prompt = (
        "You are Jeeves, a private AI valet managing an email inbox.\n"
        "Classify the following email into exactly one category:\n"
        "- FAQ: any question about Jeeves (pricing, features, shipping, Indiegogo campaign).\n"
        "- PERSONAL: a message clearly intended for Randy Wolf personally, or someone explicitly asking for a human.\n"
        "- SPAM: unsolicited mass advertising, phishing, malware, get‑rich‑quick schemes.\n"
        "- OTHER: newsletters, receipts, automated notifications, or anything else.\n\n"
        "Reply with ONLY the single word: FAQ, PERSONAL, SPAM, or OTHER.\n\n"
        f"Subject: {subject}\nFrom: {sender}\nBody: {body[:500]}"
    )
    response = _ask_llm(prompt, max_tokens=10)
    for word in ["FAQ", "PERSONAL", "SPAM", "OTHER"]:
        if word in response.upper():
            return word
    return "OTHER"

def generate_faq_reply(subject, sender, body):
    """Generate a polite, persona-driven reply for a FAQ email."""
    prompt = (
        "You are Jeeves, a warm, erudite private AI valet replying on behalf of Randy Wolf.\n"
        "The email is a question about the Jeeves product. Answer it politely, using the information below.\n"
        "Do not make up details. Keep the reply concise, warm, and helpful.\n\n"
        "PRICING: Well‑Wisher $10, Digital Valet $49, Early Adopter Confidant $2,499, "
        "Confidant $2,999, Patron $3,499, Founder's Circle $3,999.\n"
        "SHIPPING: Calculated after campaign. Ships worldwide. First units November 2026.\n"
        "FEATURES: trades crypto & stocks, remembers documents, tracks wellness, manages email, air‑gapped, no subscription.\n"
        "WEBSITE: https://www.artifexofabrika.com\n"
        "INDIEGOGO: https://www.indiegogo.com/projects/jeeves-private-ai-valet\n\n"
        f"Email subject: {subject}\nFrom: {sender}\nBody: {body[:500]}"
    )
    reply = _ask_llm(prompt, max_tokens=200, temperature=0.5)
    return reply if reply != "ERROR" else None

def log_action(email_data, action, details=""):
    """Append an action to the email log."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "message_id": email_data.get("message_id", ""),
        "subject": email_data.get("subject", ""),
        "sender": email_data.get("sender", ""),
        "action": action,
        "details": details,
    }
    log = []
    if os.path.exists(ACTION_LOG):
        try:
            with open(ACTION_LOG, "r") as f:
                log = json.load(f)
        except:
            log = []
    log.append(entry)
    with open(ACTION_LOG, "w") as f:
        json.dump(log, f, indent=2)

def send_reply(to_address, subject, reply_body):
    """Send a reply via SMTP."""
    server, username, password = get_credentials()
    msg = MIMEMultipart()
    msg["From"] = username
    msg["To"] = to_address
    msg["Subject"] = "Re: " + subject
    msg.attach(MIMEText(reply_body, "plain"))
    try:
        with smtplib.SMTP_SSL(server, 465) as smtp:
            smtp.login(username, password)
            smtp.sendmail(username, to_address, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send reply: {e}")
        return False

def forward_to_proton(email_data):
    """Forward a full email to your Proton address."""
    server, username, password = get_credentials()
    msg = MIMEMultipart()
    msg["From"] = username
    msg["To"] = YOUR_PROTON_EMAIL
    msg["Subject"] = "[Jeeves] Needs your attention: " + email_data.get("subject", "No subject")
    body = f"From: {email_data.get('sender', 'unknown')}\nSubject: {email_data.get('subject', '')}\n\n{email_data.get('snippet', '')}"
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL(server, 465) as smtp:
            smtp.login(username, password)
            smtp.sendmail(username, YOUR_PROTON_EMAIL, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to forward email: {e}")
        return False

def process_inbox():
    """Fetch recent emails, classify, reply/forward/log."""
    emails = fetch_recent_emails()
    if not emails:
        print("No new emails to process.")
        return

    print(f"Processing {len(emails)} email(s)...")
    for email_data in emails:
        subject = email_data["subject"]
        sender = email_data["sender"]
        body = email_data["snippet"]

        category = classify_email(subject, sender, body)
        print(f" - {subject[:60]}... → {category}")

        if category == "SPAM":
            log_action(email_data, "DELETED", "Classified as spam")
        elif category == "FAQ":
            reply = generate_faq_reply(subject, sender, body)
            if reply:
                if send_reply(sender, subject, reply):
                    log_action(email_data, "REPLIED", reply[:100])
                else:
                    log_action(email_data, "REPLY_FAILED", "SMTP error")
            else:
                log_action(email_data, "REPLY_FAILED", "LLM generation failed")
        elif category == "PERSONAL":
            if forward_to_proton(email_data):
                log_action(email_data, "FORWARDED", "Sent to Proton for review")
            else:
                log_action(email_data, "FORWARD_FAILED", "SMTP error")
        else:  # OTHER
            log_action(email_data, "FILED", "No action taken")

    print(f"Done. Actions logged to {ACTION_LOG}")

if __name__ == "__main__":
    process_inbox()
