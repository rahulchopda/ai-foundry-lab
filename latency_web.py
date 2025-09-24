"""
latency_web_2.py

Encapsulates latency (or other metric) rendering logic, matching cost_web.py.

Exports:
    render_latency_section() -> (str, pd.DataFrame)
        Returns: (html_snippet, dataframe)
"""

import datetime

# Import your get_metrics function here (edit the import to your project structure)
from monitoring_app import get_metrics
import pandas as pd

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

def _latency_line_area_svg(df, width=1200, height=260, stroke="#0051a8") -> str:
    """Inline SVG area+line for 'total' values in df with datetime index."""
    if df.empty or df['total'].isnull().all():
        return "<div>No latency data</div>"

    padding = 40
    xvals = df.index.to_list()
    yvals = df['total'].fillna(0).to_list()
    min_y = 0
    max_y = max(yvals) or 1
    n = len(xvals)
    if n < 2:
        return "<div>Not enough data for chart</div>"

    t0 = xvals[0]
    t1 = xvals[-1]
    span_secs = (t1-t0).total_seconds() or 1

    def x_pos(t):
        return padding + ((t-t0).total_seconds()/span_secs)*(width-2*padding)
    def y_pos(y):
        return height - padding - ((y-min_y)/(max_y-min_y))*(height-2*padding)

    first = f"M {x_pos(xvals[0])} {y_pos(yvals[0])}"
    segments = " ".join(f"L {x_pos(t)} {y_pos(y)}" for t, y in zip(xvals, yvals))
    line_path = f"{first} {segments}"
    area_path = f"{line_path} L {x_pos(xvals[-1])} {height-padding} L {x_pos(xvals[0])} {height-padding} Z"

    # X ticks (timestamps, max ~10 for readability)
    ticks = []
    for i, t in enumerate(xvals):
        if i % max(1, n//10) == 0:
            x = x_pos(t)
            ticks.append(f"<line x1='{x}' y1='{height-padding}' x2='{x}' y2='{height-padding+6}' stroke='#b3b3b3' stroke-width='1'/>")
            ticks.append(f"<text x='{x}' y='{height-padding+18}' font-size='10' text-anchor='middle' fill='#444'>{t.strftime('%H:%M')}</text>")
    # Y ticks
    for i in range(0, 6):
        val = min_y + (i/5)*(max_y-min_y)
        y = y_pos(val)
        ticks.append(f"<line x1='{padding-6}' y1='{y}' x2='{padding}' y2='{y}' stroke='#b3b3b3' stroke-width='1'/>")
        ticks.append(f"<text x='{padding-10}' y='{y+3}' font-size='10' text-anchor='end' fill='#444'>{val:.1f}</text>")
        ticks.append(f"<line x1='{padding}' y1='{y}' x2='{width-padding}' y2='{y}' stroke='#eaecef' stroke-width='1'/>")

    return f"""
    <svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet"
         role="img" aria-label="Latency Trend" style="width:100%;height:auto;display:block;">
        <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" rx="6" ry="6" />
        <defs>
            <linearGradient id="gradLatencyArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="{stroke}" stop-opacity="0.55"/>
                <stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <path d="{area_path}" fill="url(#gradLatencyArea)" stroke="none" opacity="0.85"></path>
        <path d="{line_path}" fill="none" stroke="{stroke}" stroke-width="2.2"
              stroke-linejoin="round" stroke-linecap="round"></path>
        {''.join(ticks)}
    </svg>
    """

def render_latency_section(metric_name: str = "Latency", unit: str = "ms"):
    # Call your get_metrics function
    metrics_data = get_metrics()
    df = pd.DataFrame(metrics_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    # Metrics summary
    total = df['total'].sum()
    avg = df['total'].mean()
    latest = df['total'].iloc[-1] if not df.empty else 0
    n_points = df['total'].count()
    latest_time = df.index[-1].strftime('%Y-%m-%d %H:%M') if not df.empty else ''
    if n_points > 1:
        prev = df['total'].iloc[-2]
        delta_pct = ((latest-prev)/prev)*100 if prev > 0 else 0
        delta_str = f"{delta_pct:+.2f}% vs prev" if prev > 0 else "n/a"
    else:
        delta_str = "n/a"

    summary_html = f"""
    <div style="display:flex;flex-wrap:wrap;margin:-0.4rem;">
        {_metric_block("Metric", metric_name, highlight=True)}
        {_metric_block("Total", f"{total:.2f} {unit}")}
        {_metric_block("Avg", f"{avg:.2f} {unit}")}
        

    </div>
    """

    line_svg = _latency_line_area_svg(df)

    # Recent rows (last 10)
    last_slice = df.tail(10)
    table_rows = []
    for idx, (t, row) in enumerate(last_slice.iterrows()):
        shade = "#f7f8fa" if idx%2==1 else "#fff"
        table_rows.append(
            f"<tr style='background:{shade};'>"
            f"<td style='padding:4px 8px;font-weight:600;color:#002855;border-bottom:1px solid #eaecef;'>{t.strftime('%Y-%m-%d %H:%M')}</td>"
            f"<td style='padding:4px 8px;text-align:right;border-bottom:1px solid #eaecef;'>{row['total']:.2f}</td>"
            f"</tr>"
        )


    html = f"""
    <div class="ms-card" style="margin-top:1.3rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">{metric_name} Metrics (Azure Monitor)</h3>
        {summary_html}
        <div style="display:flex;flex-wrap:wrap;gap:1.25rem;margin-top:1rem;align-items:stretch;">
            <div style="flex:3 1 0%;min-width:320px;min-height:100%;display:flex;flex-direction:column;">
                <div style="font-size:0.75rem;font-weight:600;color:#0051a8;margin:0 0 6px 0;">Trend</div>
                <div style="flex:1 1 auto;overflow:auto;">{line_svg}</div>
            </div>
            
        </div>
        <div style="text-align:right;font-size:0.6rem;color:#555;margin-top:0.75rem;">
            Generated {datetime.datetime.utcnow().isoformat()}Z
        </div>
        <style>
            @media (max-width: 1100px) {{
                .ms-card > div[style*="display:flex"][style*="flex-wrap:wrap"] > div {{
                    flex:1 1 100% !important;
                }}
            }}
        </style>
    </div>
    """
    return html, df
