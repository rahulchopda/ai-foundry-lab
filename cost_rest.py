from azure.identity import DefaultAzureCredential
import requests

# Replace with your subscription ID
subscription_id = '0b100b44-fb20-415e-b735-4594f153619b'

# Get token via Azure Identity (uses environment, managed identity, etc.)
credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default").token
print(token)

# Set API URL
url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query?api-version=2025-03-01"

# Build a sample request body (daily usage for last 7 days)
body = {
    "type": "ActualCost",
    "timeframe": "Last7Days",
    "dataset": {
        "granularity": "Daily",
        "aggregation": {
            "totalCost": {
                "name": "PreTaxCost",
                "function": "Sum"
            }
        }
    }
}

# body = {
#     "properties": {
#         "type": "Usage",
#         "schemaVersion": "V2",
#         "deliveryInfo": {
#             "destination": {
#                 "container": "cost-exports",
#                 "rootFolderPath": "ai-foundry-costs",
#                 "storageAccountId": "/subscriptions/0b100b44-fb20-415e-b735-4594f153619b/resourceGroups/rg-TIP-2025-POC/providers/Microsoft.CognitiveServices/accounts/tip-2025-poc-resource"
#             }
#         },
#         "schedule": {
#             "status": "Active",
#             "recurrence": "Daily",
#             "recurrencePeriod": {"from": "2025-09-01T00:00:00Z", "to": "2025-12-31T00:00:00Z"},
#             "daily": {"status": "Active"}
#         },
#         "definition": {
#             "type": "Usage",
#             "timeframe": "MonthToDate",
#             "dataset": {
#                 "granularity": "Daily",
#                 "configuration": {"columns": ["Date", "ResourceId", "Cost", "ConsumedQuantity"]}
#             }
#         }
#     }
# }

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, json=body)
print(response.json())