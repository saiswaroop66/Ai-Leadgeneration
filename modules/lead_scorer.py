
def calculate_lead_score(lead):
    """Calculate a priority score for a potential business lead."""

    score = 0
    reasons = []

    # A business name is available
    if lead.get("business_name") and lead["business_name"] != "Unknown Business":
        score += 20
        reasons.append("Business name available")

    # A source URL is available
    if lead.get("source_url"):
        score += 10
        reasons.append("Online source available")

    # No official website candidate was found
    status = lead.get("website_status", "").lower()

    if "no official website found" in status:
        score += 40
        reasons.append("Potential website opportunity")

    elif "candidate found" in status:
        score += 5
        reasons.append("Website candidate found - needs verification")

    # Contact information
    if lead.get("phone"):
        score += 15
        reasons.append("Phone number available")

    if lead.get("email"):
        score += 15
        reasons.append("Email address available")

    # Search relevance
    search_score = lead.get("search_score", 0) or 0

    if search_score >= 0.7:
        score += 10
        reasons.append("Strong search relevance")
    elif search_score >= 0.4:
        score += 5
        reasons.append("Moderate search relevance")

    # Keep score between 0 and 100
    score = min(score, 100)

    lead["lead_score"] = score
    lead["lead_priority"] = (
        "High" if score >= 70
        else "Medium" if score >= 40
        else "Low"
    )
    lead["score_reasons"] = reasons

    return lead


def score_all_leads(leads):
    """Calculate scores for all leads and sort them."""

    scored_leads = [
        calculate_lead_score(lead)
        for lead in leads
    ]

    scored_leads.sort(
        key=lambda lead: lead.get("lead_score", 0),
        reverse=True
    )

    return scored_leads
