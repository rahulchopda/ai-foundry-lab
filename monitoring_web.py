"""
monitoring_web.py

Refactored:
- Cost rendering moved to cost_web.render_cost_section
- Added latency section from latency_web.render_latency_section (stacked bar replacement visualization)
- Removed previous in-file cost functions & pie chart
"""

from __future__ import annotations
import random
import json
from typing import Dict, Any, List, Optional

import streamlit as st

from cost_web import render_cost_section
from latency_web import render_latency_section


# ---------------- Operational Helpers (retained) ---------------- #

def _metric_block(label: str, value, highlight=False) -> str:
    border = "border:2px solid #0051a8;" if highlight else "border:1.5px solid #eaecef;"
    return f"""
    <div style="flex:1;min-width:170px;margin:0.4rem;">
        <div class="ms-card" style="padding:1rem 0.9rem;{border}">
            <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;color:#0051a8;font-weight:600;margin-bottom:0.3rem;">
                {label}
            </div>
            <div style="font-size:1.15rem;font-weight:600;color:#002855;word-break:break-word;">{value}</div>
        </div>
    </div>
    """


def _simple_table(title: str, rows: Dict[str, str]) -> str:
    trs = "".join(
        f"<tr><td style='padding:5px 8px;font-weight:600;color:#002855'>{k}</td>"
        f"<td style='padding:5px 8px;color:#1a1a1a'>{v}</td></tr>"
        for k, v in rows.items()
    )
    return f"""
    <div class="ms-card" style="margin-bottom:1rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.05rem;">{title}</h3>
        <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
            <tbody>{trs}</tbody>
        </table>
    </div>
    """


def _generate_fake_timeseries(name: str, points: int = 24) -> Dict[str, Any]:
    import datetime
    import math
    now = datetime.datetime.utcnow()
    data = []
    base = random.uniform(50, 200)
    for i in range(points):
        ts = now - datetime.timedelta(minutes=30 * (points - i))
        variation = math.sin(i / 3.5) * 0.15 * base + random.uniform(-0.1, 0.1) * base
        val = max(0, base + variation)
        data.append({"t": ts.isoformat() + "Z", "v": round(val, 2)})
    return {"name": name, "series": data}


def _sparkline_html(series_struct: Dict[str, Any]) -> str:
    series = series_struct["series"]
    values = [p["v"] for p in series]
    if not values:
        return "<div>No data</div>"
    max_v = max(values) or 1
    bars = "".join(
        f"<div title='{p['v']}' style='flex:1;height:40px;display:flex;align-items:flex-end;'>"
        f"<div style='width:100%;background:linear-gradient(180deg,#0051a8,#002855);"
        f"height:{(p['v']/max_v)*100:.2f}%;border-radius:2px;'></div>"
        "</div>"
        for p in series
    )
    return f"""
    <div style="display:flex;gap:2px;align-items:flex-end;height:40px;">{bars}</div>
    <div style="font-size:0.6rem;color:#555;margin-top:4px;">Last {len(values)} pts</div>
    """


def _build_operational_section(governance_metrics: Dict[str, Any],
                               model_costs: Dict[str, Any]) -> str:
    req_series = _generate_fake_timeseries("Request Count", 30)
    latency_series = _generate_fake_timeseries("Latency (ms)", 30)
    token_series = _generate_fake_timeseries("Tokens Used", 30)

    top_metrics_html = """
    <div style="display:flex;flex-wrap:wrap;margin:-0.4rem;">
        {blocks}
    </div>
    """.format(
        blocks="".join([
            _metric_block("Total Requests (24h)", random.randint(500, 1800), highlight=True),
            _metric_block("Avg Latency (ms)", round(random.uniform(120, 480), 1)),
            _metric_block("Avg Tokens / Req", round(random.uniform(320, 1400), 1)),
            _metric_block("Safety Flags (24h)", random.randint(0, 12)),
            _metric_block("Errors (24h)", random.randint(0, 5)),
            _metric_block("Active Models", len(model_costs) or 0),
        ])
    )

    governance_html = _simple_table("Governance & Compliance", governance_metrics)
    config_cost_html = _simple_table(
        "Configured Model Costs",
        {m: f"${c}/1M tokens" for m, c in model_costs.items()} or {"No Models": "N/A"}
    )

    trends_html = f"""
    <div class="ms-card" style="margin-bottom:1rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.05rem;">Operational Trends</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem;">
            <div>
                <div style="font-size:0.65rem;font-weight:600;color:#0051a8;margin-bottom:4px;">Request Volume</div>
                {_sparkline_html(req_series)}
            </div>
            <div>
                <div style="font-size:0.65rem;font-weight:600;color:#0051a8;margin-bottom:4px;">Latency (ms)</div>
                {_sparkline_html(latency_series)}
            </div>
            <div>
                <div style="font-size:0.65rem;font-weight:600;color:#0051a8;margin-bottom:4px;">Tokens Used</div>
                {_sparkline_html(token_series)}
            </div>
        </div>
    </div>
    """

    raw_json = {
        "request_timeseries": req_series,
        "latency_timeseries": latency_series,
        "token_timeseries": token_series,
    }
    raw_html = f"""
    <div class="ms-card">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.05rem;">Raw Monitoring Data (Sample)</h3>
        <pre style="font-size:0.6rem;max-height:250px;overflow:auto;background:#f7f8fa;
                    padding:0.9rem;border:1px solid #eaecef;border-radius:8px;">{json.dumps(raw_json, indent=2)}</pre>
    </div>
    """

    combined = f"""
    {top_metrics_html}
    {trends_html}
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:1.1rem;">
        <div>{governance_html}</div>
        <div>{config_cost_html}</div>
    </div>
    {raw_html}
    """
    return combined


# ---------------- Public Entry Point ---------------- #

def render_monitoring_tab(
        subscription_id: Optional[str],
        governance_metrics: Dict[str, Any],
        model_costs: Dict[str, Any],
        default_timeframe: str = "Last7Days"
):
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        timeframe = st.selectbox("Cost Timeframe",
                                 ["Last7Days", "MonthToDate"],
                                 index=0 if default_timeframe == "Last7Days" else 1)
    with col2:
        refresh = st.button("Refresh Monitoring Data")
    with col3:
        show_raw_cost_table = st.checkbox("Show Full Cost Table", value=False)

    if refresh:
        st.session_state["monitoring_refresh_counter"] = \
            st.session_state.get("monitoring_refresh_counter", 0) + 1

    operational_html = _build_operational_section(governance_metrics, model_costs)

    cost_html = ""
    latency_html = ""
    full_cost_records: List[Dict[str, Any]] = []

    # Cost Section
    if subscription_id:
        cost_html, full_cost_records = render_cost_section(subscription_id, timeframe)
    else:
        cost_html = "<div class='ms-card' style='margin-top:1rem;'>No subscription configured for cost metrics.</div>"

    # Latency Section (replacement visualization)
    latency_html = render_latency_section(list(model_costs.keys()))

    #Performance
    # Latency Section (replacement visualization)
    from monitoring_webPage import render_latency_section

    latency_html, df = render_latency_section(metric_name="Latency", unit="ms")
    # Use html_snippet in your web page/app
    #latency_html = render_latency_section(list(model_costs.keys()))
    
    # Compose
    st.components.v1.html(
        operational_html + cost_html + latency_html,
        height=2300,
        scrolling=True
    )

    if show_raw_cost_table and full_cost_records:
        import pandas as pd
        df = pd.DataFrame(full_cost_records)
        st.markdown("#### Full Cost Records")
        st.dataframe(df, use_container_width=True)
