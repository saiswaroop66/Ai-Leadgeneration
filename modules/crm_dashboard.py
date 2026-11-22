
import streamlit as st

from modules.lead_manager import (
    load_leads,
    save_leads,
    STATUSES
)


def show_crm_dashboard():

    st.title("📋 Lead Management CRM")

    leads = load_leads()

    if not leads:
        st.info("No saved leads yet. Find leads first.")
        return

    st.write("Manage your hotels and restaurants.")

    status_filter = st.selectbox(
        "Filter by status",
        ["All"] + STATUSES
    )

    filtered_leads = leads

    if status_filter != "All":

        filtered_leads = [
            lead for lead in leads
            if lead.get("crm_status", "New") == status_filter
        ]

    st.subheader(
        f"Businesses: {len(filtered_leads)}"
    )

    for index, lead in enumerate(filtered_leads):

        name = lead.get(
            "business_name",
            "Unknown Business"
        )

        with st.expander(f"🏢 {name}"):

            st.write(
                "Category:",
                lead.get("category", "Not available")
            )

            st.write(
                "Phone:",
                lead.get("phone", "Not available")
            )

            st.write(
                "Email:",
                lead.get("email", "Not available")
            )

            current_status = lead.get(
                "crm_status",
                "New"
            )

            selected_status = st.selectbox(
                "Lead Status",
                STATUSES,
                index=(
                    STATUSES.index(current_status)
                    if current_status in STATUSES
                    else 0
                ),
                key=f"crm_dashboard_{index}"
            )

            if selected_status != current_status:

                lead["crm_status"] = selected_status

                save_leads(leads)

                st.success("Lead status saved!")

                st.rerun()
