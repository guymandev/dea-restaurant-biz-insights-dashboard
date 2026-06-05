import pandas as pd
import plotly.express as px
import streamlit as st

from utils.athena import run_athena_query


INGEST_DATE = "2026-05-27"


st.set_page_config(
    page_title="Customer Analytics",
    page_icon="👥",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def load_customer_clv_snapshot() -> pd.DataFrame:
    sql = f"""
        SELECT
            user_id,
            first_order_date,
            latest_order_date,
            customer_lifetime_days,
            lifetime_order_count,
            lifetime_net_revenue,
            latest_daily_order_count,
            latest_daily_net_revenue,
            latest_daily_restaurant_count,
            latest_is_loyalty_customer_day,
            clv_quartile,
            clv_tier
        FROM restaurant_analytics.customer_clv_snapshot
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY lifetime_net_revenue DESC
    """

    df = run_athena_query(sql)
    df["first_order_date"] = pd.to_datetime(df["first_order_date"])
    df["latest_order_date"] = pd.to_datetime(df["latest_order_date"])
    return df


def load_customer_daily_clv() -> pd.DataFrame:
    sql = f"""
        SELECT
            user_id,
            order_date,
            daily_order_count,
            daily_restaurant_count,
            daily_gross_item_revenue,
            daily_option_revenue,
            daily_discount_amount,
            daily_net_revenue,
            is_loyalty_customer_day,
            cumulative_order_count,
            cumulative_net_revenue,
            first_order_date,
            latest_order_date,
            customer_lifetime_days,
            clv_quartile,
            clv_tier
        FROM restaurant_analytics.customer_daily_clv
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY order_date, user_id
    """

    df = run_athena_query(sql)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["first_order_date"] = pd.to_datetime(df["first_order_date"])
    df["latest_order_date"] = pd.to_datetime(df["latest_order_date"])
    return df


def load_customer_rfm() -> pd.DataFrame:
    sql = f"""
        SELECT
            user_id,
            first_order_date,
            latest_order_date,
            customer_lifetime_days,
            lifetime_order_count,
            lifetime_net_revenue,
            clv_quartile,
            clv_tier,
            recency_days,
            frequency_score,
            monetary_score,
            recency_score,
            rfm_score,
            rfm_total_score,
            rfm_segment,
            rfm_as_of_date
        FROM restaurant_analytics.customer_rfm
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY lifetime_net_revenue DESC
    """

    df = run_athena_query(sql)
    df["first_order_date"] = pd.to_datetime(df["first_order_date"])
    df["latest_order_date"] = pd.to_datetime(df["latest_order_date"])
    df["rfm_as_of_date"] = pd.to_datetime(df["rfm_as_of_date"])
    return df


def main() -> None:
    st.title("Customer Analytics")

    st.caption(
        "Customer lifetime value, CLV tiers, RFM segmentation, and customer-level revenue behavior."
    )

    with st.spinner("Loading customer analytics from Athena..."):
        clv_df = load_customer_clv_snapshot()
        daily_clv_df = load_customer_daily_clv()
        rfm_df = load_customer_rfm()

    numeric_clv_cols = [
        "customer_lifetime_days",
        "lifetime_order_count",
        "lifetime_net_revenue",
        "latest_daily_order_count",
        "latest_daily_net_revenue",
        "latest_daily_restaurant_count",
    ]

    for col in numeric_clv_cols:
        clv_df[col] = clv_df[col].astype(float)

    numeric_daily_cols = [
        "daily_order_count",
        "daily_restaurant_count",
        "daily_gross_item_revenue",
        "daily_option_revenue",
        "daily_discount_amount",
        "daily_net_revenue",
        "cumulative_order_count",
        "cumulative_net_revenue",
        "customer_lifetime_days",
    ]

    for col in numeric_daily_cols:
        daily_clv_df[col] = daily_clv_df[col].astype(float)

    numeric_rfm_cols = [
        "customer_lifetime_days",
        "lifetime_order_count",
        "lifetime_net_revenue",
        "recency_days",
        "frequency_score",
        "monetary_score",
        "recency_score",
        "rfm_score",
        "rfm_total_score",
    ]

    for col in numeric_rfm_cols:
        rfm_df[col] = rfm_df[col].astype(float)

    total_customers = clv_df["user_id"].nunique()
    total_lifetime_revenue = clv_df["lifetime_net_revenue"].sum()
    avg_lifetime_revenue = clv_df["lifetime_net_revenue"].mean()
    median_lifetime_revenue = clv_df["lifetime_net_revenue"].median()
    avg_lifetime_orders = clv_df["lifetime_order_count"].mean()
    loyalty_customers = clv_df["latest_is_loyalty_customer_day"].sum()

    st.subheader("Customer KPIs")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Customers", format_number(total_customers))
    col2.metric("Lifetime Revenue", format_currency(total_lifetime_revenue))
    col3.metric("Avg CLV", format_currency(avg_lifetime_revenue))
    col4.metric("Median CLV", format_currency(median_lifetime_revenue))
    col5.metric("Avg Orders / Customer", f"{avg_lifetime_orders:,.2f}")

    col6, col7, col8 = st.columns(3)

    col6.metric("Latest Loyalty Customers", format_number(loyalty_customers))
    col7.metric(
        "Avg Customer Lifetime Days",
        f"{clv_df['customer_lifetime_days'].mean():,.1f}",
    )
    col8.metric(
        "Max CLV",
        format_currency(clv_df["lifetime_net_revenue"].max()),
    )

    st.caption(f"Ingest partition: {INGEST_DATE}")

    st.divider()

    st.subheader("Customer Lifetime Value Segmentation")

    tier_order = ["high", "medium_high", "medium_low", "low"]

    clv_tier_df = (
        clv_df.groupby("clv_tier", as_index=False)
        .agg(
            customer_count=("user_id", "nunique"),
            total_lifetime_revenue=("lifetime_net_revenue", "sum"),
            avg_lifetime_revenue=("lifetime_net_revenue", "mean"),
            avg_lifetime_orders=("lifetime_order_count", "mean"),
            avg_lifetime_days=("customer_lifetime_days", "mean"),
        )
    )

    clv_tier_df["clv_tier"] = pd.Categorical(
        clv_tier_df["clv_tier"],
        categories=tier_order,
        ordered=True,
    )
    clv_tier_df = clv_tier_df.sort_values("clv_tier")

    col_left, col_right = st.columns(2)

    with col_left:
        tier_count_fig = px.bar(
            clv_tier_df,
            x="clv_tier",
            y="customer_count",
            title="Customer Count by CLV Tier",
            labels={
                "clv_tier": "CLV Tier",
                "customer_count": "Customers",
            },
        )

        st.plotly_chart(tier_count_fig, use_container_width=True)

    with col_right:
        tier_revenue_fig = px.bar(
            clv_tier_df,
            x="clv_tier",
            y="total_lifetime_revenue",
            title="Lifetime Revenue by CLV Tier",
            labels={
                "clv_tier": "CLV Tier",
                "total_lifetime_revenue": "Lifetime Revenue",
            },
        )

        st.plotly_chart(tier_revenue_fig, use_container_width=True)

    st.dataframe(
        clv_tier_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("RFM Segments")

    rfm_segment_df = (
        rfm_df.groupby("rfm_segment", as_index=False)
        .agg(
            customer_count=("user_id", "nunique"),
            total_lifetime_revenue=("lifetime_net_revenue", "sum"),
            avg_lifetime_revenue=("lifetime_net_revenue", "mean"),
            avg_frequency=("lifetime_order_count", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_rfm_score=("rfm_score", "mean"),
            avg_rfm_total_score=("rfm_total_score", "mean"),
        )
        .sort_values("total_lifetime_revenue", ascending=False)
    )

    col_left, col_right = st.columns(2)

    with col_left:
        rfm_count_fig = px.bar(
            rfm_segment_df.sort_values("customer_count", ascending=True),
            x="customer_count",
            y="rfm_segment",
            orientation="h",
            title="Customer Count by RFM Segment",
            labels={
                "customer_count": "Customers",
                "rfm_segment": "RFM Segment",
            },
        )

        st.plotly_chart(rfm_count_fig, use_container_width=True)

    with col_right:
        rfm_revenue_fig = px.bar(
            rfm_segment_df.sort_values("total_lifetime_revenue", ascending=True),
            x="total_lifetime_revenue",
            y="rfm_segment",
            orientation="h",
            title="Lifetime Revenue by RFM Segment",
            labels={
                "total_lifetime_revenue": "Lifetime Revenue",
                "rfm_segment": "RFM Segment",
            },
        )

        st.plotly_chart(rfm_revenue_fig, use_container_width=True)

    st.dataframe(
        rfm_segment_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("RFM Score Breakdown")

    col_left, col_right = st.columns(2)

    with col_left:
        score_fig = px.scatter(
            rfm_df,
            x="recency_score",
            y="monetary_score",
            color="rfm_segment",
            size="lifetime_order_count",
            hover_data=["user_id", "lifetime_net_revenue", "recency_days"],
            title="Recency Score vs Monetary Score",
            labels={
                "recency_score": "Recency Score",
                "monetary_score": "Monetary Score",
                "rfm_segment": "RFM Segment",
                "lifetime_order_count": "Lifetime Orders",
            },
        )

        st.plotly_chart(score_fig, use_container_width=True)

    with col_right:
        total_score_fig = px.histogram(
            rfm_df,
            x="rfm_total_score",
            color="rfm_segment",
            nbins=20,
            title="Distribution of RFM Total Scores",
            labels={
                "rfm_total_score": "RFM Total Score",
                "rfm_segment": "RFM Segment",
            },
        )

        st.plotly_chart(total_score_fig, use_container_width=True)

    st.divider()

    st.subheader("CLV Distribution and Order Behavior")

    col_left, col_right = st.columns(2)

    with col_left:
        clv_hist_fig = px.histogram(
            clv_df,
            x="lifetime_net_revenue",
            nbins=50,
            title="Distribution of Customer Lifetime Net Revenue",
            labels={
                "lifetime_net_revenue": "Lifetime Net Revenue",
            },
        )

        st.plotly_chart(clv_hist_fig, use_container_width=True)

    with col_right:
        orders_vs_clv_fig = px.scatter(
            clv_df,
            x="lifetime_order_count",
            y="lifetime_net_revenue",
            color="clv_tier",
            size="lifetime_order_count",
            hover_data=["user_id", "first_order_date", "latest_order_date"],
            title="Lifetime Orders vs Customer Lifetime Revenue",
            labels={
                "lifetime_order_count": "Lifetime Orders",
                "lifetime_net_revenue": "Lifetime Revenue",
                "clv_tier": "CLV Tier",
            },
        )

        st.plotly_chart(orders_vs_clv_fig, use_container_width=True)

    st.divider()

    st.subheader("Customer Daily Revenue Trend")

    top_customer_n = st.slider(
        "Number of top customers to display",
        min_value=3,
        max_value=20,
        value=10,
        step=1,
    )

    top_customer_ids = clv_df.head(top_customer_n)["user_id"].dropna().tolist()

    selected_customers = st.multiselect(
        "Select customers",
        options=clv_df["user_id"].tolist(),
        default=top_customer_ids[:5],
    )

    if selected_customers:
        selected_daily_df = daily_clv_df[
            daily_clv_df["user_id"].isin(selected_customers)
        ].copy()

        cumulative_fig = px.line(
            selected_daily_df,
            x="order_date",
            y="cumulative_net_revenue",
            color="user_id",
            title="Cumulative Net Revenue by Selected Customer",
            labels={
                "order_date": "Order Date",
                "cumulative_net_revenue": "Cumulative Net Revenue",
                "user_id": "Customer ID",
            },
        )

        st.plotly_chart(cumulative_fig, use_container_width=True)

        daily_fig = px.bar(
            selected_daily_df,
            x="order_date",
            y="daily_net_revenue",
            color="user_id",
            title="Daily Net Revenue by Selected Customer",
            labels={
                "order_date": "Order Date",
                "daily_net_revenue": "Daily Net Revenue",
                "user_id": "Customer ID",
            },
        )

        st.plotly_chart(daily_fig, use_container_width=True)

        st.dataframe(
            selected_daily_df[
                [
                    "user_id",
                    "order_date",
                    "daily_order_count",
                    "daily_restaurant_count",
                    "daily_net_revenue",
                    "cumulative_order_count",
                    "cumulative_net_revenue",
                    "is_loyalty_customer_day",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Select at least one customer to view daily trends.")

    st.divider()

    st.subheader("Top Customers by Lifetime Revenue")

    top_customers_df = clv_df.head(25).copy()

    st.dataframe(
        top_customers_df[
            [
                "user_id",
                "clv_tier",
                "clv_quartile",
                "lifetime_net_revenue",
                "lifetime_order_count",
                "first_order_date",
                "latest_order_date",
                "customer_lifetime_days",
                "latest_daily_order_count",
                "latest_daily_net_revenue",
                "latest_is_loyalty_customer_day",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()