import pandas as pd
import plotly.express as px
import streamlit as st

from utils.athena import run_athena_query


INGEST_DATE = "2026-05-27"


st.set_page_config(
    page_title="Executive Overview",
    page_icon="📊",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def load_kpis() -> pd.DataFrame:
    sql = f"""
        SELECT
            SUM(order_count) AS total_orders,
            SUM(net_revenue) AS total_net_revenue,
            SUM(gross_item_revenue) AS total_gross_item_revenue,
            SUM(option_revenue) AS total_option_revenue,
            SUM(discount_amount) AS total_discount_amount,
            SUM(net_revenue) / NULLIF(SUM(order_count), 0) AS avg_order_value,
            MIN(order_date) AS min_order_date,
            MAX(order_date) AS max_order_date
        FROM restaurant_analytics.daily_sales
        WHERE ingest_date = '{INGEST_DATE}'
    """

    return run_athena_query(sql)


def load_customer_count() -> pd.DataFrame:
    sql = f"""
        SELECT
            COUNT(*) AS total_customers,
            SUM(lifetime_net_revenue) AS customer_attributed_revenue
        FROM restaurant_analytics.customer_clv_snapshot
        WHERE ingest_date = '{INGEST_DATE}'
    """

    return run_athena_query(sql)


def load_restaurant_count() -> pd.DataFrame:
    sql = f"""
        SELECT
            COUNT(DISTINCT restaurant_id) AS total_restaurants
        FROM restaurant_analytics.restaurant_daily_sales
        WHERE ingest_date = '{INGEST_DATE}'
    """

    return run_athena_query(sql)


def load_daily_revenue_trend() -> pd.DataFrame:
    sql = f"""
        SELECT
            order_date,
            order_count,
            net_revenue,
            avg_order_value
        FROM restaurant_analytics.daily_sales
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY order_date
    """

    df = run_athena_query(sql)
    df["order_date"] = pd.to_datetime(df["order_date"])

    return df


def load_top_restaurants() -> pd.DataFrame:
    sql = f"""
        SELECT
            restaurant_id,
            SUM(order_count) AS total_orders,
            SUM(net_revenue) AS total_net_revenue,
            SUM(net_revenue) / NULLIF(SUM(order_count), 0) AS avg_order_value
        FROM restaurant_analytics.restaurant_daily_sales
        WHERE ingest_date = '{INGEST_DATE}'
        GROUP BY restaurant_id
        ORDER BY total_net_revenue DESC
        LIMIT 10
    """

    return run_athena_query(sql)


def load_top_items() -> pd.DataFrame:
    sql = f"""
        SELECT
            item_category,
            item_name,
            net_revenue,
            total_item_quantity,
            line_item_count
        FROM restaurant_analytics.item_sales
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY net_revenue DESC
        LIMIT 10
    """

    return run_athena_query(sql)


def main() -> None:
    st.title("Executive Overview")

    st.caption(
        "High-level performance summary for the restaurant business insights pipeline."
    )

    with st.spinner("Loading executive metrics from Athena..."):
        kpi_df = load_kpis()
        customer_df = load_customer_count()
        restaurant_df = load_restaurant_count()
        trend_df = load_daily_revenue_trend()
        top_restaurants_df = load_top_restaurants()
        top_items_df = load_top_items()

    kpis = kpi_df.iloc[0]
    customers = customer_df.iloc[0]
    restaurants = restaurant_df.iloc[0]

    st.subheader("Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Net Revenue",
        format_currency(float(kpis["total_net_revenue"])),
    )

    col2.metric(
        "Total Orders",
        format_number(float(kpis["total_orders"])),
    )

    col3.metric(
        "Customers",
        format_number(float(customers["total_customers"])),
    )

    col4.metric(
        "Avg Order Value",
        format_currency(float(kpis["avg_order_value"])),
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Restaurants",
        format_number(float(restaurants["total_restaurants"])),
    )

    col6.metric(
        "Gross Item Revenue",
        format_currency(float(kpis["total_gross_item_revenue"])),
    )

    col7.metric(
        "Option Revenue",
        format_currency(float(kpis["total_option_revenue"])),
    )

    col8.metric(
        "Discount Amount",
        format_currency(float(kpis["total_discount_amount"])),
    )

    st.caption(
        f"Order date range: {kpis['min_order_date']} through {kpis['max_order_date']} | "
        f"Ingest partition: {INGEST_DATE}"
    )

    st.divider()

    st.subheader("Daily Revenue Trend")

    revenue_fig = px.line(
        trend_df,
        x="order_date",
        y="net_revenue",
        markers=True,
        title="Net Revenue by Order Date",
        labels={
            "order_date": "Order Date",
            "net_revenue": "Net Revenue",
        },
    )

    st.plotly_chart(revenue_fig, use_container_width=True)

    orders_fig = px.bar(
        trend_df,
        x="order_date",
        y="order_count",
        title="Order Count by Order Date",
        labels={
            "order_date": "Order Date",
            "order_count": "Orders",
        },
    )

    st.plotly_chart(orders_fig, use_container_width=True)

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Top Restaurants by Revenue")

        restaurants_display = top_restaurants_df.copy()
        restaurants_display["total_net_revenue"] = restaurants_display[
            "total_net_revenue"
        ].astype(float)
        restaurants_display["avg_order_value"] = restaurants_display[
            "avg_order_value"
        ].astype(float)

        fig = px.bar(
            restaurants_display,
            x="total_net_revenue",
            y="restaurant_id",
            orientation="h",
            title="Top 10 Restaurants",
            labels={
                "restaurant_id": "Restaurant ID",
                "total_net_revenue": "Net Revenue",
            },
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            restaurants_display,
            use_container_width=True,
            hide_index=True,
        )

    with col_right:
        st.subheader("Top Items by Revenue")

        items_display = top_items_df.copy()
        items_display["net_revenue"] = items_display["net_revenue"].astype(float)

        fig = px.bar(
            items_display,
            x="net_revenue",
            y="item_name",
            color="item_category",
            orientation="h",
            title="Top 10 Menu Items",
            labels={
                "item_name": "Item",
                "net_revenue": "Net Revenue",
                "item_category": "Category",
            },
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            items_display,
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()