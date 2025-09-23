import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# init key and endpoint
api_key = os.getenv('AZURE_API_KEY')
azure_endpoint = os.getenv('AZURE_ENDPOINT')
SUB_ID = os.getenv('AZURE_SUB_ID')
RG = os.getenv('AZURE_RESOURCE_GROUP')
ACCOUNT = os.getenv('AZURE_ACCOUNT')

from azure.monitor.query import MetricsQueryClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = MetricsQueryClient(credential)

resource_id = "/subscriptions/0b100b44-fb20-415e-b735-4594f153619b/resourceGroups/rg-TIP-2025-POC/providers/Microsoft.CognitiveServices/accounts/tip-2025-poc-resource"

# https://portal.azure.com/#@morganstanleylab.onmicrosoft.com/resource/subscriptions/0b100b44-fb20-415e-b735-4594f153619b/resourceGroups/rg-TIP-2025-POC/providers/Microsoft.CognitiveServices/accounts/tip-2025-poc-resource/metrics

from datetime import datetime
start = datetime.fromisoformat("2025-09-01T00:00:00")
end = datetime.fromisoformat("2025-09-30T00:00:00")
timespan = (start, end)
# timespan = "2025-09-01T00:00:00Z/2025-09-16T00:00:00Z"
metrics = ["TotalTokens", "Latency", "RequestsCompleted"]

response = client.query_resource(
    resource_id,
    metric_names=metrics,
    timespan=timespan,
    aggregations=["Average", "Total"],
    interval="PT1H"
)

# Export to CSV
import pandas as pd
data = []
for metric in response.metrics:
    for time_series in metric.timeseries:
        for point in time_series.data:
            data.append({
                "Timestamp": point.time_stamp,
                "Metric": metric.name.value,
                "Average": point.average,
                "Total": point.total
            })
df = pd.DataFrame(data)
df.to_csv("ai-foundry-metrics.csv", index=False)
print("Exported to ai-foundry-metrics.csv")