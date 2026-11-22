
from modules.email_templates import get_email_template


def personalize_email(lead):

    business_name = lead.get(
        "business_name",
        "Your Business"
    )

    category = lead.get(
        "category",
        "business"
    )

    website_status = str(
        lead.get("website_status", "")
    ).lower()

    template = get_email_template(category)

    subject = (
        f"Website Development Opportunity for {business_name}"
    )

    if (
        "potential lead" in website_status
        or "no website" in website_status
    ):

        opening = (
            f"We came across {business_name} while researching "
            "businesses in your area. We couldn't find a clearly "
            "verified official website, so we wanted to introduce "
            "our website development services."
        )

    else:

        opening = (
            f"We came across {business_name} and wanted to "
            "introduce our professional website development services."
        )

    body = template["body"].format(
        business_name=business_name
    )

    body = body.replace(
        "I came across your hotel and wanted to introduce our professional website development services.",
        opening
    )

    body = body.replace(
        "I came across your restaurant and wanted to introduce our professional website development services.",
        opening
    )

    return {
        "subject": subject,
        "body": body
    }


def personalize_all_emails(leads):

    for lead in leads:

        draft = personalize_email(lead)

        lead["email_draft"] = draft

        lead["email_subject"] = draft["subject"]

        lead["email_body"] = draft["body"]

    return leads
