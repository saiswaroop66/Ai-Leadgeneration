
def set_status(lead, status):
    """Keep both approval status fields synchronized."""

    lead["approval_status"] = status
    lead["email_approval"] = status

    return lead


def approve_email(lead):
    """Mark an email draft as approved."""

    if not lead.get("email_draft"):
        return set_status(lead, "No draft available")

    if not lead.get("email"):
        return set_status(lead, "No recipient email")

    return set_status(lead, "Approved")


def reject_email(lead):
    """Reject an email draft."""

    return set_status(lead, "Rejected")


def reset_approval(lead):
    """Reset email approval status."""

    return set_status(lead, "Pending")


def get_pending_emails(leads):
    """Return drafts waiting for approval."""

    return [
        lead for lead in leads
        if lead.get("email_draft")
        and lead.get("approval_status", lead.get("email_approval", "Pending")) == "Pending"
    ]


def get_approved_emails(leads):
    """Return approved drafts with recipient emails."""

    return [
        lead for lead in leads
        if lead.get("approval_status", lead.get("email_approval")) == "Approved"
        and lead.get("email")
        and lead.get("email_draft")
    ]
