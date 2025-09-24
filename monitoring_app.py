import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from azure.identity import DefaultAzureCredential
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import MetricDefinition
import plotly.express as px

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Now you can use the environment variables in your code
client_id = os.getenv('AZURE_CLIENT_ID')
tenant_id = os.getenv('AZURE_TENANT_ID')
client_secret = os.getenv('AZURE_CLIENT_SECRET')
# Azure Setup
subscription_id = "0b100b44-fb20-415e-b735-4594f153619b"
resource_group = "rg-TIP-2025-POC"
resource_name = "tip-2025-poc-resource"
resource_type = "microsoft.cognitiveservices/accounts"
#metric_name = "microsoft.cognitiveservices/accounts--ModelRequests"
metric_name = "Latency"
aggregation_type = "Total"  # Example aggregation type
project_name = "tip-2025-poc"
# Azure Monitor client
credential = DefaultAzureCredential()
monitor_client = MonitorManagementClient(credential, subscription_id)

# Helper function to get metrics from Azure Monitor
def get_metrics():
    # Get the current time and set a 24-hour duration (86400000 ms)
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(milliseconds=36000000)

    # Prepare the resource ID
    resource_id = f"/subscriptions/{subscription_id}/resourcegroups/{resource_group}/providers/{resource_type}/{resource_name}"

    # Fetch metrics
    metrics_data = monitor_client.metrics.list(
        resource_id,
        timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
        metricnames=metric_name,
        aggregation=aggregation_type
    )

    # Process the metrics data into a format for the frontend
    metrics_list = []
    #print(metrics_data.value)
    for item in metrics_data.value:
        for timeseries in item.timeseries:
            for data in timeseries.data:
                #print(data)
                metrics_list.append({
                    'timestamp': data.time_stamp.isoformat(),
                    'average': data.average,
                    'minimum': data.minimum,
                    'maximum': data.maximum,
                    'total': data.total
                })
        #print(metrics_list)
    #print(metrics_list)
    return metrics_list

# Streamlit page configuration

