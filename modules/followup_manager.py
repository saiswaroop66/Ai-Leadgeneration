
from datetime import datetime, timedelta, timezone

from modules.lead_manager import load_leads, save_leads


# --------------------------------------------------
# FOLLOW-UP SETTINGS
# --------------------------------------------------

INITIAL_FOLLOWUP_DAYS = 3
SECOND_FOLLOWUP_DAYS = 5
MAX_FOLLOWUPS = 2


def current_time():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def format_time(value):
    """Convert a datetime into an ISO timestamp."""
    return value.isoformat()


def parse_time(value):
    """Convert an ISO timestamp into a datetime."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    except (ValueError, TypeError):
        return None


# --------------------------------------------------
# GET OUTREACH HISTORY
# --------------------------------------------------

def get_outreach_history(lead):
    """Return the outreach history of a business."""

    history = lead.get("outreach_history", [])

    if not isinstance(history, list):
        return []

    return history


# --------------------------------------------------
# MARK INITIAL EMAIL AS SENT
# --------------------------------------------------

def mark_initial_email_sent(lead_index):
    """
    Record that the user manually sent the first email.
    """

    leads = load_leads()

    if lead_index < 0 or lead_index >= len(leads):
        raise IndexError("Business not found in CRM.")

    lead = leads[lead_index]

    if not lead.get("email"):
        raise ValueError(
            "This business does not have an email address."
        )

    history = get_outreach_history(lead)

    if any(item.get("stage") == "initial" for item in history):
        raise ValueError(
            "The initial email has already been marked as sent."
        )

    sent_at = current_time()

    history.append({
        "stage": "initial",
        "sent_at": format_time(sent_at)
    })

    lead["outreach_history"] = history
    lead["outreach_status"] = "Contacted"
    lead["reply_received"] = False

    lead["next_followup_at"] = format_time(
        sent_at + timedelta(days=INITIAL_FOLLOWUP_DAYS)
    )

    save_leads(leads)

    return lead


# --------------------------------------------------
# FIND FOLLOW-UP CANDIDATES
# --------------------------------------------------

def get_followup_candidates():
    """
    Return businesses whose next follow-up is due.

    A business is eligible only if:
    - Its initial email was marked as sent.
    - It has not replied.
    - Its follow-up date has arrived.
    - It has fewer than two follow-ups.
    """

    leads = load_leads()

    now = current_time()
    candidates = []

    for index, lead in enumerate(leads):

        if not isinstance(lead, dict):
            continue

        history = get_outreach_history(lead)

        initial_sent = any(
            item.get("stage") == "initial"
            for item in history
        )

        if not initial_sent:
            continue

        if lead.get("reply_received", False):
            continue

        followup_count = sum(
            1 for item in history
            if str(item.get("stage", "")).startswith("followup_")
        )

        if followup_count >= MAX_FOLLOWUPS:
            continue

        next_followup = parse_time(
            lead.get("next_followup_at")
        )

        if not next_followup or now < next_followup:
            continue

        candidates.append({
            "lead_index": index,
            "business_name": lead.get(
                "business_name",
                "Unknown Business"
            ),
            "email": lead.get("email", ""),
            "lead": lead,
            "followup_number": followup_count + 1,
            "due_at": format_time(next_followup),
            "days_overdue": max(
                0,
                (now - next_followup).days
            )
        })

    return candidates


# --------------------------------------------------
# MARK FOLLOW-UP EMAIL AS SENT
# --------------------------------------------------

def mark_followup_sent(lead_index):
    """
    Record that the user manually sent a follow-up.
    """

    leads = load_leads()

    if lead_index < 0 or lead_index >= len(leads):
        raise IndexError("Business not found in CRM.")

    lead = leads[lead_index]

    history = get_outreach_history(lead)

    initial_sent = any(
        item.get("stage") == "initial"
        for item in history
    )

    if not initial_sent:
        raise ValueError(
            "Mark the initial email as sent first."
        )

    if lead.get("reply_received", False):
        raise ValueError(
            "This business has already replied."
        )

    followup_count = sum(
        1 for item in history
        if str(item.get("stage", "")).startswith("followup_")
    )

    if followup_count >= MAX_FOLLOWUPS:
        raise ValueError(
            "Maximum follow-up limit reached."
        )

    sent_at = current_time()

    followup_number = followup_count + 1

    history.append({
        "stage": f"followup_{followup_number}",
        "sent_at": format_time(sent_at)
    })

    lead["outreach_history"] = history

    if followup_number == 1:

        lead["outreach_status"] = "Follow-up 1 Sent"

        lead["next_followup_at"] = format_time(
            sent_at + timedelta(days=SECOND_FOLLOWUP_DAYS)
        )

    else:

        lead["outreach_status"] = "Follow-ups Completed"
        lead["next_followup_at"] = None

    save_leads(leads)

    return lead


# --------------------------------------------------
# MARK REPLY RECEIVED
# --------------------------------------------------

def mark_reply_received(lead_index):
    """Stop follow-ups when a business replies."""

    leads = load_leads()

    if lead_index < 0 or lead_index >= len(leads):
        raise IndexError("Business not found in CRM.")

    lead = leads[lead_index]

    lead["reply_received"] = True
    lead["outreach_status"] = "Replied"
    lead["next_followup_at"] = None

    save_leads(leads)

    return lead


# --------------------------------------------------
# GET FOLLOW-UP SUMMARY
# --------------------------------------------------

def get_followup_summary():

    leads = load_leads()

    total_contacted = 0
    total_replied = 0
    total_followups_sent = 0

    for lead in leads:

        if not isinstance(lead, dict):
            continue

        history = get_outreach_history(lead)

        if any(
            item.get("stage") == "initial"
            for item in history
        ):
            total_contacted += 1

        if lead.get("reply_received", False):
            total_replied += 1

        total_followups_sent += sum(
            1 for item in history
            if str(item.get("stage", "")).startswith("followup_")
        )

    due_count = len(get_followup_candidates())

    return {
        "contacted": total_contacted,
        "replied": total_replied,
        "followups_sent": total_followups_sent,
        "followups_due": due_count
    }
