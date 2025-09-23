import os
import requests
from datetime import datetime, timedelta, timezone
from azure.identity import DefaultAzureCredential

subscription_id = "0b100b44-fb20-415e-b735-4594f153619b"
resource_group = "rg-TIP-2025-POC"
account_name = "tip-2025-poc-resource"

# Build resourceId (without leading slash for formatting)
resource_id = f"subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{account_name}"

base_url = f"https://management.azure.com/{resource_id}/providers/microsoft.insights/metrics"

# Last 6 hours
end_time = datetime.now(timezone.utc).replace(microsecond=0)
start_time = end_time - timedelta(hours=6)
timespan = f"{start_time.isoformat()}/{end_time.isoformat()}"

params = {
    "metricnames": "SuccessLatency,TotalLatency",
    "metricnamespace": "microsoft.cognitiveservices/accounts",
    "timespan": timespan,
    "interval": "PT5M",
    "aggregation": "Average,Percentile",
    "percentile": "50,95,99",
    # Filter example (optional):
    # "filter": "Operation eq 'TextTranslation' and ResponseType eq 'Success'",
    "api-version": "2025-03-01"
}

credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default").token
headers = {
    "Authorization": f"Bearer {token}"
}

resp = requests.get(base_url, headers=headers, params=params, timeout=30)
resp.raise_for_status()
data = resp.json()

# Simple parse: print P95 average across last buckets
for metric in data.get("value", []):
    print("Metric:", metric.get("name", {}).get("value"))
    for ts in metric.get("timeseries", []):
        meta = ts.get("metadatavalues", [])
        for dp in ts.get("data", []):
            # dp keys: average, percentile, timeStamp, etc.
            # Percentile values appear as e.g. 'percentile' or 'P95' depending on API version
            # For 2023-10-01: expect 'percentile50', 'percentile95', 'percentile99'
            p95 = dp.get("percentile95")
            if p95 is not None:
                print(dp["timeStamp"], "P95(ms) =", p95)