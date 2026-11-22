
import os
import re
import requests

from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def find_business_contacts(lead):

    business_name = lead.get("business_name", "")
    city = lead.get("address", "Visakhapatnam")

    lead["email"] = lead.get("email", "")
    lead["phone"] = lead.get("phone", "")

    if not TAVILY_API_KEY:
        lead["contact_search_error"] = "TAVILY_API_KEY missing in .env"
        return lead

    query = (
        f'"{business_name}" {city} '
        'official contact phone email'
    )

    try:

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "max_results": 8
            },
            timeout=30
        )

        response.raise_for_status()

        results = response.json().get("results", [])

        emails = []
        phones = []
        sources = []

        for result in results:

            content = (
                str(result.get("title", ""))
                + " "
                + str(result.get("content", ""))
            )

            url = result.get("url", "")

            if url:
                sources.append(url)

            found_emails = re.findall(
                r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
                content
            )

            found_phones = re.findall(
                r'(?:\+91[\s-]?)?[6-9]\d{9}',
                content
            )

            for email in found_emails:
                if email.lower() not in [e.lower() for e in emails]:
                    emails.append(email)

            for phone in found_phones:
                cleaned = re.sub(r'\D', '', phone)

                if len(cleaned) == 12 and cleaned.startswith("91"):
                    cleaned = cleaned[2:]

                if len(cleaned) == 10 and cleaned not in phones:
                    phones.append(cleaned)

        if not lead.get("email") and emails:
            lead["email"] = emails[0]
            lead["email_source"] = sources[0] if sources else "Tavily search"

        if not lead.get("phone") and phones:
            lead["phone"] = phones[0]
            lead["phone_source"] = sources[0] if sources else "Tavily search"

        lead["contact_sources"] = sources
        lead["contact_status"] = (
            "Public contact details found"
            if lead.get("email") or lead.get("phone")
            else "No public contact details found"
        )

    except Exception as error:

        lead["contact_search_error"] = str(error)

    return lead


def find_contacts_for_leads(leads):

    updated_leads = []

    for lead in leads:
        updated_leads.append(
            find_business_contacts(lead)
        )

    return updated_leads
