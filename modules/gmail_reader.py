
import base64
import re
import json
from pathlib import Path
from email.utils import getaddresses

import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# --------------------------------------------------
# FILE PATHS AND GMAIL SETTINGS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


# --------------------------------------------------
# CONNECT TO GMAIL
# --------------------------------------------------

def connect_gmail():

    credentials = None

    # 1. Check Streamlit Cloud Secrets
    try:
        token_json = st.secrets.get(
            "GMAIL_TOKEN_JSON",
            None
        )
    except Exception:
        token_json = None

    # 2. Load token from Streamlit Secrets
    if token_json:

        try:

            token_info = json.loads(token_json)

            credentials = Credentials.from_authorized_user_info(
                token_info,
                SCOPES
            )

        except Exception as e:

            raise Exception(
                "Unable to load Gmail token from Streamlit Secrets. "
                "Please check GMAIL_TOKEN_JSON configuration."
            ) from e

    # 3. Local development fallback
    elif TOKEN_FILE.exists():

        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

    # 4. Refresh expired credentials
    if credentials and credentials.expired and credentials.refresh_token:

        credentials.refresh(Request())

        # Save refreshed token locally only
        if not token_json:

            TOKEN_FILE.write_text(
                credentials.to_json(),
                encoding="utf-8"
            )

    # 5. Handle missing or invalid credentials
    if not credentials or not credentials.valid:

        if token_json:

            raise Exception(
                "Gmail authentication failed. "
                "Your Streamlit Gmail token may be expired "
                "or missing a refresh token. "
                "Please reauthorize Gmail."
            )

        if not CREDENTIALS_FILE.exists():

            raise FileNotFoundError(
                "Gmail credentials not configured. "
                "Please add GMAIL_TOKEN_JSON to Streamlit Secrets."
            )

        # Local OAuth login
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES
        )

        credentials = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8"
        )

    # 6. Connect to Gmail API
    service = build(
        "gmail",
        "v1",
        credentials=credentials
    )

    return service


# --------------------------------------------------
# DECODE EMAIL BODY
# --------------------------------------------------

def decode_body(data):

    if not data:
        return ""

    try:

        decoded = base64.urlsafe_b64decode(
            data + "=" * (-len(data) % 4)
        )

        return decoded.decode(
            "utf-8",
            errors="replace"
        )

    except Exception:

        return ""


# --------------------------------------------------
# EXTRACT EMAIL BODY
# --------------------------------------------------

def extract_email_body(payload):

    mime_type = payload.get("mimeType", "")

    body_data = payload.get(
        "body", {}
    ).get("data")

    # Plain text email
    if mime_type == "text/plain" and body_data:

        return decode_body(body_data)

    # Multipart email
    parts = payload.get("parts", [])

    for part in parts:

        result = extract_email_body(part)

        if result:
            return result

    # HTML fallback
    if mime_type == "text/html" and body_data:

        return decode_body(body_data)

    return ""


# --------------------------------------------------
# GET EMAIL ADDRESSES FROM CRM LEADS
# --------------------------------------------------

def extract_crm_contacts(leads):

    contacts = {}

    for lead in leads:

        if not isinstance(lead, dict):
            continue

        raw_email = str(
            lead.get("email", "")
        ).strip()

        if not raw_email:
            continue

        business_name = lead.get(
            "business_name",
            "CRM Business"
        )

        addresses = getaddresses([raw_email])

        for name, address in addresses:

            address = address.strip().lower()

            if re.fullmatch(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                address
            ):

                contacts[address] = business_name

    return contacts


# --------------------------------------------------
# GET COMPLETE EMAIL DETAILS
# --------------------------------------------------

def get_message_details(service, message_id, business_name):

    details = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = details.get("payload", {})

    headers = payload.get("headers", [])

    email_data = {
        "id": message_id,
        "thread_id": details.get("threadId", ""),
        "from": "",
        "to": "",
        "subject": "",
        "date": "",
        "body": extract_email_body(payload),
        "business_name": business_name,
        "internal_date": int(
            details.get("internalDate", 0)
        )
    }

    for header in headers:

        name = header.get("name", "").lower()
        value = header.get("value", "")

        if name == "from":

            email_data["from"] = value

        elif name == "to":

            email_data["to"] = value

        elif name == "subject":

            email_data["subject"] = value

        elif name == "date":

            email_data["date"] = value

    return email_data


# --------------------------------------------------
# FETCH EMAILS ONLY FROM CRM BUSINESSES
# --------------------------------------------------

def get_recent_emails_from_leads(leads, max_results=10):

    """
    Fetch inbox emails only from email addresses
    saved in the CRM.
    """

    contacts = extract_crm_contacts(leads)

    if not contacts:
        return []

    service = connect_gmail()

    collected = {}

    per_sender_limit = max(
        1,
        min(int(max_results), 100)
    )

    for address, business_name in contacts.items():

        query = f"in:inbox from:{address}"

        results = service.users().messages().list(
            userId="me",
            maxResults=per_sender_limit,
            q=query
        ).execute()

        messages = results.get("messages", [])

        for message in messages:

            message_id = message["id"]

            if message_id in collected:
                continue

            try:

                email_data = get_message_details(
                    service,
                    message_id,
                    business_name
                )

                collected[message_id] = email_data

            except Exception:
                continue

    # Sort newest emails first
    emails = sorted(
        collected.values(),
        key=lambda item: item.get("internal_date", 0),
        reverse=True
    )

    return emails[:max_results]


# --------------------------------------------------
# ORIGINAL FUNCTION - GENERAL INBOX EMAILS
# --------------------------------------------------

def get_recent_emails(max_results=10):

    """
    Fetch recent inbox emails without CRM filtering.
    """

    service = connect_gmail()

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q="in:inbox"
    ).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:

        try:

            email_data = get_message_details(
                service,
                message["id"],
                "Unknown Business"
            )

            emails.append(email_data)

        except Exception:
            continue

    return emails
