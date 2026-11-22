
import streamlit as st
import pandas as pd

from modules.analytics import calculate_analytics


def show_analytics_dashboard():

    st.title("📊 Business Analytics Dashboard")

    data = calculate_analytics()

    counts = data["counts"]

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Businesses",
        data["total"]
    )

    col2.metric(
        "Contacted",
        data["contacted"]
    )

    col3.metric(
        "Converted",
        data["converted"]
    )

    col4.metric(
        "Conversion Rate",
        f'{data["conversion_rate"]}%'
    )

    st.divider()

    # Contact information
    st.subheader("📞 Contact Information")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Email Addresses",
        data["emails"]
    )

    col2.metric(
        "Phone Numbers",
        data["phones"]
    )

    col3.metric(
        "Website Opportunities",
        data["website_opportunities"]
    )

    st.divider()

    # CRM status chart
    st.subheader("📈 Lead Pipeline")

    status_df = pd.DataFrame({
        "Status": list(counts.keys()),
        "Businesses": list(counts.values())
    })

    st.bar_chart(
        status_df,
        x="Status",
        y="Businesses"
    )

    st.divider()

    # Lead distribution
    st.subheader("🥧 Lead Status Distribution")

    nonzero = {
        key: value
        for key, value in counts.items()
        if value > 0
    }

    if nonzero:

        chart_df = pd.DataFrame({
            "Status": list(nonzero.keys()),
            "Businesses": list(nonzero.values())
        })

        st.bar_chart(
            chart_df,
            x="Status",
            y="Businesses"
        )

    else:

        st.info("No CRM activity yet.")

    st.caption(
        "Analytics are calculated from your saved CRM leads. "
        "Conversion rate = converted leads / contacted leads."
    )
