
import streamlit as st
from urllib.parse import urlencode

from modules.lead_manager import load_leads

from modules.followup_manager import (
    mark_initial_email_sent,
    mark_followup_sent,
    mark_reply_received,
    get_followup_candidates,
    get_followup_summary,
)

from modules.followup_generator import generate_followup_email


# --------------------------------------------------
# EMAIL DRAFT PARSER
# --------------------------------------------------

def parse_followup_email(result):

    subject = ""
    body = ""

    if "BODY:" in result:

        parts = result.split("BODY:", 1)
        subject_part = parts[0].strip()
        body = parts[1].strip()

        if subject_part.upper().startswith("SUBJECT:"):
            subject = subject_part[len("SUBJECT:"):].strip()

    return subject, body


# --------------------------------------------------
# GMAIL COMPOSE LINK
# --------------------------------------------------

def create_gmail_link(email, subject, body):

    params = {
        "view": "cm",
        "fs": "1",
        "to": email,
        "su": subject,
        "body": body
    }

    return (
        "https://mail.google.com/mail/u/0/"
        "?" + urlencode(params)
    )


# --------------------------------------------------
# FOLLOW-UP DASHBOARD
# --------------------------------------------------

def show_followup_dashboard():

    st.title("📨 AI Follow-up Automation")

    st.caption(
        "Track sent emails, generate AI follow-ups "
        "and manage business responses."
    )

    # ----------------------------------------------
    # SUMMARY
    # ----------------------------------------------

    summary = get_followup_summary()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Contacted", summary["contacted"])
    col2.metric("Replies", summary["replied"])
    col3.metric("Follow-ups Sent", summary["followups_sent"])
    col4.metric("Follow-ups Due", summary["followups_due"])

    st.divider()

    # ----------------------------------------------
    # TRACK INITIAL EMAILS
    # ----------------------------------------------

    st.subheader("📤 Track Initial Emails")

    leads = load_leads()

    untracked = []

    for index, lead in enumerate(leads):

        if not isinstance(lead, dict):
            continue

        history = lead.get("outreach_history", [])

        if not isinstance(history, list):
            history = []

        already_sent = any(
            item.get("stage") == "initial"
            for item in history
        )

        if lead.get("email") and not already_sent:

            untracked.append({
                "index": index,
                "name": lead.get(
                    "business_name",
                    "Unknown Business"
                ),
                "email": lead.get("email", "")
            })

    if untracked:

        selected = st.selectbox(
            "Select a business whose initial email you have sent",
            options=untracked,
            format_func=lambda item: (
                f"{item['name']} — {item['email']}"
            ),
            key="followup_initial_select"
        )

        st.warning(
            "Only mark this as sent after you have actually "
            "sent the initial email through Gmail."
        )

        if st.button(
            "✅ Mark Initial Email as Sent",
            key="mark_initial_followup"
        ):

            try:

                mark_initial_email_sent(
                    selected["index"]
                )

                st.success(
                    f"Initial email tracked for {selected['name']}."
                )

                st.rerun()

            except Exception as error:
                st.error(str(error))

    else:

        st.info(
            "No untracked CRM businesses with email addresses found."
        )

    st.divider()

    # ----------------------------------------------
    # FOLLOW-UP CANDIDATES
    # ----------------------------------------------

    st.subheader("⏰ Follow-ups Due")

    candidates = get_followup_candidates()

    if not candidates:

        st.success(
            "No follow-ups are due right now. "
            "Businesses will appear here when their follow-up date arrives."
        )

    for candidate in candidates:

        index = candidate["lead_index"]
        name = candidate["business_name"]
        email = candidate["email"]
        number = candidate["followup_number"]

        with st.expander(
            f"📩 {name} — Follow-up {number}",
            expanded=True
        ):

            st.write(f"**Business:** {name}")
            st.write(f"**Email:** {email}")
            st.write(
                f"**Days overdue:** {candidate['days_overdue']}"
            )

            extra_instruction = st.text_input(
                "Additional instructions (optional)",
                placeholder="Example: Mention our website development service.",
                key=f"followup_instruction_{index}_{number}"
            )

            draft_key = f"followup_draft_{index}_{number}"

            if st.button(
                "✨ Generate AI Follow-up",
                key=f"generate_followup_{index}_{number}"
            ):

                try:

                    with st.spinner(
                        "Ollama is writing your follow-up..."
                    ):

                        result = generate_followup_email(
                            candidate["lead"],
                            followup_number=number,
                            extra_instruction=extra_instruction
                        )

                    st.session_state[draft_key] = result

                except Exception as error:
                    st.error(str(error))

            if draft_key in st.session_state:

                subject, body = parse_followup_email(
                    st.session_state[draft_key]
                )

                edited_subject = st.text_input(
                    "Email subject",
                    value=subject,
                    key=f"subject_{index}_{number}"
                )

                edited_body = st.text_area(
                    "Review and edit your email",
                    value=body,
                    height=250,
                    key=f"body_{index}_{number}"
                )

                if edited_subject.strip() and edited_body.strip():

                    gmail_url = create_gmail_link(
                        email,
                        edited_subject,
                        edited_body
                    )

                    st.link_button(
                        "📧 Open Gmail to Send",
                        gmail_url,
                        use_container_width=True
                    )

                    st.warning(
                        "After sending the email in Gmail, return here "
                        "and click the button below."
                    )

                    if st.button(
                        "✅ I Have Sent This Follow-up",
                        key=f"confirm_followup_{index}_{number}",
                        use_container_width=True
                    ):

                        try:

                            mark_followup_sent(index)

                            st.session_state.pop(
                                draft_key,
                                None
                            )

                            st.success(
                                "Follow-up successfully recorded!"
                            )

                            st.rerun()

                        except Exception as error:
                            st.error(str(error))

                else:

                    st.warning(
                        "Please enter both a subject and email body."
                    )

            st.divider()

            if st.button(
                "💬 Mark Business as Replied",
                key=f"replied_{index}_{number}"
            ):

                try:

                    mark_reply_received(index)

                    st.success(
                        f"{name} marked as replied. "
                        "Further follow-ups are stopped."
                    )

                    st.rerun()

                except Exception as error:
                    st.error(str(error))
