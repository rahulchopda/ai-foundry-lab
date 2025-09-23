import datetime
import random
import json
from typing import Dict, Optional
from shared_css import inline_full_css  # Import shared CSS (for optional embedding)

def _metric_block(label: str, value, highlight=False):
    border = "border:2px solid #0051a8;" if highlight else "border:1.5px solid #eaecef;"
    return f"""
    <div style="flex:1;min-width:180px;margin:0.5rem;">
        <div class="ms-card" style="padding:1.2rem 1rem;{border}">
            <div style="font-size:0.85rem;text-transform:uppercase;letter-spacing:1px;color:#0051a8;font-weight:600;margin-bottom:0.35rem;">
                {label}
            </div>
            <div style="font-size:1.4rem;font-weight:600;color:#002855;">{value}</div>
        </div>
    </div>
    """

def _simple_table(title: str, rows: Dict[str, str]):
    trs = "".join(
        f"<tr><td style='padding:6px 10px;font-weight:600;color:#002855'>{k}</td>"
        f"<td style='padding:6px 10px;color:#1a1a1a'>{v}</td></tr>"
        for k, v in rows.items()
    )
    return f"""
    <div class="ms-card" style="margin-bottom:1.5rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">{title}</h3>
        <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
            <tbody>{trs}</tbody>
        </table>
    </div>
    """

def _generate_fake_timeseries(name: str, points: int = 24):
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

def generate_monitoring_html(
        governance_metrics: Dict,
        model_costs: Dict,
        selected_models=None,
        include_css: bool = True
) -> str:
    """
    Returns consolidated monitoring dashboard HTML.
    include_css=True embeds the shared CSS (useful if rendered standalone).
    """
    req_series = _generate_fake_timeseries("Request Count", 30)
    latency_series = _generate_fake_timeseries("Latency (ms)", 30)
    token_series = _generate_fake_timeseries("Tokens Used", 30)

    def sparkline(series_struct):
        series = series_struct["series"]
        values = [p["v"] for p in series]
        if not values:
            return "<div>No data</div>"
        max_v = max(values) or 1
        bars = "".join(
            f"<div title='{v}' style='flex:1;height:40px;display:flex;align-items:flex-end;'>"
            f"<div style='width:100%;background:linear-gradient(180deg,#0051a8,#002855);height:{(v/max_v)*100:.2f}%;border-radius:2px;'></div>"
            "</div>"
            for v in values
        )
        return f"""
        <div style="display:flex;gap:2px;align-items:flex-end;height:40px;">{bars}</div>
        <div style="font-size:0.7rem;color:#555;margin-top:4px;">Last {len(values)} pts</div>
        """

    top_metrics_html = """
    <div style="display:flex;flex-wrap:wrap;margin:-0.5rem;">
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

    governance_html = _simple_table("Governance & Compliance", {k: v for k, v in governance_metrics.items()})
    cost_rows = {model: f"${cost}/1M tokens" for model, cost in model_costs.items()}
    cost_html = _simple_table("Configured Model Costs", cost_rows or {"No Models": "N/A"})

    timeseries_html = f"""
    <div class="ms-card" style="margin-bottom:1.5rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Operational Trends</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;">
            <div>
                <div style="font-size:0.8rem;font-weight:600;color:#0051a8;margin-bottom:4px;">Request Volume</div>
                {sparkline(req_series)}
            </div>
            <div>
                <div style="font-size:0.8rem;font-weight:600;color:#0051a8;margin-bottom:4px;">Latency (ms)</div>
                {sparkline(latency_series)}
            </div>
            <div>
                <div style="font-size:0.8rem;font-weight:600;color:#0051a8;margin-bottom:4px;">Tokens Used</div>
                {sparkline(token_series)}
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
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.15rem;">Raw Monitoring Data (Sample)</h3>
        <pre style="font-size:0.7rem;max-height:300px;overflow:auto;background:#f7f8fa;padding:1rem;border:1px solid #eaecef;border-radius:8px;">{json.dumps(raw_json, indent=2)}</pre>
    </div>
    """

    css_block = inline_full_css() if include_css else ""
    full_html = f"""
    {css_block}
    <div style="margin-top:0.5rem;">
        {top_metrics_html}
        {timeseries_html}
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1.5rem;">
            <div>{governance_html}</div>
            <div>{cost_html}</div>
        </div>
        {raw_html}
        <div style="text-align:center;font-size:0.7rem;color:#555;margin-top:1.5rem;">
            Generated at {datetime.datetime.utcnow().isoformat()}Z
        </div>
    </div>
    """
    return full_html