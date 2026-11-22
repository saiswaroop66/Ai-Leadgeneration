
import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient

# Load API key
load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")

# Domains that are not official business websites
DIRECTORY_DOMAINS = {
    "justdial.com",
    "zomato.com",
    "swiggy.com",
    "tripadvisor.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "google.com",
    "maps.google.com",
    "yelp.com",
    "magicpin.in",
    "makemytrip.com",
    "booking.com",
    "goibibo.com"
}


def is_directory_website(url):
    """Check whether a URL belongs to a directory or social platform."""

    domain = urlparse(url).netloc.lower()
    domain = domain.removeprefix("www.")

    return any(
        domain == blocked or domain.endswith("." + blocked)
        for blocked in DIRECTORY_DOMAINS
    )


def clean_text(value):
    """Convert text into a simple comparable format."""

    return re.sub(
        r"[^a-z0-9 ]",
        " ",
        value.lower()
    )


def business_name_matches(name, text):
    """Check whether the business name appears in the search evidence."""

    name_words = set(clean_text(name).split())
    text_words = set(clean_text(text).split())

    # Ignore very short words
    name_words = {
        word for word in name_words if len(word) > 2
    }

    if not name_words:
        return False

    matching_words = name_words.intersection(text_words)

    match_ratio = len(matching_words) / len(name_words)

    return match_ratio >= 0.6


def analyze_one_business(client, lead, city):
    """Search for an official website for one business."""

    business_name = lead.get(
        "business_name", "Unknown Business"
    )

    category = lead.get("category", "business")

    query = (
        f'"{business_name}" {category} in {city}, India '
        f"official website contact"
    )

    response = client.search(
        query=query,
        search_depth="basic",
        max_results=5,
        include_answer=False
    )

    possible_websites = []

    for result in response.get("results", []):

        url = (result.get("url") or "").strip()

        if not url:
            continue

        # Ignore directories and social media
        if is_directory_website(url):
            continue

        title = result.get("title", "")
        content = result.get("content", "")

        evidence = title + " " + content

        # Check whether the result actually mentions this business
        if business_name_matches(business_name, evidence):

            possible_websites.append({
                "url": url,
                "title": title,
                "description": content
            })

    if possible_websites:

        best_result = possible_websites[0]

        lead["official_website"] = best_result["url"]

        lead["website_status"] = "Official website candidate found"

        lead["verification_evidence"] = (
            "A non-directory website search result "
            "mentions the business name."
        )

        lead["verification_source"] = best_result["url"]

    else:

        lead["official_website"] = ""

        lead["website_status"] = (
            "Potential lead - no official website found"
        )

        lead["verification_evidence"] = (
            "No matching official website was identified "
            "in the search results. Manual confirmation is needed."
        )

        lead["verification_source"] = ""

    return lead


def analyze_websites(leads, city):
    """Analyze the websites of all discovered businesses."""

    if not API_KEY:
        raise ValueError(
            "Tavily API key is missing in your .env file."
        )

    if not leads:
        return []

    client = TavilyClient(api_key=API_KEY)

    analyzed_leads = []

    for lead in leads:

        try:
            analyzed = analyze_one_business(
                client,
                lead,
                city
            )

            analyzed_leads.append(analyzed)

        except Exception as error:

            lead["official_website"] = ""

            lead["website_status"] = "Manual review"

            lead["verification_evidence"] = str(error)

            lead["verification_source"] = ""

            analyzed_leads.append(lead)

    return analyzed_leads
