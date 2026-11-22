
import streamlit as st
import pandas as pd
from urllib.parse import urlencode

# ==================================================
# IMPORT MODULES
# ==================================================

from modules.search_engine import search_businesses
from modules.contact_finder import find_contacts_for_leads
from modules.website_analyzer import analyze_websites
from modules.lead_scorer import score_all_leads

from modules.lead_manager import (
    load_leads,
    save_leads,
    save_new_leads,
)

from modules.crm_dashboard import show_crm_dashboard
from modules.email_personalizer import personalize_email
from modules.analytics_charts import show_analytics_dashboard
from modules.gmail_reader import get_recent_emails
from modules.ollama_ai import generate_email_reply
from modules.followup_dashboard import show_followup_dashboard


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="LEADGEN AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================================================
# BUSINESS FILTERING
# ==================================================

EXCLUDED_NAME_WORDS = [
    "hostel",
    "lodge",
    "guest house",
    "guesthouse",
    "motel",
    "cafe",
    "café",
    "tea time",
    "tiffin",
    "parlor",
    "parlour",
    "food stall",
]


def is_valid_business(lead):
    """Allow only proper hotel and restaurant place listings."""

    name = str(lead.get("business_name", "")).strip()
    category = str(lead.get("category", "")).strip().lower()
    source = str(lead.get("data_source", "")).strip().lower()

    if not name:
        return False

    if category not in ["hotels", "hotel", "restaurants", "restaurant"]:
        return False

    if source and source != "geoapify":
        return False

    name_lower = name.lower()

    for word in EXCLUDED_NAME_WORDS:
        if word in name_lower:
            return False

    return True


def filter_businesses(leads):
    """Remove non-business results and duplicate place listings."""

    filtered = []
    seen = set()

    for lead in leads:

        if not isinstance(lead, dict):
            continue

        if not is_valid_business(lead):
            continue

        place_id = str(lead.get("place_id", "")).strip()

        if place_id:
            unique_key = place_id.lower()
        else:
            unique_key = (
                str(lead.get("business_name", "")).strip().lower()
                + "|"
                + str(lead.get("address", "")).strip().lower()
            )

        if unique_key in seen:
            continue

        seen.add(unique_key)
        filtered.append(lead)

    return filtered


def restore_original_business_names(updated_leads, original_leads):
    """Protect original Geoapify business names during enrichment."""

    original_by_id = {
        str(lead.get("place_id")): lead
        for lead in original_leads
        if lead.get("place_id")
    }

    restored = []

    for index, lead in enumerate(updated_leads):

        if not isinstance(lead, dict):
            continue

        place_id = str(lead.get("place_id", ""))
        original = original_by_id.get(place_id)

        if original is None and index < len(original_leads):
            original = original_leads[index]

        if original:
            lead["business_name"] = original.get(
                "business_name",
                lead.get("business_name", "")
            )
            lead["category"] = original.get(
                "category",
                lead.get("category", "")
            )
            lead["data_source"] = original.get(
                "data_source",
                lead.get("data_source", "Geoapify")
            )

        restored.append(lead)

    return restored


# ==================================================
# DASHBOARD STATISTICS
# ==================================================

def get_dashboard_data():

    leads = load_leads()

    total = len(leads)

    emails = sum(
        1 for lead in leads if lead.get("email")
    )

    phones = sum(
        1 for lead in leads if lead.get("phone")
    )

    opportunities = sum(
        1 for lead in leads
        if (
            "potential lead" in str(
                lead.get("website_status", "")
            ).lower()
            or "no website" in str(
                lead.get("website_status", "")
            ).lower()
        )
    )

    return total, emails, phones, opportunities


# ==================================================
# EMAIL VARIATIONS
# ==================================================

def get_email_variant(lead, variant_number):

    draft = personalize_email(lead)

    business_name = lead.get(
        "business_name", "your business"
    )

    category = str(
        lead.get("category", "")
    ).lower()

    website_status = str(
        lead.get("website_status", "")
    ).lower()

    if "hotel" in category:
        business_type = "hotel"
    else:
        business_type = "restaurant"

    if (
        "potential lead" in website_status
        or "no website" in website_status
    ):

        openings = [
            f"While researching local businesses, we came across {business_name}. We couldn't find a clearly verified official website and wanted to introduce our website development services.",

            f"We recently discovered {business_name} while exploring local {business_type}s. We would love to help strengthen your online presence with a professional website.",

            f"We noticed {business_name} while researching businesses in the area. A dedicated website could help more customers discover your business and contact you.",

            f"We are reaching out because {business_name} may benefit from a modern online presence. We would be happy to discuss a website solution suited to your business."
        ]

    else:

        openings = [
            f"We recently came across {business_name} and wanted to introduce our professional website development services.",

            f"We discovered {business_name} while researching local businesses and thought our website development services might be useful to your team.",

            f"We are reaching out to introduce our website development services and explore how we could support {business_name}'s online presence.",

            f"We would love to help {business_name} improve its online presence with a professional and mobile-friendly website."
        ]

    opening = openings[variant_number % len(openings)]

    lines = draft["body"].splitlines()

    for i, line in enumerate(lines):

        if (
            line.startswith("I came across")
            or line.startswith("We came across")
            or line.startswith("We recently")
            or line.startswith("We noticed")
            or line.startswith("We are reaching")
        ):
            lines[i] = opening
            break

    else:

        if len(lines) > 2:
            lines[2] = opening

    draft["body"] = "\n".join(lines)

    return draft


# ==================================================
# EMAIL REGENERATION
# ==================================================

def regenerate_email_callback(index):

    leads = load_leads()

    if index >= len(leads):
        return

    lead = leads[index]

    variant_number = int(
        lead.get("_email_variant", 0)
    ) + 1

    draft = get_email_variant(
        lead,
        variant_number
    )

    lead["_email_variant"] = variant_number

    lead["email_draft"] = draft
    lead["email_subject"] = draft["subject"]
    lead["email_body"] = draft["body"]

    save_leads(leads)

    st.session_state[f"email_subject_{index}"] = draft["subject"]
    st.session_state[f"email_body_{index}"] = draft["body"]

    st.session_state["email_regenerated"] = True


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

st.sidebar.title("🚀 LEADGEN AI")

st.sidebar.caption(
    "Smart Business Lead Generation Platform"
)

st.sidebar.divider()

pages = [
    "🏠 Home",
    "🔎 Find Leads",
    "📋 CRM Management",
    "✉️ AI Email Studio",
    "📬 AI Reply Handler",
    "📨 Follow-up Automation",
    "📊 Analytics"
]

if "selected_page" in st.session_state:

    default_index = (
        pages.index(st.session_state["selected_page"])
        if st.session_state["selected_page"] in pages
        else 0
    )

    del st.session_state["selected_page"]

else:
    default_index = 0


page = st.sidebar.radio(
    "NAVIGATION",
    pages,
    index=default_index
)

st.sidebar.divider()

st.sidebar.info(
    "Discover Businesses | Find Opportunities | Grow Your Business"
)

st.sidebar.caption("LEADGEN AI © 2026")


# ==================================================
# HOME PAGE
# ==================================================

if page == "🏠 Home":

    st.title("🚀 LEADGEN AI")

    st.subheader(
        "Turn Business Data Into Real Opportunities."
    )

    st.write(
        "Your intelligent business lead generation platform. "
        "Discover hotels and restaurants, identify website opportunities, "
        "find public business contacts, and manage your outreach."
    )

    st.divider()

    with st.container(border=True):

        st.markdown("## 👋 Welcome to LEADGEN AI")

        st.write(
            "Find businesses that could benefit from a professional website. "
            "Manage your leads, prepare personalized emails, and track your "
            "business growth from one place."
        )

        st.info(
            "🎯 Current focus: Discovering hotels and restaurants "
            "in Visakhapatnam that may need a professional website."
        )

    st.subheader("📈 Your Business Overview")

    total, emails, phones, opportunities = get_dashboard_data()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Leads", total)
    col2.metric("Public Emails Found", emails)
    col3.metric("Public Phone Numbers", phones)
    col4.metric("Website Opportunities", opportunities)

    st.divider()

    st.subheader("⚡ Explore Your Platform")

    col1, col2 = st.columns(2)

    with col1:

        with st.container(border=True):

            st.markdown("### 🔎 Lead Discovery")

            st.write(
                "Search hotels and restaurants and discover "
                "businesses that may need a website."
            )

            if st.button("Find New Leads", use_container_width=True):
                st.session_state["selected_page"] = "🔎 Find Leads"
                st.rerun()

        with st.container(border=True):

            st.markdown("### 📋 CRM Management")

            st.write(
                "Organize your leads, update their status, "
                "and manage your business pipeline."
            )

            if st.button("Manage Leads", use_container_width=True):
                st.session_state["selected_page"] = "📋 CRM Management"
                st.rerun()

    with col2:

        with st.container(border=True):

            st.markdown("### ✉️ AI Email Studio")

            st.write(
                "Create professional business emails, edit drafts, "
                "and open Gmail with your prepared message."
            )

            if st.button("Open Email Studio", use_container_width=True):
                st.session_state["selected_page"] = "✉️ AI Email Studio"
                st.rerun()

        with st.container(border=True):

            st.markdown("### 📊 Business Analytics")

            st.write(
                "View your lead pipeline, contact information, "
                "and business statistics."
            )

            if st.button("View Analytics", use_container_width=True):
                st.session_state["selected_page"] = "📊 Analytics"
                st.rerun()

    st.divider()

    st.subheader("💡 How LEADGEN AI Works")

    step1, step2, step3, step4 = st.columns(4)

    with step1:
        st.markdown("### 1️⃣ Discover")
        st.caption("Search local businesses.")

    with step2:
        st.markdown("### 2️⃣ Analyze")
        st.caption("Check website opportunities.")

    with step3:
        st.markdown("### 3️⃣ Connect")
        st.caption("Find public contacts.")

    with step4:
        st.markdown("### 4️⃣ Grow")
        st.caption("Manage leads and progress.")

    st.divider()

    st.caption(
        "LEADGEN AI | Smart Lead Discovery • Contact Research • CRM • Email Studio"
    )


# ==================================================
# FIND LEADS PAGE
# ==================================================

elif page == "🔎 Find Leads":

    st.title("🔎 Find Business Leads")

    st.write(
        "Find actual hotels and restaurants using Geoapify business listings."
    )

    with st.container(border=True):

        city = st.text_input(
            "Enter City",
            value="Visakhapatnam"
        )

        col1, col2 = st.columns(2)

        with col1:

            business_type = st.selectbox(
                "Business Category",
                ["Both", "Hotels", "Restaurants"]
            )

        with col2:

            lead_count = st.slider(
                "Number of Businesses",
                min_value=5,
                max_value=30,
                value=10
            )

        find_button = st.button(
            "🔎 Find Leads",
            type="primary"
        )

    # Clear old results when a new search starts.
    if find_button:

        st.session_state.pop("latest_search_leads", None)

        if not city.strip():

            st.error("Please enter a city.")

        else:

            try:

                # ----------------------------------
                # STEP 1: SEARCH GEOAPIFY
                # ----------------------------------

                with st.spinner(
                    "Finding actual hotels and restaurants..."
                ):

                    raw_leads = search_businesses(
                        city=city.strip(),
                        max_results=lead_count,
                        business_type=business_type
                    )

                st.write("### Search verification")

                st.write(
                    f"Geoapify returned {len(raw_leads)} raw listings."
                )

                # Keep only real hotel and restaurant listings.
                leads = filter_businesses(raw_leads)

                st.write(
                    f"{len(leads)} listings passed the business filters."
                )

                if not leads:

                    st.warning(
                        "No qualifying hotel or restaurant listings found. "
                        "Try another category or city."
                    )

                else:

                    # Preserve the original business records.
                    original_leads = [dict(lead) for lead in leads]

                    st.success(
                        f"Found {len(leads)} qualifying business listings!"
                    )

                    # ----------------------------------
                    # STEP 2: FIND PUBLIC CONTACTS
                    # ----------------------------------

                    with st.spinner(
                        "Finding public contact information..."
                    ):

                        leads = find_contacts_for_leads(leads)

                    leads = restore_original_business_names(
                        leads,
                        original_leads
                    )

                    # ----------------------------------
                    # STEP 3: ANALYZE WEBSITES
                    # ----------------------------------

                    with st.spinner(
                        "Analyzing business websites..."
                    ):

                        leads = analyze_websites(
                            leads,
                            city.strip()
                        )

                    leads = restore_original_business_names(
                        leads,
                        original_leads
                    )

                    # Re-apply filters after enrichment.
                    leads = filter_businesses(leads)

                    # ----------------------------------
                    # STEP 4: SCORE LEADS
                    # ----------------------------------

                    with st.spinner(
                        "Calculating lead scores..."
                    ):

                        leads = score_all_leads(leads)

                    # ----------------------------------
                    # STEP 5: PREPARE EMAIL DRAFTS
                    # ----------------------------------

                    with st.spinner(
                        "Preparing professional email drafts..."
                    ):

                        for lead in leads:

                            draft = personalize_email(lead)

                            lead["email_draft"] = draft
                            lead["email_subject"] = draft["subject"]
                            lead["email_body"] = draft["body"]

                    # ----------------------------------
                    # STEP 6: SAVE TO CRM
                    # ----------------------------------

                    if leads:

                        saved_leads = save_new_leads(leads)

                        st.session_state["latest_search_leads"] = leads

                        st.success(
                            f"Search completed! Found {len(leads)} businesses. "
                            f"Your saved CRM now contains {len(saved_leads)} leads."
                        )

            except Exception as error:

                st.error(
                    f"Something went wrong: {error}"
                )

    # ==================================================
    # DISPLAY SEARCH RESULTS
    # ==================================================

    latest_leads = st.session_state.get(
        "latest_search_leads", []
    )

    if latest_leads:

        st.divider()

        st.subheader("📋 Business Search Results")

        for index, lead in enumerate(latest_leads):

            name = lead.get(
                "business_name",
                "Unknown Business"
            )

            with st.expander(f"🏢 {name}"):

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "**Category:**",
                        lead.get("category", "Not available")
                    )

                    st.write(
                        "**Phone:**",
                        lead.get("phone") or "Not found"
                    )

                    st.write(
                        "**Email:**",
                        lead.get("email") or "Not found"
                    )

                    st.write(
                        "**Address:**",
                        lead.get("address", "Not available")
                    )

                with col2:

                    st.write(
                        "**Website:**",
                        lead.get("website") or "Not found"
                    )

                    st.write(
                        "**Website Status:**",
                        lead.get("website_status", "Manual review")
                    )

                    st.write(
                        "**Lead Score:**",
                        lead.get("lead_score", "Not available")
                    )

                    st.write(
                        "**Lead Rating:**",
                        lead.get("lead_rating", "Not available")
                    )

                if lead.get("source_url"):

                    st.write(
                        "**Map / Source:**",
                        lead["source_url"]
                    )

                if lead.get("contact_sources"):

                    st.write("**Contact research sources:**")

                    for source in lead["contact_sources"]:
                        st.write(source)

        # CSV EXPORT
        export_df = pd.DataFrame(latest_leads)

        csv_data = export_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Leads as CSV",
            data=csv_data,
            file_name="leadgen_ai_leads.csv",
            mime="text/csv"
        )

    else:

        st.info(
            "Search for hotels or restaurants to see business listings here."
        )

    st.caption(
        "A missing website listing does not prove that a business has no website. "
        "Check public contact details before outreach."
    )


# ==================================================
# CRM MANAGEMENT PAGE
# ==================================================

elif page == "📋 CRM Management":

    show_crm_dashboard()


# ==================================================
# AI EMAIL STUDIO
# ==================================================

elif page == "✉️ AI Email Studio":

    st.title("✉️ AI Email Studio")

    st.write(
        "Prepare professional emails for your business leads."
    )

    leads = load_leads()

    if not leads:

        st.warning(
            "No saved leads found. Please find leads first."
        )

    else:

        st.divider()

        selected_index = st.selectbox(
            "Select Business",
            options=list(range(len(leads))),
            format_func=lambda i: leads[i].get(
                "business_name",
                "Unknown Business"
            )
        )

        lead = leads[selected_index]

        if not lead.get("email_draft"):

            draft = personalize_email(lead)

            lead["email_draft"] = draft
            lead["email_subject"] = draft["subject"]
            lead["email_body"] = draft["body"]

            save_leads(leads)

        draft = lead.get("email_draft", {})

        subject_key = f"email_subject_{selected_index}"
        body_key = f"email_body_{selected_index}"
        recipient_key = f"email_recipient_{selected_index}"

        if subject_key not in st.session_state:

            st.session_state[subject_key] = lead.get(
                "email_subject",
                draft.get("subject", "")
            )

        if body_key not in st.session_state:

            st.session_state[body_key] = lead.get(
                "email_body",
                draft.get("body", "")
            )

        if recipient_key not in st.session_state:

            st.session_state[recipient_key] = lead.get(
                "email",
                ""
            )

        st.subheader("🏢 Business Information")

        col1, col2 = st.columns(2)

        with col1:

            st.write(
                "**Business:**",
                lead.get("business_name", "Not available")
            )

            st.write(
                "**Category:**",
                lead.get("category", "Not available")
            )

        with col2:

            st.write(
                "**Public Email:**",
                lead.get("email") or "Not found"
            )

            st.write(
                "**Phone:**",
                lead.get("phone") or "Not found"
            )

        st.divider()

        st.subheader("📝 Email Draft")

        recipient = st.text_input(
            "Recipient Email Address",
            key=recipient_key,
            placeholder="Enter business email address"
        )

        subject = st.text_input(
            "Email Subject",
            key=subject_key
        )

        body = st.text_area(
            "Email Message",
            key=body_key,
            height=350
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "💾 Save Email Draft",
                use_container_width=True
            ):

                current_leads = load_leads()

                current_leads[selected_index]["email"] = recipient
                current_leads[selected_index]["email_subject"] = subject
                current_leads[selected_index]["email_body"] = body

                current_leads[selected_index]["email_draft"] = {
                    "subject": subject,
                    "body": body
                }

                save_leads(current_leads)

                st.success(
                    "Email draft saved successfully!"
                )

        with col2:

            st.button(
                "🔄 Regenerate Email",
                use_container_width=True,
                on_click=regenerate_email_callback,
                args=(selected_index,)
            )

        if st.session_state.pop(
            "email_regenerated",
            False
        ):

            st.success(
                "A new email version has been generated!"
            )

        st.divider()

        st.subheader("📨 Open Gmail")

        if recipient and "@" in recipient:

            gmail_url = (
                "https://mail.google.com/mail/?view=cm&fs=1&"
                + urlencode({
                    "to": recipient,
                    "su": subject,
                    "body": body
                })
            )

            st.link_button(
                "Open Gmail Compose",
                gmail_url,
                use_container_width=True
            )

            st.caption(
                "Gmail opens with your draft filled in. "
                "Review it and click Send yourself."
            )

        else:

            st.warning(
                "Enter a valid public business email address to open Gmail."
            )


# ==================================================
# AI REPLY HANDLER PAGE
# ==================================================

elif page == "📬 AI Reply Handler":

    st.title("📬 AI Reply Handler")

    st.write(
        "Read incoming Gmail messages and prepare professional AI replies locally with Ollama. "
        "You review and copy each reply yourself; this page does not send emails."
    )

    st.info(
        "Gmail access is read-only. Ollama generates reply suggestions on your computer. "
        "Review every suggestion before using it."
    )

    max_emails = st.selectbox(
        "Number of recent emails",
        [5, 10, 20, 30],
        index=1
    )

    if st.button("🔄 Connect / Refresh Gmail", type="primary"):

        try:

            with st.spinner(
                "Connecting to Gmail and fetching recent emails..."
            ):

                emails = get_recent_emails(
                    max_results=max_emails
                )

            st.session_state["gmail_recent_emails"] = emails

            st.success(
                f"Gmail connected. Retrieved {len(emails)} email(s)."
            )

        except Exception as error:

            st.error(
                f"Gmail connection failed: {error}"
            )

            st.caption(
                "Check that Gmail API is enabled, credentials.json is in the main project folder, "
                "your Gmail account is an OAuth test user, and the Gmail API Python packages are installed."
            )

    emails = st.session_state.get(
        "gmail_recent_emails",
        []
    )

    if emails:

        st.subheader("Recent Gmail Messages")

        for email in emails:

            message_id = str(
                email.get("id", "unknown")
            )

            safe_id = "".join(
                ch for ch in message_id if ch.isalnum()
            )[:30] or "message"

            reply_key = f"ollama_reply_{safe_id}"
            instruction_key = f"ollama_instruction_{safe_id}"
            edited_key = f"edited_{safe_id}"

            email_body = (
                email.get("body") or ""
            ).strip()

            with st.container(border=True):

                st.markdown(
                    f"**Subject:** {email.get('subject') or '(No subject)'}"
                )

                st.write(
                    "**From:**",
                    email.get("from") or "Unknown sender"
                )

                st.caption(
                    email.get("date", "Date unavailable")
                )

                with st.expander(
                    "📩 Read Full Email",
                    expanded=False
                ):

                    if email_body:
                        st.text(email_body)
                    else:
                        st.info(
                            "No readable email content was found."
                        )

                st.text_area(
                    "What should the reply focus on? (Optional)",
                    key=instruction_key,
                    placeholder="Example: Thank them and ask when they are available for a short call.",
                    height=70
                )

                if st.button(
                    "✨ Generate AI Reply",
                    key=f"generate_{safe_id}",
                    type="primary"
                ):

                    if not email_body:

                        st.warning(
                            "This email has no readable body. Cannot generate a useful reply."
                        )

                    else:

                        try:

                            with st.spinner(
                                "Ollama is writing a professional reply..."
                            ):

                                st.session_state[reply_key] = generate_email_reply(
                                    email,
                                    extra_instruction=st.session_state.get(
                                        instruction_key,
                                        ""
                                    )
                                )

                            st.session_state[edited_key] = (
                                st.session_state[reply_key]
                            )

                            st.success(
                                "Reply generated. Review and edit it below."
                            )

                        except Exception as error:

                            st.error(
                                f"AI reply generation failed: {error}"
                            )

                if st.session_state.get(reply_key):

                    if edited_key not in st.session_state:

                        st.session_state[edited_key] = (
                            st.session_state[reply_key]
                        )

                    st.text_area(
                        "AI Reply — edit before using",
                        key=edited_key,
                        height=220
                    )

                    st.caption(
                        "Review and copy this reply into Gmail. Nothing is sent automatically."
                    )

                thread_id = email.get("thread_id", "")

                if thread_id:

                    thread_url = (
                        f"https://mail.google.com/mail/u/0/#all/{thread_id}"
                    )

                    st.link_button(
                        "Open Original Gmail Conversation",
                        thread_url
                    )

                st.caption(
                    f"Message ID: {message_id}"
                )

    elif "gmail_recent_emails" in st.session_state:

        st.info(
            "No inbox emails were returned. Try refreshing Gmail."
        )

    else:

        st.info(
            "Click **Connect / Refresh Gmail** to load your recent emails."
        )


# ==================================================
# FOLLOW-UP AUTOMATION PAGE
# ==================================================

elif page == "📨 Follow-up Automation":

    show_followup_dashboard()


# ==================================================
# ANALYTICS PAGE
# ==================================================

elif page == "📊 Analytics":

    show_analytics_dashboard()
