
from modules.lead_manager import load_leads, STATUSES


def calculate_analytics():

    leads = load_leads()

    total = len(leads)

    counts = {
        status: 0 for status in STATUSES
    }

    email_count = 0
    phone_count = 0
    website_opportunities = 0

    for lead in leads:

        status = lead.get("crm_status", "New")

        if status in counts:
            counts[status] += 1

        if lead.get("email"):
            email_count += 1

        if lead.get("phone"):
            phone_count += 1

        website_status = str(
            lead.get("website_status", "")
        ).lower()

        if (
            "potential lead" in website_status
            or "no website" in website_status
        ):
            website_opportunities += 1

    contacted = (
        counts["Contacted"]
        + counts["Interested"]
        + counts["Negotiating"]
        + counts["Converted"]
    )

    conversion_rate = (
        (counts["Converted"] / contacted) * 100
        if contacted > 0
        else 0
    )

    return {
        "total": total,
        "counts": counts,
        "emails": email_count,
        "phones": phone_count,
        "website_opportunities": website_opportunities,
        "contacted": contacted,
        "converted": counts["Converted"],
        "conversion_rate": round(conversion_rate, 2)
    }
