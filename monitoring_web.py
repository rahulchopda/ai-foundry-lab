"""
monitoring_web.py

All monitoring logic (operational + cost metrics). The cost management
module was renamed from cost_management.py to cost_rest.py.
"""

from __future__ import annotations
import datetime
import random
import json
from typing import Dict, Any, List, Optional

import streamlit as st

# Updated import after rename
try:
    from cost_rest import fetch_daily_costs
    _COST_AVAILABLE = True
except Exception:
    _COST_AVAILABLE = False


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
        f"<div style='width:100%;background:linear-gradient(180deg,#0051a8,#002855);height:{(p['v']/max_v)*100:.2f}%;border-radius:2px;'></div>"
        "</div>"
        for p in series
    )
    return f"""
    <div style="display:flex;gap:2px;align-items:flex-end;height:40px;">{bars}</div>
    <div style="font-size:0.6rem;color:#555;margin-top:4px;">Last {len(values)} pts</div>
    """


def _cost_line_area_svg(records: List[Dict[str, Any]], width=760, height=240, stroke="#0051a8") -> str:
    if not records:
        return "<div>No cost data</div>"
    padding = 40
    dates = [r["date"] for r in records]
    costs = [r["cost"] for r in records]
    min_cost = 0
    max_cost = max(costs) or 1
    date_min = min(dates)
    date_max = max(dates)
    span = (date_max - date_min).days or 1

    def x_pos(d):
        return padding + ((d - date_min).days / span) * (width - 2 * padding)

    def y_pos(c):
        return height - padding - ((c - min_cost) / (max_cost - min_cost)) * (height - 2 * padding)

    first_point = f"M {x_pos(dates[0])} {y_pos(costs[0])}"
    line_segments = " ".join(f"L {x_pos(d)} {y_pos(c)}" for d, c in zip(dates, costs))
    line_path = f"{first_point} {line_segments}"
    area_path = f"{line_path} L {x_pos(dates[-1])} {height - padding} L {x_pos(dates[0])} {height - padding} Z"

    tick_elems = []
    for d in dates:
        x = x_pos(d)
        tick_elems.append(f"<line x1='{x}' y1='{height - padding}' x2='{x}' y2='{height - padding + 6}' stroke='#888' stroke-width='1'/>")
        tick_elems.append(f"<text x='{x}' y='{height - padding + 18}' font-size='10' text-anchor='middle' fill='#444'>{d.strftime('%m-%d')}</text>")
    for i in range(0, 6):
        val = min_cost + (i / 5) * (max_cost - min_cost)
        y = y_pos(val)
        tick_elems.append(f"<line x1='{padding - 6}' y1='{y}' x2='{padding}' y2='{y}' stroke='#888' stroke-width='1'/>")
        tick_elems.append(f"<text x='{padding - 10}' y='{y + 3}' font-size='10' text-anchor='end' fill='#444'>{val:.1f}</text>")
        tick_elems.append(f"<line x1='{padding}' y1='{y}' x2='{width - padding}' y2='{y}' stroke='#eaecef' stroke-width='1'/>")

    return f"""
    <svg width="{width}" height="{height}" role="img" aria-label="Daily Cost Trend">
        <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" rx="6" ry="6" />
        <defs>
            <linearGradient id="gradCostArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="{stroke}" stop-opacity="0.55"/>
                <stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <path d="{area_path}" fill="url(#gradCostArea)" stroke="none" opacity="0.85"></path>
        <path d="{line_path}" fill="none" stroke="{stroke}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"></path>
        {''.join(tick_elems)}
    </svg>
    """


def _cost_pie_svg(records: List[Dict[str, Any]], diameter=300) -> str:
    if not records:
        return "<div>No cost data</div>"
    import math
    total = sum(r["cost"] for r in records) or 1
    cx = cy = diameter / 2
    radius = (diameter / 2) - 4
    palette = [
        "#002855", "#0051a8", "#0072ce", "#338fce", "#5aa4d6",
        "#7fb9de", "#a6cee6", "#c3dbed", "#d9e7f3", "#b2d4ff",
        "#4d7fb3", "#1b4f72", "#41729f", "#2f6690", "#398cbf"
    ]
    segments = []
    accum_angle = 0.0
    for idx, r in enumerate(records):
        fraction = r["cost"] / total
        angle = fraction * 2 * math.pi
        start_angle = accum_angle
        end_angle = accum_angle + angle
        accum_angle += angle
        x1 = cx + radius * math.sin(start_angle)
        y1 = cy - radius * math.cos(start_angle)
        x2 = cx + radius * math.sin(end_angle)
        y2 = cy - radius * math.cos(end_angle)
        large_arc = 1 if angle > math.pi else 0
        path_d = f"M {cx} {cy} L {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} Z"
        color = palette[idx % len(palette)]
        segments.append(
            f"<path d='{path_d}' fill='{color}' stroke='#ffffff' stroke-width='1'>"
            f"<title>{r['date'].strftime('%Y-%m-%d')} : {r['cost']:.2f}</title></path>"
        )
    legend_items = []
    for idx, r in enumerate(records):
        color = palette[idx % len(palette)]
        pct = (r["cost"] / total) * 100
        legend_items.append(
            f"<div style='display:flex;align-items:center;font-size:11px;margin-bottom:4px;'>"
            f"<span style='display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;margin-right:6px;"
            f"border:1px solid #fff;box-shadow:0 0 0 1px #eaecef;'></span>"
            f"{r['date'].strftime('%m-%d')}: {r['cost']:.2f} ({pct:.1f}%)</div>"
        )
    return f"""
    <div style="display:flex;flex-wrap:wrap;gap:1.2rem;">
        <svg width="{diameter}" height="{diameter}" viewBox="0 0 {diameter} {diameter}" role="img" aria-label="Cost Distribution by Day">
            <circle cx="{cx}" cy="{cy}" r="{radius}" fill="#f8fafc" stroke="#eaecef" stroke-width="1"/>
            {''.join(segments)}
        </svg>
        <div style="flex:1;min-width:180px;display:flex;flex-direction:column;flex-wrap:nowrap;">
            <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin-bottom:6px;">Daily Distribution</div>
            {''.join(legend_items)}
        </div>
    </div>
    """


def _build_cost_section(subscription_id: str, timeframe: str) -> str:
    if not _COST_AVAILABLE:
        return """
        <div class="ms-card" style="margin-top:1.5rem;">
            <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics</h3>
            <div style="color:#a00;font-size:0.85rem;">cost_rest module not available.</div>
        </div>
        """
    try:
        result = fetch_daily_costs(subscription_id, timeframe=timeframe)
    except Exception as e:
        return f"""
        <div class="ms-card" style="margin-top:1.5rem;">
            <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics</h3>
            <div style="color:#a00;font-size:0.85rem;">Failed to fetch cost data: {e}</div>
        </div>
        """

    records = result.get("records", [])
    if not records:
        return """
        <div class="ms-card" style="margin-top:1.5rem;">
            <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics</h3>
            <div style="font-size:0.85rem;">No cost data returned for selected timeframe.</div>
        </div>
        """

    currency = result["currency"]
    total_cost = result["total_cost"]
    avg_daily_cost = result["avg_daily_cost"]
    latest = records[-1]

    if len(records) > 1:
        prev = records[-2]["cost"]
        delta_pct = ((latest["cost"] - prev) / prev) * 100 if prev > 0 else 0
        delta_str = f"{delta_pct:+.2f}% vs prev day" if prev > 0 else "n/a"
    else:
        delta_str = "n/a"

    summary_html = f"""
    <div style="display:flex;flex-wrap:wrap;margin:-0.4rem;">
        {_metric_block("Timeframe", timeframe, highlight=True)}
        {_metric_block("Total Cost", f"{total_cost:.2f} {currency}")}
        {_metric_block("Avg Daily", f"{avg_daily_cost:.2f} {currency}")}
        {_metric_block("Latest ({latest_date})".format(latest_date=latest['date'].strftime('%m-%d')), f"{latest['cost']:.2f} {currency}")}
        {_metric_block("Day Change", delta_str)}
        {_metric_block("Data Points", len(records))}
    </div>
    """

    line_svg = _cost_line_area_svg(records)
    pie_svg = _cost_pie_svg(records)

    last_slice = records[-7:] if len(records) > 7 else records
    table_rows = "".join(
        f"<tr><td style='padding:4px 8px;font-weight:600;color:#002855'>{r['date']}</td>"
        f"<td style='padding:4px 8px;text-align:right;'>{r['cost']:.2f}</td></tr>"
        for r in last_slice
    )
    table_html = f"""
    <table style="width:100%;border-collapse:collapse;font-size:0.70rem;">
        <thead>
            <tr>
                <th style="text-align:left;padding:6px 8px;color:#0051a8;">Date</th>
                <th style="text-align:right;padding:6px 8px;color:#0051a8;">PreTaxCost ({currency})</th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
    """

    cost_html = f"""
    <div class="ms-card" style="margin-top:1.3rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics (Azure Cost Management)</h3>
        {summary_html}
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1.25rem;margin-top:1rem;">
            <div>
                <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin-bottom:6px;">Daily Cost Trend</div>
                <div style="overflow:auto;">{line_svg}</div>
            </div>
            <div>
                <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin-bottom:6px;">Distribution by Day</div>
                <div style="overflow:auto;">{pie_svg}</div>
            </div>
            <div>
                <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin-bottom:6px;">Recent Days</div>
                <div class="ms-card" style="padding:0.7rem 0.7rem 0.4rem 0.7rem;margin:0;border:1px solid #eaecef;">
                    {table_html}
                </div>
            </div>
        </div>
        <div style="text-align:right;font-size:0.6rem;color:#555;margin-top:0.75rem;">
            Generated {datetime.datetime.utcnow().isoformat()}Z — Currency: {currency}
        </div>
    </div>
    """
    return cost_html


def _build_operational_section(governance_metrics: Dict[str, Any], model_costs: Dict[str, Any]) -> str:
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
        <pre style="font-size:0.6rem;max-height:250px;overflow:auto;background:#f7f8fa;padding:0.9rem;border:1px solid #eaecef;border-radius:8px;">{json.dumps(raw_json, indent=2)}</pre>
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


def render_monitoring_tab(
        subscription_id: Optional[str],
        governance_metrics: Dict[str, Any],
        model_costs: Dict[str, Any],
        default_timeframe: str = "Last7Days"
):
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        timeframe = st.selectbox("Cost Timeframe", ["Last7Days", "MonthToDate"],
                                 index=0 if default_timeframe == "Last7Days" else 1)
    with col2:
        refresh = st.button("Refresh Monitoring Data")
    with col3:
        show_raw_cost_table = st.checkbox("Show Full Cost Table", value=False)

    if refresh:
        st.session_state["monitoring_refresh_counter"] = st.session_state.get("monitoring_refresh_counter", 0) + 1

    operational_html = _build_operational_section(governance_metrics, model_costs)

    cost_html = ""
    full_cost_records: List[Dict[str, Any]] = []
    if subscription_id:
        try:
            if _COST_AVAILABLE:
                cost_result = fetch_daily_costs(subscription_id, timeframe=timeframe)
                full_cost_records = cost_result.get("records", [])
                cost_html = _build_cost_section(subscription_id, timeframe)
            else:
                cost_html = "<div class='ms-card' style='margin-top:1rem;'>Cost module unavailable.</div>"
        except Exception as e:
            cost_html = f"<div class='ms-card' style='margin-top:1rem;color:#a00;'>Failed to fetch cost data: {e}</div>"
    else:
        cost_html = "<div class='ms-card' style='margin-top:1rem;'>No subscription configured for cost metrics.</div>"

    st.components.v1.html(operational_html + cost_html, height=2400, scrolling=True)

    if show_raw_cost_table and full_cost_records:
        import pandas as pd
        df = pd.DataFrame(full_cost_records)
        st.markdown("#### Full Cost Records")
        st.dataframe(df, use_container_width=True)