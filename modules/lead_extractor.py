
from urllib.parse import urlparse


def clean_business_name(name):
    """Clean extra spaces from a business name."""
    if not name:
        return "Unknown Business"

    return " ".join(name.split()).strip()


def extract_leads(search_results):
    """Prepare and clean leads from search results."""

    if not search_results:
        return []

    extracted_leads = []
    seen = set()

    for result in search_results:

        name = clean_business_name(
            result.get("business_name", "")
        )

        category = result.get("category", "business")

        source_url = (
            result.get("source_url")
            or result.get("website")
            or ""
        ).strip()

        if not source_url:
            continue

        # Use the business name and source domain to avoid duplicates
        domain = urlparse(source_url).netloc.lower()
        unique_key = (name.lower(), domain)

        if unique_key in seen:
            continue

        seen.add(unique_key)

        lead = {
            "business_name": name,
            "category": category,
            "source_url": source_url,
            "domain": domain,
            "description": result.get("description", ""),
            "search_score": result.get("search_score", 0),
            "official_website": "",
            "website_status": "Not verified",
            "verification_evidence": "",
            "verification_source": "",
            "phone": "",
            "email": "",
            "address": ""
        }

        extracted_leads.append(lead)

    return extracted_leads
