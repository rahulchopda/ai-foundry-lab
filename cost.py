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

from azure.mgmt.costmanagement import CostManagementClient
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

# credential = AzureKeyCredential(api_key)
credential = DefaultAzureCredential()
client = CostManagementClient(credential)

scope = "/subscriptions/0b100b44-fb20-415e-b735-4594f153619b"  # Or resource group, etc.
export_name = "AI-Foundry-Cost-Export"

# Create export
export_definition = {
    "properties": {
        "type": "Usage",
        "schemaVersion": "V2",
        "deliveryInfo": {
            "destination": {
                "container": "cost-exports",
                "rootFolderPath": "ai-foundry-costs",
                "storageAccountId": "/subscriptions/0b100b44-fb20-415e-b735-4594f153619b/resourceGroups/rg-TIP-2025-POC/providers/Microsoft.CognitiveServices/accounts/tip-2025-poc-resource"
            }
        },
        "schedule": {
            "status": "Active",
            "recurrence": "Daily",
            "recurrencePeriod": {"from": "2025-09-01T00:00:00Z", "to": "2025-12-31T00:00:00Z"},
            "daily": {"status": "Active"}
        },
        "definition": {
            "type": "Usage",
            "timeframe": "MonthToDate",
            "dataset": {
                "granularity": "Daily",
                "configuration": {"columns": ["Date", "ResourceId", "Cost", "ConsumedQuantity"]}
            }
        }
    }
}
client.exports.create_or_update(scope, export_name, export_definition)

# Execute export
client.exports.execute(scope, export_name, {"runHistoryName": "Run1"})

# List exports
exports = client.exports.list(scope)
for exp in exports:
    print(exp.name, exp.properties.status)