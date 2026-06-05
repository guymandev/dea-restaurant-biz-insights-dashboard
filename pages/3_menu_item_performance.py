import pandas as pd
import plotly.express as px
import streamlit as st

from utils.athena import run_athena_query


INGEST_DATE = "2026-05-27"


st.set_page_config(
    page_title="Menu Item Performance",
    page_icon="🍜",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def load_item_sales() -> pd.DataFrame:
    sql = f"""
        SELECT
            item_category,
            item_name,
            line_item_count,
            total_item_quantity,
            gross_item_revenue,
            option_revenue,
            discount_amount,
            net_revenue,
            avg_net_revenue_per_line,
            avg_net_revenue_per_unit
        FROM restaurant_analytics.item_sales
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY net_revenue DESC
    """

    return run_athena_query(sql)


def load_restaurant_item_sales() -> pd.DataFrame:
    sql = f"""
        SELECT
            restaurant_id,
            item_category,
            item_name,
            line_item_count,
            total_item_quantity,
            gross_item_revenue,
            option_revenue,
            discount_amount,
            net_revenue,
            avg_net_revenue_per_line,
            avg_net_revenue_per_unit
        FROM restaurant_analytics.restaurant_item_sales
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY net_revenue DESC
    """

    return run_athena_query(sql)


def main() -> None:
    st.title("Menu Item Performance")

    st.caption(
        "Menu item revenue, quantity, line-item activity, category performance, "
        "and restaurant-item combinations."
    )

    with st.spinner("Loading menu item data from Athena..."):
        item_sales_df = load_item_sales()
        restaurant_item_sales_df = load_restaurant_item_sales()

    numeric_cols = [
        "line_item_count",
        "total_item_quantity",
        "gross_item_revenue",
        "option_revenue",
        "discount_amount",
        "net_revenue",
        "avg_net_revenue_per_line",
        "avg_net_revenue_per_unit",
    ]

    for col in numeric_cols:
        item_sales_df[col] = item_sales_df[col].astype(float)
        restaurant_item_sales_df[col] = restaurant_item_sales_df[col].astype(float)

    total_items = len(item_sales_df)
    total_categories = item_sales_df["item_category"].nunique()
    total_line_items = item_sales_df["line_item_count"].sum()
    total_quantity = item_sales_df["total_item_quantity"].sum()
    total_net_revenue = item_sales_df["net_revenue"].sum()

    st.subheader("Menu Item KPIs")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Item / Category Combos", format_number(total_items))
    col2.metric("Categories", format_number(total_categories))
    col3.metric("Line Items", format_number(total_line_items))
    col4.metric("Units Sold", format_number(total_quantity))
    col5.metric("Net Revenue", format_currency(total_net_revenue))

    st.caption(f"Ingest partition: {INGEST_DATE}")

    st.divider()

    st.subheader("Top Menu Items")

    top_n = st.slider(
        "Number of items to display",
        min_value=5,
        max_value=min(30, len(item_sales_df)),
        value=10,
        step=1,
    )

    top_items_df = item_sales_df.head(top_n).copy()

    top_items_fig = px.bar(
        top_items_df.sort_values("net_revenue", ascending=True),
        x="net_revenue",
        y="item_name",
        color="item_category",
        orientation="h",
        title=f"Top {top_n} Menu Items by Net Revenue",
        labels={
            "item_name": "Item",
            "net_revenue": "Net Revenue",
            "item_category": "Category",
        },
    )

    st.plotly_chart(top_items_fig, use_container_width=True)

    st.dataframe(
        top_items_df[
            [
                "item_category",
                "item_name",
                "net_revenue",
                "total_item_quantity",
                "line_item_count",
                "avg_net_revenue_per_line",
                "avg_net_revenue_per_unit",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Category Performance")

    category_df = (
        item_sales_df.groupby("item_category", as_index=False)
        .agg(
            item_count=("item_name", "nunique"),
            line_item_count=("line_item_count", "sum"),
            total_item_quantity=("total_item_quantity", "sum"),
            net_revenue=("net_revenue", "sum"),
            gross_item_revenue=("gross_item_revenue", "sum"),
            option_revenue=("option_revenue", "sum"),
        )
        .sort_values("net_revenue", ascending=False)
    )

    col_left, col_right = st.columns(2)

    with col_left:
        category_revenue_fig = px.bar(
            category_df.sort_values("net_revenue", ascending=True),
            x="net_revenue",
            y="item_category",
            orientation="h",
            title="Net Revenue by Item Category",
            labels={
                "item_category": "Category",
                "net_revenue": "Net Revenue",
            },
        )

        st.plotly_chart(category_revenue_fig, use_container_width=True)

    with col_right:
        category_quantity_fig = px.bar(
            category_df.sort_values("total_item_quantity", ascending=True),
            x="total_item_quantity",
            y="item_category",
            orientation="h",
            title="Units Sold by Item Category",
            labels={
                "item_category": "Category",
                "total_item_quantity": "Units Sold",
            },
        )

        st.plotly_chart(category_quantity_fig, use_container_width=True)

    st.dataframe(
        category_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Revenue vs Quantity")

    scatter_fig = px.scatter(
        item_sales_df,
        x="total_item_quantity",
        y="net_revenue",
        size="line_item_count",
        color="item_category",
        hover_data=[
            "item_name",
            "avg_net_revenue_per_line",
            "avg_net_revenue_per_unit",
        ],
        title="Item Quantity vs Net Revenue",
        labels={
            "total_item_quantity": "Units Sold",
            "net_revenue": "Net Revenue",
            "line_item_count": "Line Items",
            "item_category": "Category",
        },
    )

    st.plotly_chart(scatter_fig, use_container_width=True)

    st.divider()

    st.subheader("Restaurant-Item Performance")

    category_options = ["All"] + sorted(
        restaurant_item_sales_df["item_category"].dropna().unique().tolist()
    )

    selected_category = st.selectbox(
        "Filter by item category",
        options=category_options,
    )

    filtered_restaurant_item_df = restaurant_item_sales_df.copy()

    if selected_category != "All":
        filtered_restaurant_item_df = filtered_restaurant_item_df[
            filtered_restaurant_item_df["item_category"] == selected_category
        ]

    top_restaurant_item_n = st.slider(
        "Number of restaurant-item combinations to display",
        min_value=5,
        max_value=min(30, len(filtered_restaurant_item_df)),
        value=10,
        step=1,
    )

    top_restaurant_items_df = filtered_restaurant_item_df.head(
        top_restaurant_item_n
    ).copy()

    restaurant_item_fig = px.bar(
        top_restaurant_items_df.sort_values("net_revenue", ascending=True),
        x="net_revenue",
        y="item_name",
        color="restaurant_id",
        orientation="h",
        title=f"Top {top_restaurant_item_n} Restaurant-Item Combinations by Net Revenue",
        labels={
            "item_name": "Item",
            "net_revenue": "Net Revenue",
            "restaurant_id": "Restaurant ID",
        },
        hover_data=[
            "restaurant_id",
            "item_category",
            "total_item_quantity",
            "line_item_count",
        ],
    )

    st.plotly_chart(restaurant_item_fig, use_container_width=True)

    st.dataframe(
        top_restaurant_items_df[
            [
                "restaurant_id",
                "item_category",
                "item_name",
                "net_revenue",
                "total_item_quantity",
                "line_item_count",
                "avg_net_revenue_per_line",
                "avg_net_revenue_per_unit",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()