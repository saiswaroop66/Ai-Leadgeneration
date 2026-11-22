
import json
import os

DATA_FOLDER = "data"
DATA_FILE = os.path.join(DATA_FOLDER, "leads.json")

STATUSES = [
    "New",
    "Contacted",
    "Interested",
    "Negotiating",
    "Converted",
    "Not Interested"
]


def load_leads():

    os.makedirs(DATA_FOLDER, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return []


def save_leads(leads):

    os.makedirs(DATA_FOLDER, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(leads, file, indent=4, ensure_ascii=False)


def update_lead_status(business_name, status):

    if status not in STATUSES:
        return False

    leads = load_leads()

    for lead in leads:

        if lead.get("business_name") == business_name:
            lead["crm_status"] = status
            save_leads(leads)
            return True

    return False


def save_new_leads(new_leads):

    existing_leads = load_leads()

    existing_names = {
        lead.get("business_name", "").strip().lower()
        for lead in existing_leads
    }

    for lead in new_leads:

        name = lead.get("business_name", "").strip().lower()

        if name and name not in existing_names:

            lead["crm_status"] = "New"

            existing_leads.append(lead)

            existing_names.add(name)

    save_leads(existing_leads)

    return existing_leads


def get_lead_counts():

    leads = load_leads()

    counts = {
        status: 0 for status in STATUSES
    }

    for lead in leads:

        status = lead.get("crm_status", "New")

        if status in counts:
            counts[status] += 1

    return counts
