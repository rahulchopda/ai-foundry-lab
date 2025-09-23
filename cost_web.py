"""
cost_web.py

Encapsulates cost metrics rendering logic (migrated from monitoring_web.py).
Pie / distribution chart removed per earlier request.

Exports:
    render_cost_section(subscription_id: str, timeframe: str) -> (str, List[Dict[str, Any]])
        Returns (html_snippet, records_list)

Change Log:
2025-09-23 (Layout update):
    - Daily Cost Trend vs Recent Days changed from (4fr 1fr ~80/20) to an explicit flex layout
      with Daily Cost Trend occupying ~75% width (flex:3) and Recent Days ~25% (flex:1).
    - Made the trend SVG responsive (scales to container width).
    - Added alternating row striping to Recent Days table.
"""

from __future__ import annotations
import datetime
from typing import Any, Dict, List, Tuple

try:
    from cost_rest import fetch_daily_costs
    _COST_AVAILABLE = True
except Exception:  # pragma: no cover
    _COST_AVAILABLE = False


# ---- Internal Helpers ---- #

def _metric_block(label: str, value, highlight: bool = False) -> str:
    border = "border:2px solid #0051a8;" if highlight else "border:1.5px solid #eaecef;"
    return f"""
    <div style="flex:1;min-width:170px;margin:0.4rem;">
        <div class="ms-card" style="padding:1rem 0.9rem;{border}">
            <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;
                        color:#0051a8;font-weight:600;margin-bottom:0.3rem;">
                {label}
            </div>
            <div style="font-size:1.15rem;font-weight:600;color:#002855;word-break:break-word;">{value}</div>
        </div>
    </div>
    """


def _cost_line_area_svg(records: List[Dict[str, Any]],
                        width: int = 1200,
                        height: int = 260,
                        stroke: str = "#0051a8") -> str:
    """
    Generates an inline SVG for the daily cost trend.
    Width is set via viewBox for responsiveness (rendered at 100% of container).
    """
    if not records:
        return "<div>No cost data</div>"

    padding = 40
    dates = [r["date"] for r in records]
    costs = [r["cost"] for r in records]
    min_cost = 0
    max_cost = max(costs) or 1
    date_min = min(dates)
    date_max = max(dates)
    span_days = (date_max - date_min).days or 1

    def x_pos(d):
        return padding + ((d - date_min).days / span_days) * (width - 2 * padding)

    def y_pos(c):
        return height - padding - ((c - min_cost) / (max_cost - min_cost)) * (height - 2 * padding)

    first_point = f"M {x_pos(dates[0])} {y_pos(costs[0])}"
    line_segments = " ".join(f"L {x_pos(d)} {y_pos(c)}" for d, c in zip(dates, costs))
    line_path = f"{first_point} {line_segments}"
    area_path = f"{line_path} L {x_pos(dates[-1])} {height - padding} L {x_pos(dates[0])} {height - padding} Z"

    ticks = []
    for d in dates:
        x = x_pos(d)
        ticks.append(
            f"<line x1='{x}' y1='{height - padding}' x2='{x}' y2='{height - padding + 6}' "
            f"stroke='#b3b3b3' stroke-width='1'/>")
        ticks.append(
            f"<text x='{x}' y='{height - padding + 18}' font-size='10' text-anchor='middle' "
            f"fill='#444'>{d.strftime('%m-%d')}</text>"
        )

    for i in range(0, 6):
        val = min_cost + (i / 5) * (max_cost - min_cost)
        y = y_pos(val)
        ticks.append(f"<line x1='{padding - 6}' y1='{y}' x2='{padding}' y2='{y}' stroke='#b3b3b3' stroke-width='1'/>")
        ticks.append(f"<text x='{padding - 10}' y='{y + 3}' font-size='10' text-anchor='end' fill='#444'>{val:.1f}</text>")
        ticks.append(f"<line x1='{padding}' y1='{y}' x2='{width - padding}' y2='{y}' stroke='#eaecef' stroke-width='1'/>")

    return f"""
    <svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet"
         role="img" aria-label="Daily Cost Trend" style="width:100%;height:auto;display:block;">
        <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" rx="6" ry="6" />
        <defs>
            <linearGradient id="gradCostArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="{stroke}" stop-opacity="0.55"/>
                <stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <path d="{area_path}" fill="url(#gradCostArea)" stroke="none" opacity="0.85"></path>
        <path d="{line_path}" fill="none" stroke="{stroke}" stroke-width="2.2"
              stroke-linejoin="round" stroke-linecap="round"></path>
        {''.join(ticks)}
    </svg>
    """


# ---- Public Rendering Function ---- #

def render_cost_section(subscription_id: str,
                        timeframe: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Build cost metrics HTML snippet.
    Returns: (html_string, records_list)
    """
    if not _COST_AVAILABLE:
        return ("""
        <div class="ms-card" style="margin-top:1.5rem;">
            <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics</h3>
            <div style="color:#a00;font-size:0.85rem;">cost_rest module not available.</div>
        </div>
        """, [])

    try:
        result = fetch_daily_costs(subscription_id, timeframe=timeframe)
    except Exception as e:  # pragma: no cover
        return (f"""
        <div class="ms-card" style="margin-top:1.5rem;">
            <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics</h3>
            <div style="color:#a00;font-size:0.85rem;">Failed to fetch cost data: {e}</div>
        </div>
        """, [])

    records = result.get("records", [])
    if not records:
        return ("""
        <div class="ms-card" style="margin-top:1.5rem;">
            <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics</h3>
            <div style="font-size:0.85rem;">No cost data returned for selected timeframe.</div>
        </div>
        """, [])

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
        {_metric_block("Latest ({latest_date})".format(latest_date=latest['date'].strftime('%m-%d')),
                       f"{latest['cost']:.2f} {currency}")}
        {_metric_block("Day Change", delta_str)}
        {_metric_block("Data Points", len(records))}
    </div>
    """

    line_svg = _cost_line_area_svg(records)

    last_slice = records[-7:] if len(records) > 7 else records
    # Build striped rows manually (alternate background)
    table_rows_parts: List[str] = []
    for idx, r in enumerate(last_slice):
        shade = "#f7f8fa" if idx % 2 == 1 else "#ffffff"
        table_rows_parts.append(
            f"<tr style='background:{shade};'>"
            f"<td style='padding:4px 8px;font-weight:600;color:#002855;border-bottom:1px solid #eaecef;'>{r['date']}</td>"
            f"<td style='padding:4px 8px;text-align:right;border-bottom:1px solid #eaecef;'>{r['cost']:.2f}</td>"
            f"</tr>"
        )
    table_rows = "".join(table_rows_parts)

    table_html = f"""
    <table class="recent-days-table" style="width:100%;border-collapse:collapse;font-size:0.70rem;">
        <thead>
            <tr style="background:#e9f2fb;">
                <th style="text-align:left;padding:6px 8px;color:#0051a8;border-bottom:1px solid #d3dbe5;">Date</th>
                <th style="text-align:right;padding:6px 8px;color:#0051a8;border-bottom:1px solid #d3dbe5;">PreTaxCost ({currency})</th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
    """

    # Flex layout: 75% (trend) / 25% (recent days)
    # Using flex-basis to hint size and min-width:0 to allow proper shrinking.
    html = f"""
    <div class="ms-card" style="margin-top:1.3rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Cost Metrics (Azure Cost Management)</h3>
        {summary_html}
        <div style="display:flex;flex-wrap:wrap;gap:1.25rem;margin-top:1rem;align-items:stretch;">
            <div style="flex:3 1 0%;min-width:320px;min-height:100%;display:flex;flex-direction:column;">
                <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin:0 0 6px 0;">Daily Cost Trend</div>
                <div style="flex:1 1 auto;overflow:auto;">{line_svg}</div>
            </div>
            <div style="flex:1 1 0%;min-width:220px;display:flex;flex-direction:column;">
                <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin:0 0 6px 0;">Recent Days</div>
                <div class="ms-card" style="flex:1 1 auto;padding:0.7rem 0.7rem 0.4rem 0.7rem;margin:0;border:1px solid #eaecef;overflow:auto;">
                    {table_html}
                </div>
            </div>
        </div>
        <div style="text-align:right;font-size:0.6rem;color:#555;margin-top:0.75rem;">
            Generated {datetime.datetime.utcnow().isoformat()}Z — Currency: {currency}
        </div>
        <style>
            @media (max-width: 1100px) {{
                /* Stack panels on narrower viewports */
                .ms-card > div[style*="display:flex"][style*="flex-wrap:wrap"] > div {{
                    flex:1 1 100% !important;
                }}
            }}
        </style>
    </div>
    """

    return html, records