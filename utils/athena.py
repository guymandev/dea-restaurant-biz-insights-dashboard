import os

import boto3
import awswrangler as wr
import pandas as pd
import streamlit as st


DEFAULT_REGION = "us-east-2"
DEFAULT_DATABASE = "restaurant_analytics"
DEFAULT_ATHENA_OUTPUT = "s3://dea-restaurant-biz-insights/athena-query-results/"


def get_secret_value(section: str, key: str, default: str | None = None) -> str | None:
    """
    Safely read values from Streamlit secrets.

    This supports deployment via Streamlit Cloud while still allowing local
    development through normal AWS CLI credentials or environment variables.
    """
    try:
        return st.secrets.get(section, {}).get(key, default)
    except Exception:
        return default


def get_aws_config() -> dict:
    """
    Resolve AWS/Athena configuration from Streamlit secrets first,
    then environment variables, then project defaults.
    """
    region_name = (
        get_secret_value("aws", "region_name")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_REGION
    )

    athena_database = (
        get_secret_value("aws", "athena_database")
        or os.getenv("ATHENA_DATABASE")
        or DEFAULT_DATABASE
    )

    athena_output_location = (
        get_secret_value("aws", "athena_output_location")
        or os.getenv("ATHENA_OUTPUT_LOCATION")
        or DEFAULT_ATHENA_OUTPUT
    )

    aws_access_key_id = (
        get_secret_value("aws", "aws_access_key_id")
        or os.getenv("AWS_ACCESS_KEY_ID")
    )

    aws_secret_access_key = (
        get_secret_value("aws", "aws_secret_access_key")
        or os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    return {
        "region_name": region_name,
        "athena_database": athena_database,
        "athena_output_location": athena_output_location,
        "aws_access_key_id": aws_access_key_id,
        "aws_secret_access_key": aws_secret_access_key,
    }


@st.cache_resource
def get_boto3_session(config: dict) -> boto3.Session:
    """
    Create a boto3 session.

    Locally, this can use existing AWS CLI credentials.
    In Streamlit Cloud, it can use credentials from st.secrets.
    """
    if config.get("aws_access_key_id") and config.get("aws_secret_access_key"):
        return boto3.Session(
            aws_access_key_id=config["aws_access_key_id"],
            aws_secret_access_key=config["aws_secret_access_key"],
            region_name=config["region_name"],
        )

    return boto3.Session(region_name=config["region_name"])


@st.cache_data(ttl=600)
def run_athena_query(sql: str) -> pd.DataFrame:
    """
    Run an Athena query and return a Pandas DataFrame.
    """
    config = get_aws_config()
    boto3_session = get_boto3_session(config)

    return wr.athena.read_sql_query(
        sql=sql,
        database=config["athena_database"],
        s3_output=config["athena_output_location"],
        boto3_session=boto3_session,
        ctas_approach=False,
    )