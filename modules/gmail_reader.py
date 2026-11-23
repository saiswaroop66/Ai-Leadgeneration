
import os
import json
import re
from pathlib import Path

import streamlit as st

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / "token.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"


def get_gmail_service():
    """Connect to Gmail using Streamlit Cloud secrets or local OAuth files."""

    creds = None

    # 1. Try Streamlit Cloud token secret
    try:
        token_json = st.secrets.get("GMAIL_TOKEN_JSON", None)

        if token_json:
            if isinstance(token_json, str):
                token_info = json.loads(token_json)
            else:
                token_info = dict(token_json)

            creds = Credentials.from_authorized_user_info(
                token_info,
                SCOPES
            )
    except Exception as e:
        print("Could not load Gmail token from Streamlit secrets:", e)

    # 2. Try local token.json
    if not creds and TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(TOKEN_FILE),
                SCOPES
            )
        except Exception as e:
            print("Could not load local token:", e)

    # 3. Refresh expired token
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())

            if TOKEN_FILE.exists():
                TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

        except Exception as e:
            raise Exception(
                f"Gmail token refresh failed: {e}. "
                "Check your Streamlit Cloud Gmail token secret."
            )

    # 4. Local OAuth login if no valid token
    if not creds or not creds.valid:

        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "Gmail credentials.json not found. "
                "For Streamlit Cloud, configure GMAIL_TOKEN_JSON "
                "in App Settings > Secrets."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(
            creds.to_json(),
            encoding="utf-8"
        )

    return build("gmail", "v1", credentials=creds)


def extract_email_body(payload):
    """Extract readable text from a Gmail message."""

    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")

            if mime_type == "text/plain":
                data = part.get("body", {}).get("data")

                if data:
                    import base64
                    body += base64.urlsafe_b64decode(
                        data + "=="
                    ).decode("utf-8", errors="ignore")

            elif "parts" in part:
                body += extract_email_body(part)

    else:
        data = payload.get("body", {}).get("data")

        if data:
            import base64
            body = base64.urlsafe_b64decode(
                data + "=="
            ).decode("utf-8", errors="ignore")

    return body.strip()


def get_message_details(service, message_id):
    """Get one email's details."""

    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    headers = message.get("payload", {}).get("headers", [])

    subject = ""
    sender = ""
    date = ""

    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")

        if name == "subject":
            subject = value

        elif name == "from":
            sender = value

        elif name == "date":
            date = value

    body = extract_email_body(
        message.get("payload", {})
    )

    return {
        "id": message_id,
        "sender": sender,
        "subject": subject,
        "date": date,
        "body": body,
        "snippet": message.get("snippet", "")
    }


def get_recent_emails(max_results=10):
    """
    Fetch recent inbox emails.
    Use only when you explicitly need general inbox messages.
    """

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q="in:inbox",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        try:
            email = get_message_details(
                service,
                msg["id"]
            )
            emails.append(email)

        except Exception as e:
            print("Could not read email:", e)

    return emails


def extract_crm_contacts(leads):
    """Extract valid email addresses from CRM leads."""

    contacts = {}

    if not leads:
        return contacts

    for lead in leads:

        if not isinstance(lead, dict):
            continue

        email = str(lead.get("email", "")).strip().lower()

        business_name = (
            lead.get("business_name")
            or lead.get("name")
            or "CRM Lead"
        )

        if re.fullmatch(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            email
        ):
            contacts[email] = business_name

    return contacts


def get_recent_emails_from_leads(leads, max_results=50):
    """
    Fetch Gmail messages ONLY from email addresses saved in CRM.

    This function does not fetch the entire inbox.
    """

    contacts = extract_crm_contacts(leads)

    if not contacts:
        return []

    service = get_gmail_service()

    emails = []
    seen_ids = set()

    # Gmail supports OR searches using braces.
    addresses = list(contacts.keys())

    # Keep the search query manageable.
    for start in range(0, len(addresses), 20):

        batch = addresses[start:start + 20]

        sender_query = " OR ".join(
            f"from:{address}" for address in batch
        )

        query = f"in:inbox {{{sender_query}}}"

        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])

        for msg in messages:

            message_id = msg.get("id")

            if not message_id or message_id in seen_ids:
                continue

            seen_ids.add(message_id)

            try:
                email = get_message_details(
                    service,
                    message_id
                )

                # Match actual sender against CRM addresses.
                sender_text = email.get("sender", "").lower()

                matched_email = next(
                    (
                        address
                        for address in batch
                        if address in sender_text
                    ),
                    None
                )

                if not matched_email:
                    continue

                email["business_name"] = contacts.get(
                    matched_email,
                    "CRM Lead"
                )

                email["crm_email"] = matched_email

                emails.append(email)

            except Exception as e:
                print("Could not read CRM email:", e)

    return emails

