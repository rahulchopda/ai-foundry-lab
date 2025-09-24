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


# Title of the App
st.title("Azure Monitor Metrics for Model Requests")
st.markdown("""
<div class="ms-header">
    <img src="https://www.morganstanley.com/etc.clientlibs/msdotcomr4/clientlibs/components/site/resources/img/logo-white.png"
         class="ms-logo" alt="Morgan Stanley Logo" />
    <h1 style="margin-bottom:8px;font-family: 'Helvetica Neue', 'Segoe UI', 'Arial', sans-serif !important;">Gen AI Playground</h1>
    <span style="font-size:1.2rem;font-weight:400;">
        Experiment, Evaluate, Govern, and Monitor AI Models
        <span class="badge-foundry">Powered by Azure AI Foundry</span>
    </span>
</div>
""", unsafe_allow_html=True)
# Fetch Metrics Data
st.sidebar.subheader("Metrics Data Filter")
metrics_data = get_metrics()

# Display metrics as a table
df = pd.DataFrame(metrics_data)
# Convert the 'timestamp' to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])



# Streamlit UI
st.title('Azure Synapse (Foundry) Monitoring')

st.write(f"Showing chart for the metric over time (filtered data)")

# Check if there are valid rows after filtering
# Set 'time_stamp' as index for reindexing
df.set_index('timestamp', inplace=True)

# Create a continuous time series (fill missing times if necessary)
full_index = pd.date_range(df.index.min(), df.index.max(), freq='T')  # Frequency is set to minute ('T')
df = df.reindex(full_index)

# Fill missing 'total' values with 0 (or you can choose a different method like interpolation)
df['total'] = df['total'].fillna(0)

# Plot the continuous time series with Plotly Express
fig = px.line(df, x=df.index, y='total', title='Average Latency Over Time')

# Customize the chart
fig.update_layout(
    xaxis_title='Timestamp',
    yaxis_title='Total (ms)',
    showlegend=False
    )

    # Display the Plotly figure in Streamlit
st.plotly_chart(fig)
