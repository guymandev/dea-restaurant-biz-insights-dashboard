import pandas as pd
import plotly.express as px
import streamlit as st

from utils.athena import run_athena_query


INGEST_DATE = "2026-05-27"


st.set_page_config(
    page_title="Restaurant Performance",
    page_icon="🏪",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def load_restaurant_summary() -> pd.DataFrame:
    sql = f"""
        SELECT
            restaurant_id,
            SUM(order_count) AS total_orders,
            SUM(net_revenue) AS total_net_revenue,
            SUM(gross_item_revenue) AS total_gross_item_revenue,
            SUM(option_revenue) AS total_option_revenue,
            SUM(discount_amount) AS total_discount_amount,
            SUM(net_revenue) / NULLIF(SUM(order_count), 0) AS avg_order_value,
            COUNT(DISTINCT order_date) AS active_sales_days,
            MIN(order_date) AS first_order_date,
            MAX(order_date) AS latest_order_date
        FROM restaurant_analytics.restaurant_daily_sales
        WHERE ingest_date = '{INGEST_DATE}'
        GROUP BY restaurant_id
        ORDER BY total_net_revenue DESC
    """

    return run_athena_query(sql)


def load_restaurant_daily_sales() -> pd.DataFrame:
    sql = f"""
        SELECT
            restaurant_id,
            order_date,
            order_count,
            gross_item_revenue,
            option_revenue,
            discount_amount,
            net_revenue,
            avg_order_value
        FROM restaurant_analytics.restaurant_daily_sales
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY order_date, restaurant_id
    """

    df = run_athena_query(sql)
    df["order_date"] = pd.to_datetime(df["order_date"])

    return df


def main() -> None:
    st.title("Restaurant Performance")

    st.caption(
        "Restaurant-level revenue, order volume, average order value, and daily sales trends."
    )

    with st.spinner("Loading restaurant performance data from Athena..."):
        restaurant_summary_df = load_restaurant_summary()
        restaurant_daily_df = load_restaurant_daily_sales()

    restaurant_summary_df["total_net_revenue"] = restaurant_summary_df[
        "total_net_revenue"
    ].astype(float)
    restaurant_summary_df["avg_order_value"] = restaurant_summary_df[
        "avg_order_value"
    ].astype(float)

    restaurant_daily_df["net_revenue"] = restaurant_daily_df["net_revenue"].astype(float)
    restaurant_daily_df["avg_order_value"] = restaurant_daily_df[
        "avg_order_value"
    ].astype(float)

    total_restaurants = restaurant_summary_df["restaurant_id"].nunique()
    total_orders = restaurant_summary_df["total_orders"].sum()
    total_net_revenue = restaurant_summary_df["total_net_revenue"].sum()
    avg_restaurant_revenue = restaurant_summary_df["total_net_revenue"].mean()

    st.subheader("Restaurant KPIs")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Restaurants", format_number(total_restaurants))
    col2.metric("Total Orders", format_number(total_orders))
    col3.metric("Total Net Revenue", format_currency(total_net_revenue))
    col4.metric("Avg Revenue / Restaurant", format_currency(avg_restaurant_revenue))

    st.caption(f"Ingest partition: {INGEST_DATE}")

    st.divider()

    st.subheader("Top Restaurants")

    top_n = st.slider(
        "Number of restaurants to display",
        min_value=5,
        max_value=min(28, len(restaurant_summary_df)),
        value=10,
        step=1,
    )

    top_restaurants_df = restaurant_summary_df.head(top_n).copy()

    fig = px.bar(
        top_restaurants_df.sort_values("total_net_revenue", ascending=True),
        x="total_net_revenue",
        y="restaurant_id",
        orientation="h",
        title=f"Top {top_n} Restaurants by Net Revenue",
        labels={
            "restaurant_id": "Restaurant ID",
            "total_net_revenue": "Net Revenue",
        },
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        top_restaurants_df[
            [
                "restaurant_id",
                "total_orders",
                "total_net_revenue",
                "avg_order_value",
                "active_sales_days",
                "first_order_date",
                "latest_order_date",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Restaurant Revenue Distribution")

    col_left, col_right = st.columns(2)

    with col_left:
        revenue_dist_fig = px.histogram(
            restaurant_summary_df,
            x="total_net_revenue",
            nbins=20,
            title="Distribution of Total Net Revenue by Restaurant",
            labels={
                "total_net_revenue": "Total Net Revenue",
            },
        )

        st.plotly_chart(revenue_dist_fig, use_container_width=True)

    with col_right:
        aov_fig = px.scatter(
            restaurant_summary_df,
            x="total_orders",
            y="avg_order_value",
            size="total_net_revenue",
            hover_data=["restaurant_id", "total_net_revenue"],
            title="Orders vs Average Order Value",
            labels={
                "total_orders": "Total Orders",
                "avg_order_value": "Average Order Value",
                "total_net_revenue": "Total Net Revenue",
            },
        )

        st.plotly_chart(aov_fig, use_container_width=True)

    st.divider()

    st.subheader("Daily Sales by Restaurant")

    restaurant_options = restaurant_summary_df["restaurant_id"].tolist()

    selected_restaurants = st.multiselect(
        "Select restaurants",
        options=restaurant_options,
        default=restaurant_options[:5],
    )

    if selected_restaurants:
        selected_daily_df = restaurant_daily_df[
            restaurant_daily_df["restaurant_id"].isin(selected_restaurants)
        ].copy()

        trend_fig = px.line(
            selected_daily_df,
            x="order_date",
            y="net_revenue",
            color="restaurant_id",
            title="Daily Net Revenue by Selected Restaurant",
            labels={
                "order_date": "Order Date",
                "net_revenue": "Net Revenue",
                "restaurant_id": "Restaurant ID",
            },
        )

        st.plotly_chart(trend_fig, use_container_width=True)

        orders_fig = px.line(
            selected_daily_df,
            x="order_date",
            y="order_count",
            color="restaurant_id",
            title="Daily Order Count by Selected Restaurant",
            labels={
                "order_date": "Order Date",
                "order_count": "Orders",
                "restaurant_id": "Restaurant ID",
            },
        )

        st.plotly_chart(orders_fig, use_container_width=True)

        st.dataframe(
            selected_daily_df[
                [
                    "restaurant_id",
                    "order_date",
                    "order_count",
                    "net_revenue",
                    "avg_order_value",
                    "gross_item_revenue",
                    "option_revenue",
                    "discount_amount",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Select at least one restaurant to view daily trends.")


if __name__ == "__main__":
    main()