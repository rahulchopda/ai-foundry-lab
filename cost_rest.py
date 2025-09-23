"""
cost_rest.py

Functions to query Azure Cost Management API for daily costs and return
a structured result for visualization.

Prerequisites:
- azure-identity
- requests
- Proper RBAC role on the subscription (e.g. Cost Management Reader)
- Environment/MSI configured for DefaultAzureCredential

Usage inside Streamlit or other modules:
    from cost_rest import fetch_daily_costs
    data = fetch_daily_costs(subscription_id)

Returned structure:
{
  "raw": <full_response_json>,
  "records": [
      {"date": date, "cost": float, "currency": "USD"},
      ...
  ],
  "currency": "USD",
  "total_cost": float,
  "avg_daily_cost": float
}
"""

from __future__ import annotations
import datetime
from typing import Dict, Any, List, Optional
from azure.identity import DefaultAzureCredential
import requests


def _get_token() -> str:
    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default").token
    return token


def _build_body(timeframe: str = "Last7Days",
                granularity: str = "Daily",
                cost_type: str = "ActualCost",
                time_period: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Build request body for Cost Management query.
    timeframe: Last7Days | MonthToDate | BillingMonthToDate | Custom
    If timeframe='Custom', provide time_period={'from': ISO, 'to': ISO}
    """
    body: Dict[str, Any] = {
        "type": cost_type,
        "timeframe": timeframe,
        "dataset": {
            "granularity": granularity,
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum"
                }
            }
        }
    }
    if timeframe == "Custom" and time_period:
        body["timePeriod"] = time_period
    return body


def query_cost_management(subscription_id: str,
                          timeframe: str = "Last7Days",
                          time_period: Optional[Dict[str, str]] = None,
                          api_version: str = "2025-03-01") -> Dict[str, Any]:
    """
    Low-level function to query Azure Cost Management API.
    """
    token = _get_token()
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/providers/Microsoft.CostManagement/query?api-version={api_version}"
    )
    body = _build_body(timeframe=timeframe, time_period=time_period)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _parse_cost_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    props = response.get("properties", {})
    columns = props.get("columns", [])
    rows = props.get("rows", [])

    index_map = {col["name"]: idx for idx, col in enumerate(columns)}
    required = {"PreTaxCost", "UsageDate", "Currency"}
    if not required.issubset(index_map.keys()):
        raise ValueError(f"Response columns missing required fields; got {list(index_map.keys())}")

    parsed: List[Dict[str, Any]] = []
    for row in rows:
        cost = float(row[index_map["PreTaxCost"]])
        usage_date_numeric = str(row[index_map["UsageDate"]])  # 'YYYYMMDD'
        currency = row[index_map["Currency"]]
        dt = datetime.datetime.strptime(usage_date_numeric, "%Y%m%d").date()
        parsed.append({"date": dt, "cost": cost, "currency": currency})
    return parsed


def fetch_daily_costs(subscription_id: str,
                      timeframe: str = "Last7Days",
                      custom_from: Optional[datetime.date] = None,
                      custom_to: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    High-level helper to fetch and parse daily costs.
    If timeframe='Custom', both custom_from and custom_to required.

    Returns dict with keys: raw, records, currency, total_cost, avg_daily_cost
    """
    time_period = None
    if timeframe == "Custom":
        if not (custom_from and custom_to):
            raise ValueError("custom_from and custom_to required for Custom timeframe")
        time_period = {
            "from": custom_from.isoformat() + "T00:00:00Z",
            "to": custom_to.isoformat() + "T00:00:00Z"
        }

    response = query_cost_management(
        subscription_id=subscription_id,
        timeframe=timeframe,
        time_period=time_period
    )
    records = _parse_cost_response(response)
    if not records:
        return {
            "raw": response,
            "records": [],
            "currency": None,
            "total_cost": 0.0,
            "avg_daily_cost": 0.0
        }
    currency = records[0]["currency"]
    total_cost = sum(r["cost"] for r in records)
    avg_daily = total_cost / len(records)
    return {
        "raw": response,
        "records": sorted(records, key=lambda r: r["date"]),
        "currency": currency,
        "total_cost": total_cost,
        "avg_daily_cost": avg_daily
    }


if __name__ == "__main__":
    # Basic manual test (ensure creds valid)
    SUB_ID = "0b100b44-fb20-415e-b735-4594f153619b"
    data = fetch_daily_costs(SUB_ID, timeframe="Last7Days")
    from pprint import pprint
    pprint(data)