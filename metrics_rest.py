#!/usr/bin/env python
"""
metrics_web.py

FastAPI service (and CLI tool) to expose Azure OpenAI (Azure Cognitive Services)
token usage and latency metrics via the Azure Monitor Metrics REST API.

Auth:
  Uses Azure AD via DefaultAzureCredential with helper:
      def _get_token() -> str:
          credential = DefaultAzureCredential()
          token = credential.get_token("https://management.azure.com/.default").token
          return token

NEW (CLI Mode):
  When executed directly (python metrics_web.py) this script no longer launches uvicorn.
  Instead it runs a one-shot metrics query (using the same internal logic as the API)
  and prints JSON to stdout. You can pass CLI arguments to customize the query.

Run as API (unchanged) with uvicorn:
  uvicorn metrics_web:app --host 0.0.0.0 --port 8000

Run as CLI:
  python metrics_web.py --hours 6 --include-latency
  python metrics_web.py --start 2025-09-23T00:00:00Z --end 2025-09-23T06:00:00Z --include-latency --raw
  python metrics_web.py --hours 4 --interval PT5M --include-optional --include-latency

Requirements:
  pip install fastapi uvicorn requests python-dotenv pydantic azure-identity

Environment (.env) for resource resolution:
  RESOURCE_ID
    OR (all three)
      AZ_SUBSCRIPTION_ID
      AZ_RESOURCE_GROUP
      AZ_COG_ACCOUNT

Optional:
  PORT (only used when serving via uvicorn separately)

Metrics:
  Token: PromptTokens, CompletionTokens, TotalTokens (+ InputTokens, OutputTokens if requested)
  Latency: SuccessLatency, TotalLatency with Average + P50/P95/P99 (weighted average computed)

Caching:
  30 second in‑memory cache (applies to API use; CLI one‑shot won't benefit unless multiple
  queries are run within same process execution).

Troubleshooting:
  400: metricnamespace mismatch, invalid metric name, bad timespan, unsupported aggregation
  403: Identity lacks Reader / Monitoring Reader on the Cognitive Services resource
  401: Credential chain failed (e.g., no managed identity, no Azure CLI login, etc.)

Author: (Your Team)
"""

from __future__ import annotations

import os
import time
import json
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv()

# -----------------------------------------------------------------------------
# Constants / Config
# -----------------------------------------------------------------------------
AZURE_MONITOR_API_VERSION = "2024-02-01"
DEFAULT_HOURS = 1
MAX_HOURS = 48
METRIC_NAMESPACE = "microsoft.cognitiveservices/accounts"

PRIMARY_TOKEN_METRICS = ["ProcessedPromptTokens", "GeneratedTokens", "ContentSafetyTextAnalyzeRequestCount"]
OPTIONAL_TOKEN_METRICS = ["InputTokens", "OutputTokens", "TotalTokens"]
LATENCY_METRICS = ["Latency", "TimeToResponse"]

CACHE_TTL_SECONDS = 30
ALLOWED_INTERVAL_PREFIX = "PT"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metrics_web")

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(title="Azure OpenAI Metrics Service (AAD Auth)")

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class LatencySummary(BaseModel):
    success_latency_avg_ms: Optional[float] = None
    success_latency_p50_ms: Optional[float] = None
    success_latency_p95_ms: Optional[float] = None
    success_latency_p99_ms: Optional[float] = None
    total_latency_avg_ms: Optional[float] = None
    total_latency_p50_ms: Optional[float] = None
    total_latency_p95_ms: Optional[float] = None
    total_latency_p99_ms: Optional[float] = None

class MetricsSummary(BaseModel):
    timeframe_start: str
    timeframe_end: str
    interval: Optional[str] = None
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    total_tokens_total: int = 0
    input_tokens_total: Optional[int] = None
    output_tokens_total: Optional[int] = None
    missing_token_metrics: List[str] = Field(default_factory=list)
    latency: Optional[LatencySummary] = None
    missing_latency_metrics: List[str] = Field(default_factory=list)

class MetricsResponse(BaseModel):
    summary: MetricsSummary
    azure_monitor_request_url: str
    raw_metrics: Optional[Dict[str, Any]] = None

# -----------------------------------------------------------------------------
# Authentication helper (per user request)
# -----------------------------------------------------------------------------
def _get_token() -> str:
    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default").token
    return token

# -----------------------------------------------------------------------------
# Resource ID
# -----------------------------------------------------------------------------
def resolve_resource_id() -> str:
    explicit = os.getenv("RESOURCE_ID")
    if explicit:
        if not explicit.startswith("/"):
            explicit = "/" + explicit
        return explicit
    sub = os.getenv("AZURE_SUB_ID")
    rg = os.getenv("AZURE_RESOURCE_GROUP")
    acct = os.getenv("AZURE_ACCOUNT")
    if not all([sub, rg, acct]):
        raise RuntimeError(
            "Provide RESOURCE_ID or AZ_SUBSCRIPTION_ID, AZ_RESOURCE_GROUP, AZ_COG_ACCOUNT."
        )
    return f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{acct}"

# -----------------------------------------------------------------------------
# Time Handling
# -----------------------------------------------------------------------------
def parse_time_params(
        hours: Optional[int],
        start: Optional[str],
        end: Optional[str]
) -> Tuple[datetime, datetime]:
    if hours is not None and (start or end):
        raise ValueError("Specify either hours OR (start & end), not both.")
    if hours is None and (start is None or end is None):
        hours = DEFAULT_HOURS
    if hours is not None:
        if hours < 1 or hours > MAX_HOURS:
            raise ValueError(f"hours must be between 1 and {MAX_HOURS}")
        end_dt = datetime.now(timezone.utc).replace(microsecond=0)
        start_dt = end_dt - timedelta(hours=hours)
        return start_dt, end_dt
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except Exception:
        raise ValueError("start/end must be ISO8601 (e.g., 2025-09-23T00:00:00Z)")
    if start_dt >= end_dt:
        raise ValueError("start must be before end.")
    return start_dt, end_dt

def build_timespan(start_dt: datetime, end_dt: datetime) -> str:
    return f"{start_dt.isoformat().replace('+00:00','Z')}/{end_dt.isoformat().replace('+00:00','Z')}"

# -----------------------------------------------------------------------------
# Azure Monitor REST
# -----------------------------------------------------------------------------
def build_metrics_url(resource_id: str) -> str:
    return f"https://management.azure.com{resource_id}/providers/microsoft.insights/metrics"

def diagnose_400(resp: requests.Response) -> str:
    try:
        text = resp.text.lower()
    except Exception:
        return "Unknown cause."
    if "invalid timespan" in text:
        return "Invalid timespan (check start/end ISO8601)."
    if "metricnamespace" in text and "invalid" in text:
        return "Verify metricnamespace=microsoft.cognitiveservices/accounts."
    if "metricname" in text and "not found" in text:
        return "Invalid metric name; call /metric-definitions."
    if "aggregation" in text and "invalid" in text:
        return "Check aggregation set; for latency use Total,Average,Percentile,Count."
    return "Check names, namespace, timespan, API version."

def request_metrics(
        resource_id: str,
        metric_names: List[str],
        start_dt: datetime,
        end_dt: datetime,
        interval: Optional[str],
        include_latency: bool
) -> Dict[str, Any]:
    token = _get_token()
    timespan = build_timespan(start_dt, end_dt)

    if include_latency:
        aggregation = "Total,Average,Percentile,Count"
        percentile = "50,95,99"
    else:
        aggregation = "Total"
        percentile = None

    params = {
        "metricnames": ",".join(metric_names),
        "metricnamespace": METRIC_NAMESPACE,
        "timespan": timespan,
        "aggregation": aggregation,
        "api-version": AZURE_MONITOR_API_VERSION,
    }
    if percentile:
        params["percentile"] = percentile
    if interval:
        params["interval"] = interval

    url = build_metrics_url(resource_id)
    headers = {"Authorization": f"Bearer {token}"}

    logger.info("Azure Monitor query params: %s", params)
    resp = requests.get(url, headers=headers, params=params, timeout=40)

    if resp.status_code == 400:
        hint = diagnose_400(resp)
        raise HTTPException(status_code=400, detail=f"Azure Monitor 400: {resp.text}. Hint: {hint}")
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized (AAD credential issue or missing permissions).")
    if resp.status_code == 403:
        raise HTTPException(status_code=403, detail="Forbidden. Principal likely lacks Reader/Monitoring Reader on the resource.")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Not found: {resp.text}")
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=f"Azure Monitor error: {resp.text}")

    return {"url": resp.url, "payload": resp.json()}

# -----------------------------------------------------------------------------
# Aggregation
# -----------------------------------------------------------------------------
def aggregate_token_metrics(raw_payload: Dict[str, Any]) -> Dict[str, int]:
    sums: Dict[str, int] = {}
    for metric_entry in raw_payload.get("value", []):
        name = metric_entry.get("name", {}).get("value")
        if name not in PRIMARY_TOKEN_METRICS and name not in OPTIONAL_TOKEN_METRICS:
            continue
        total_sum = 0
        for ts in metric_entry.get("timeseries", []):
            for dp in ts.get("data", []):
                val = dp.get("total")
                if val is not None:
                    total_sum += int(val)
        sums[name] = total_sum
    return sums

def extract_latency_metrics(raw_payload: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    results: Dict[str, Dict[str, float]] = {}
    for metric_entry in raw_payload.get("value", []):
        name = metric_entry.get("name", {}).get("value")
        if name not in LATENCY_METRICS:
            continue
        total_weighted = 0.0
        total_count = 0
        simple_avgs: List[float] = []
        p50_vals: List[float] = []
        p95_vals: List[float] = []
        p99_vals: List[float] = []
        count_present = False

        for ts in metric_entry.get("timeseries", []):
            for dp in ts.get("data", []):
                avg = dp.get("average")
                count = dp.get("count")
                p50 = dp.get("percentile50")
                p95 = dp.get("percentile95")
                p99 = dp.get("percentile99")

                if avg is not None:
                    if count is not None:
                        total_weighted += avg * count
                        total_count += count
                        count_present = True
                    else:
                        simple_avgs.append(avg)
                if p50 is not None:
                    p50_vals.append(p50)
                if p95 is not None:
                    p95_vals.append(p95)
                if p99 is not None:
                    p99_vals.append(p99)

        if count_present and total_count > 0:
            weighted_avg = total_weighted / total_count
        elif simple_avgs:
            weighted_avg = sum(simple_avgs) / len(simple_avgs)
        else:
            weighted_avg = None

        def last_or_none(vals: List[float]) -> Optional[float]:
            return vals[-1] if vals else None

        results[name] = {
            "avg": weighted_avg,
            "p50": last_or_none(p50_vals),
            "p95": last_or_none(p95_vals),
            "p99": last_or_none(p99_vals),
        }
    return results

# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------
_cache: Dict[str, Dict[str, Any]] = {}

def cache_key(
        resource_id: str,
        timespan: str,
        interval: Optional[str],
        include_optional_tokens: bool,
        include_latency: bool,
        raw: bool
) -> str:
    return json.dumps({
        "r": resource_id,
        "t": timespan,
        "i": interval,
        "opt": include_optional_tokens,
        "lat": include_latency,
        "raw": raw
    }, sort_keys=True)

def get_cached(key: str) -> Optional[Dict[str, Any]]:
    entry = _cache.get(key)
    if not entry:
        return None
    if (time.time() - entry["ts"]) > CACHE_TTL_SECONDS:
        return None
    return entry["data"]

def set_cache(key: str, data: Dict[str, Any]) -> None:
    _cache[key] = {"ts": time.time(), "data": data}

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/", summary="Root")
def root():
    return {
        "service": "Azure OpenAI Metrics (AAD Auth)",
        "endpoints": ["/token-usage", "/metrics/prometheus", "/metric-definitions", "/healthz"],
        "auth": "DefaultAzureCredential",
    }

@app.get("/metric-definitions", summary="List available metrics")
def metric_definitions():
    resource_id = resolve_resource_id()
    url = (
        f"https://management.azure.com{resource_id}"
        f"/providers/microsoft.insights/metricDefinitions"
        f"?api-version={AZURE_MONITOR_API_VERSION}"
    )
    token = _get_token()
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@app.get("/token-usage", response_model=MetricsResponse, summary="Aggregated token and (optional) latency metrics")
def token_usage(
        hours: Optional[int] = Query(None, ge=1, le=MAX_HOURS),
        start: Optional[str] = Query(None),
        end: Optional[str] = Query(None),
        interval: Optional[str] = Query(None, description="ISO8601 duration (e.g., PT5M)"),
        include_optional_tokens: bool = Query(False),
        include_latency: bool = Query(False),
        raw: bool = Query(False),
):
    if interval and not interval.startswith(ALLOWED_INTERVAL_PREFIX):
        raise HTTPException(status_code=400, detail="interval must start with 'PT' (e.g., PT5M).")

    try:
        start_dt, end_dt = parse_time_params(hours, start, end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    resource_id = resolve_resource_id()
    timespan = build_timespan(start_dt, end_dt)
    key = cache_key(resource_id, timespan, interval, include_optional_tokens, include_latency, raw)
    cached = get_cached(key)
    if cached:
        return cached

    metric_names = list(PRIMARY_TOKEN_METRICS)
    if include_optional_tokens:
        metric_names.extend(OPTIONAL_TOKEN_METRICS)
    if include_latency:
        metric_names.extend(LATENCY_METRICS)

    try:
        result = request_metrics(
            resource_id=resource_id,
            metric_names=metric_names,
            start_dt=start_dt,
            end_dt=end_dt,
            interval=interval,
            include_latency=include_latency
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error requesting metrics")
        raise HTTPException(status_code=500, detail=str(e))

    payload = result["payload"]

    # Token aggregation
    token_sums = aggregate_token_metrics(payload)
    missing_token_metrics = [m for m in PRIMARY_TOKEN_METRICS if m not in token_sums]
    if include_optional_tokens:
        missing_token_metrics.extend([m for m in OPTIONAL_TOKEN_METRICS if m not in token_sums])

    # Latency
    latency_summary: Optional[LatencySummary] = None
    missing_latency_metrics: List[str] = []
    if include_latency:
        latency_data = extract_latency_metrics(payload)
        for lm in LATENCY_METRICS:
            if lm not in latency_data:
                missing_latency_metrics.append(lm)
        latency_summary = LatencySummary(
            success_latency_avg_ms=latency_data.get("SuccessLatency", {}).get("avg"),
            success_latency_p50_ms=latency_data.get("SuccessLatency", {}).get("p50"),
            success_latency_p95_ms=latency_data.get("SuccessLatency", {}).get("p95"),
            success_latency_p99_ms=latency_data.get("SuccessLatency", {}).get("p99"),
            total_latency_avg_ms=latency_data.get("TotalLatency", {}).get("avg"),
            total_latency_p50_ms=latency_data.get("TotalLatency", {}).get("p50"),
            total_latency_p95_ms=latency_data.get("TotalLatency", {}).get("p95"),
            total_latency_p99_ms=latency_data.get("TotalLatency", {}).get("p99"),
        )

    summary = MetricsSummary(
        timeframe_start=start_dt.isoformat().replace("+00:00", "Z"),
        timeframe_end=end_dt.isoformat().replace("+00:00", "Z"),
        interval=interval,
        prompt_tokens_total=token_sums.get("PromptTokens", 0),
        completion_tokens_total=token_sums.get("CompletionTokens", 0),
        total_tokens_total=token_sums.get("TotalTokens", 0),
        input_tokens_total=token_sums.get("InputTokens"),
        output_tokens_total=token_sums.get("OutputTokens"),
        missing_token_metrics=missing_token_metrics,
        latency=latency_summary,
        missing_latency_metrics=missing_latency_metrics
    )

    response_obj = MetricsResponse(
        summary=summary,
        azure_monitor_request_url=result["url"],
        raw_metrics=payload if raw else None
    )
    data_dict = json.loads(response_obj.json())
    set_cache(key, data_dict)
    return data_dict

@app.get("/metrics/prometheus", summary="Prometheus exposition")
def prometheus_metrics(
        hours: Optional[int] = Query(1, ge=1, le=MAX_HOURS),
        include_optional_tokens: bool = Query(False),
        include_latency: bool = Query(False),
):
    resp = token_usage(
        hours=hours,
        start=None,
        end=None,
        interval=None,
        include_optional_tokens=include_optional_tokens,
        include_latency=include_latency,
        raw=False,
    )
    s = resp["summary"]
    lines = [
        "# HELP azure_openai_prompt_tokens_total Sum of prompt tokens in timeframe.",
        "# TYPE azure_openai_prompt_tokens_total gauge",
        f"azure_openai_prompt_tokens_total {s['prompt_tokens_total']}",
        "# HELP azure_openai_completion_tokens_total Sum of completion tokens in timeframe.",
        "# TYPE azure_openai_completion_tokens_total gauge",
        f"azure_openai_completion_tokens_total {s['completion_tokens_total']}",
        "# HELP azure_openai_total_tokens_total Sum of total tokens in timeframe.",
        "# TYPE azure_openai_total_tokens_total gauge",
        f"azure_openai_total_tokens_total {s['total_tokens_total']}",
    ]
    if s.get("input_tokens_total") is not None:
        lines += [
            "# HELP azure_openai_input_tokens_total Optional input tokens metric.",
            "# TYPE azure_openai_input_tokens_total gauge",
            f"azure_openai_input_tokens_total {s['input_tokens_total']}",
        ]
    if s.get("output_tokens_total") is not None:
        lines += [
            "# HELP azure_openai_output_tokens_total Optional output tokens metric.",
            "# TYPE azure_openai_output_tokens_total gauge",
            f"azure_openai_output_tokens_total {s['output_tokens_total']}",
        ]

    if include_latency and s.get("latency"):
        lat = s["latency"]

        def emit_latency(metric_name: str, value: Optional[float], help_text: str):
            if value is None:
                return []
            return [
                f"# HELP {metric_name} {help_text}",
                f"# TYPE {metric_name} gauge",
                f"{metric_name} {value}",
            ]

        lines += emit_latency("azure_openai_success_latency_avg_ms", lat.get("success_latency_avg_ms"),
                              "Weighted average success latency (ms).")
        lines += emit_latency("azure_openai_success_latency_p50_ms", lat.get("success_latency_p50_ms"),
                              "P50 success latency (ms).")
        lines += emit_latency("azure_openai_success_latency_p95_ms", lat.get("success_latency_p95_ms"),
                              "P95 success latency (ms).")
        lines += emit_latency("azure_openai_success_latency_p99_ms", lat.get("success_latency_p99_ms"),
                              "P99 success latency (ms).")
        lines += emit_latency("azure_openai_total_latency_avg_ms", lat.get("total_latency_avg_ms"),
                              "Weighted average total latency (ms).")
        lines += emit_latency("azure_openai_total_latency_p50_ms", lat.get("total_latency_p50_ms"),
                              "P50 total latency (ms).")
        lines += emit_latency("azure_openai_total_latency_p95_ms", lat.get("total_latency_p95_ms"),
                              "P95 total latency (ms).")
        lines += emit_latency("azure_openai_total_latency_p99_ms", lat.get("total_latency_p99_ms"),
                              "P99 total latency (ms).")

    return PlainTextResponse("\n".join(lines) + "\n")

@app.get("/healthz", summary="Health check")
def healthz():
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# CLI Entry Point (Replaces uvicorn launch in __main__)
# -----------------------------------------------------------------------------
def _cli():
    parser = argparse.ArgumentParser(
        description="One-shot Azure OpenAI metrics query (token + optional latency)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--hours", type=int, help="Last N hours (mutually exclusive with --start/--end).")
    group2 = parser.add_argument_group("Explicit timeframe")
    group2.add_argument("--start", type=str, help="Start time ISO8601 (e.g. 2025-09-23T00:00:00Z)")
    group2.add_argument("--end", type=str, help="End time ISO8601 (e.g. 2025-09-23T06:00:00Z)")

    parser.add_argument("--interval", type=str, help="Bucket interval ISO8601 (e.g. PT5M).")
    parser.add_argument("--include-optional", action="store_true", help="Include InputTokens/OutputTokens.")
    parser.add_argument("--include-latency", action="store_true", help="Include latency metrics.")
    parser.add_argument("--raw", action="store_true", help="Include raw Azure Monitor payload.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args()

    try:
        result = token_usage(
            hours=args.hours,
            start=args.start,
            end=args.end,
            interval=args.interval,
            include_optional_tokens=args.include_optional,
            include_latency=args.include_latency,
            raw=args.raw,
        )
    except HTTPException as he:
        # Graceful CLI error display
        print(json.dumps({"error": he.status_code, "detail": he.detail}, indent=2))
        return
    except Exception as e:
        print(json.dumps({"error": "unexpected", "detail": str(e)}, indent=2))
        return

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))

if __name__ == "__main__":
    _cli()