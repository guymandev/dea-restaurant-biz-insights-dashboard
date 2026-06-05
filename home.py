import os

import boto3
import awswrangler as wr
import pandas as pd
import streamlit as st
from utils.athena import get_aws_config, run_athena_query


APP_TITLE = "Restaurant Business Insights Dashboard"

DEFAULT_REGION = "us-east-2"
DEFAULT_DATABASE = "restaurant_analytics"
DEFAULT_ATHENA_OUTPUT = "s3://dea-restaurant-biz-insights/athena-query-results/"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🍽️",
    layout="wide",
)

def render_sidebar(config: dict) -> None:
    st.sidebar.title("Dashboard Config")

    st.sidebar.write("**Athena database**")
    st.sidebar.code(config["athena_database"])

    st.sidebar.write("**AWS region**")
    st.sidebar.code(config["region_name"])

    st.sidebar.write("**Athena output location**")
    st.sidebar.code(config["athena_output_location"])

    st.sidebar.divider()

    st.sidebar.caption(
        "Use the pages in the sidebar to navigate between executive, "
        "restaurant, menu, customer, and option analytics."
    )


def main() -> None:
    config = get_aws_config()
    render_sidebar(config)

    st.title(APP_TITLE)

    st.markdown(
        """
        This dashboard presents curated analytics from the restaurant business
        insights data pipeline.

        The data flow is:

        ```text
        SQL Server → AWS Glue → S3 Raw/Silver/Gold/Marts → Glue Data Catalog → Athena → Streamlit
        ```
        """
    )

    st.subheader("Available Dashboard Sections")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Executive Overview")
        st.write("Revenue, orders, customers, average order value, and trend metrics.")

        st.markdown("### Restaurant Performance")
        st.write("Top restaurants, restaurant-level revenue, and daily performance.")

    with col2:
        st.markdown("### Menu Item Performance")
        st.write("Top items, item categories, and restaurant-item combinations.")

        st.markdown("### Customer Analytics")
        st.write("Customer lifetime value, CLV tiers, and RFM segmentation.")

    with col3:
        st.markdown("### Option Analytics")
        st.write("Top modifiers/options by revenue, quantity, and usage.")

    st.divider()

    st.subheader("Athena Connection Check")

    st.write(
        "Use this quick check to confirm that Streamlit can connect to Athena "
        "and see the curated mart tables."
    )

    if st.button("Test Athena connection"):
        sql = f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = '{config["athena_database"]}'
            ORDER BY table_name
        """

        try:
            tables_df = run_athena_query(sql)

            st.success("Athena connection succeeded.")
            st.dataframe(tables_df, use_container_width=True)

        except Exception as exc:
            st.error("Athena connection failed.")
            st.exception(exc)

    st.divider()

    st.caption(
        "Restaurant Business Insights Dashboard | Powered by AWS Glue, Athena, "
        "S3, and Streamlit"
    )


if __name__ == "__main__":
    main()