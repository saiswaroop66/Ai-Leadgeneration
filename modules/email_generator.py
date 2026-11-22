
def generate_email(lead):

    business_name = lead.get(
        "business_name",
        "Your Business"
    )

    category = str(
        lead.get("category", "business")
    ).lower()

    website_status = str(
        lead.get("website_status", "")
    ).lower()

    if "hotel" in category:
        benefit = (
            "showcase your rooms, facilities, pricing, "
            "and make it easier for guests to contact you "
            "or enquire about bookings."
        )

    else:
        benefit = (
            "showcase your menu, food, services, location, "
            "and make it easier for customers to discover "
            "and contact your restaurant."
        )

    if (
        "potential lead" in website_status
        or "no website" in website_status
    ):

        opening = (
            "I was looking for businesses in your area "
            "and came across your business. I couldn't "
            "find a clearly verified official website "
            "for your business."
        )

    else:

        opening = (
            "I came across your business and wanted to "
            "introduce our website development services."
        )

    subject = (
        f"Website Development Opportunity for {business_name}"
    )

    body = f"""Dear {business_name} Team,

I hope you are doing well.

{opening}

We help businesses build modern, professional, and "
mobile-friendly websites that improve their online presence.

A dedicated website could help your business {benefit}

Our services can include:
• Professional website design
• Mobile-friendly layout
• Business information and contact details
• Menu or room/service showcase
• Google Maps and enquiry integration

We would be happy to understand your requirements and "
discuss how we could help your business establish a "
stronger online presence.

Please let us know if you would be interested in a "
brief discussion.

Thank you for your time.

Best regards,
Website Development Team
"""

    return {
        "subject": subject,
        "body": body
    }


def generate_emails(leads):

    updated_leads = []

    for lead in leads:

        draft = generate_email(lead)

        lead["email_draft"] = draft

        lead["email_subject"] = draft["subject"]

        lead["email_body"] = draft["body"]

        updated_leads.append(lead)

    return updated_leads

