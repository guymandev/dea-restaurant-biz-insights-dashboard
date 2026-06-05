import pandas as pd
import plotly.express as px
import streamlit as st

from utils.athena import run_athena_query


INGEST_DATE = "2026-05-27"


st.set_page_config(
    page_title="Option Analytics",
    page_icon="🧂",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def load_option_sales() -> pd.DataFrame:
    sql = f"""
        SELECT
            option_group_name,
            option_name,
            option_row_count,
            total_option_quantity,
            option_revenue,
            discount_amount
        FROM restaurant_analytics.option_sales
        WHERE ingest_date = '{INGEST_DATE}'
        ORDER BY option_revenue DESC
    """

    return run_athena_query(sql)


def main() -> None:
    st.title("Option Analytics")

    st.caption(
        "Modifier and option performance by revenue, quantity, option group, and usage frequency."
    )

    with st.spinner("Loading option analytics from Athena..."):
        option_sales_df = load_option_sales()

    numeric_cols = [
        "option_row_count",
        "total_option_quantity",
        "option_revenue",
        "discount_amount",
    ]

    for col in numeric_cols:
        option_sales_df[col] = option_sales_df[col].astype(float)

    total_options = len(option_sales_df)
    total_option_groups = option_sales_df["option_group_name"].nunique()
    total_option_rows = option_sales_df["option_row_count"].sum()
    total_option_quantity = option_sales_df["total_option_quantity"].sum()
    total_option_revenue = option_sales_df["option_revenue"].sum()

    st.subheader("Option KPIs")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Option Combos", format_number(total_options))
    col2.metric("Option Groups", format_number(total_option_groups))
    col3.metric("Option Rows", format_number(total_option_rows))
    col4.metric("Option Quantity", format_number(total_option_quantity))
    col5.metric("Option Revenue", format_currency(total_option_revenue))

    st.caption(f"Ingest partition: {INGEST_DATE}")

    st.divider()

    st.subheader("Top Options")

    top_n = st.slider(
        "Number of options to display",
        min_value=5,
        max_value=min(30, len(option_sales_df)),
        value=10,
        step=1,
    )

    top_options_df = option_sales_df.head(top_n).copy()

    top_revenue_fig = px.bar(
        top_options_df.sort_values("option_revenue", ascending=True),
        x="option_revenue",
        y="option_name",
        color="option_group_name",
        orientation="h",
        title=f"Top {top_n} Options by Revenue",
        labels={
            "option_name": "Option",
            "option_revenue": "Option Revenue",
            "option_group_name": "Option Group",
        },
    )

    st.plotly_chart(top_revenue_fig, use_container_width=True)

    st.dataframe(
        top_options_df[
            [
                "option_group_name",
                "option_name",
                "option_revenue",
                "total_option_quantity",
                "option_row_count",
                "discount_amount",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Option Group Performance")

    option_group_df = (
        option_sales_df.groupby("option_group_name", as_index=False)
        .agg(
            option_count=("option_name", "nunique"),
            option_row_count=("option_row_count", "sum"),
            total_option_quantity=("total_option_quantity", "sum"),
            option_revenue=("option_revenue", "sum"),
            discount_amount=("discount_amount", "sum"),
        )
        .sort_values("option_revenue", ascending=False)
    )

    col_left, col_right = st.columns(2)

    with col_left:
        group_revenue_fig = px.bar(
            option_group_df.sort_values("option_revenue", ascending=True),
            x="option_revenue",
            y="option_group_name",
            orientation="h",
            title="Option Revenue by Option Group",
            labels={
                "option_group_name": "Option Group",
                "option_revenue": "Option Revenue",
            },
        )

        st.plotly_chart(group_revenue_fig, use_container_width=True)

    with col_right:
        group_quantity_fig = px.bar(
            option_group_df.sort_values("total_option_quantity", ascending=True),
            x="total_option_quantity",
            y="option_group_name",
            orientation="h",
            title="Option Quantity by Option Group",
            labels={
                "option_group_name": "Option Group",
                "total_option_quantity": "Option Quantity",
            },
        )

        st.plotly_chart(group_quantity_fig, use_container_width=True)

    st.dataframe(
        option_group_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Revenue vs Quantity")

    scatter_fig = px.scatter(
        option_sales_df,
        x="total_option_quantity",
        y="option_revenue",
        size="option_row_count",
        color="option_group_name",
        hover_data=["option_name", "discount_amount"],
        title="Option Quantity vs Option Revenue",
        labels={
            "total_option_quantity": "Option Quantity",
            "option_revenue": "Option Revenue",
            "option_row_count": "Option Rows",
            "option_group_name": "Option Group",
        },
    )

    st.plotly_chart(scatter_fig, use_container_width=True)

    st.divider()

    st.subheader("Top Options by Quantity")

    top_quantity_df = option_sales_df.sort_values(
        "total_option_quantity",
        ascending=False,
    ).head(top_n)

    quantity_fig = px.bar(
        top_quantity_df.sort_values("total_option_quantity", ascending=True),
        x="total_option_quantity",
        y="option_name",
        color="option_group_name",
        orientation="h",
        title=f"Top {top_n} Options by Quantity",
        labels={
            "option_name": "Option",
            "total_option_quantity": "Option Quantity",
            "option_group_name": "Option Group",
        },
    )

    st.plotly_chart(quantity_fig, use_container_width=True)

    st.dataframe(
        top_quantity_df[
            [
                "option_group_name",
                "option_name",
                "total_option_quantity",
                "option_row_count",
                "option_revenue",
                "discount_amount",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Explore Options")

    option_group_options = ["All"] + sorted(
        option_sales_df["option_group_name"].dropna().unique().tolist()
    )

    selected_option_group = st.selectbox(
        "Filter by option group",
        options=option_group_options,
    )

    filtered_options_df = option_sales_df.copy()

    if selected_option_group != "All":
        filtered_options_df = filtered_options_df[
            filtered_options_df["option_group_name"] == selected_option_group
        ]

    filtered_options_df = filtered_options_df.sort_values(
        "option_revenue",
        ascending=False,
    )

    st.dataframe(
        filtered_options_df,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()