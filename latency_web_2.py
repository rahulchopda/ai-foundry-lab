"""
latency_web_2.py

Provides a replacement visualization for latency:
A stacked bar chart per model showing latency distribution buckets
(Fast / Typical / Slow) plus percentile markers, rendered as inline SVG.

Exports:
    render_latency_section(model_names: List[str]) -> str
"""

from __future__ import annotations
import random
from typing import List, Dict


def _generate_latency_distribution(model: str) -> Dict:
    """
    Create synthetic latency distribution for a model:
    - fast:   0-250ms
    - normal: 250-1000ms
    - slow:   1000-2500ms
    Returns dictionary with counts and approximate percentiles.
    """
    fast = random.randint(50, 300)
    normal = random.randint(200, 800)
    slow = random.randint(20, 200)
    total = fast + normal + slow
    # Synthetic percentiles (weighted rough values)
    p50 = random.uniform(220, 600)
    p90 = random.uniform(700, 1400)
    p99 = random.uniform(1500, 2400)
    return {
        "model": model,
        "fast": fast,
        "normal": normal,
        "slow": slow,
        "total": total,
        "p50": round(p50, 1),
        "p90": round(p90, 1),
        "p99": round(p99, 1)
    }


def _stacked_bar_svg(data: List[Dict], width: int = 820, bar_height: int = 32,
                     gap: int = 18) -> str:
    """
    Render stacked horizontal bars for each model with segments representing
    fast / normal / slow counts and vertical percentile markers.
    """
    if not data:
        return "<div>No latency data</div>"

    max_total = max(d["total"] for d in data) or 1
    height = (bar_height + gap) * len(data) + 40

    # Colors
    colors = {
        "fast": "#1b7b34",
        "normal": "#f5a300",
        "slow": "#c62828"
    }

    svg_parts = [
        f"<svg width='{width}' height='{height}' role='img' aria-label='Latency Distribution by Model'>",
        "<rect x='0' y='0' width='100%' height='100%' fill='#ffffff' rx='8' ry='8'/>",
        "<style>"
        ".lbl{font:11px Helvetica,Arial,sans-serif;fill:#002855}"
        ".pct{font:9px Helvetica,Arial,sans-serif;fill:#444}"
        "</style>"
    ]

    left_margin = 140
    usable_width = width - left_margin - 40

    y_offset = 30
    svg_parts.append(
        "<text x='12' y='18' class='lbl' font-size='13' font-weight='600'>Latency Distribution (synthetic)</text>"
    )
    svg_parts.append(
        "<text x='12' y='32' class='pct' font-size='10'>Stacked counts (fast / typical / slow) with p50 | p90 | p99 markers</text>"
    )

    for idx, row in enumerate(data):
        y = y_offset + idx * (bar_height + gap)

        # Label
        svg_parts.append(
            f"<text x='12' y='{y + bar_height * 0.65}' class='lbl' font-size='11' font-weight='600'>{row['model']}</text>"
        )

        x_cursor = left_margin
        for seg_name in ["fast", "normal", "slow"]:
            seg_value = row[seg_name]
            seg_width = (seg_value / max_total) * usable_width
            svg_parts.append(
                f"<rect x='{x_cursor}' y='{y}' width='{seg_width}' height='{bar_height}' "
                f"fill='{colors[seg_name]}' rx='4' ry='4'>"
                f"<title>{row['model']} - {seg_name}: {seg_value} ({seg_value/row['total']*100:.1f}%)</title>"
                f"</rect>"
            )
            x_cursor += seg_width

        # Percentile markers
        # Map percentile ms values onto bar using assumed max range aligned with p99 for that model (capped).
        max_latency_for_scale = max(row["p99"], 2000)
        def x_for_latency(ms: float) -> float:
            ratio = min(ms / max_latency_for_scale, 1.0)
            return left_margin + ratio * usable_width

        for mark, color in [("p50", "#004b8d"), ("p90", "#6a1b9a"), ("p99", "#b00020")]:
            x_m = x_for_latency(row[mark])
            svg_parts.append(
                f"<line x1='{x_m}' y1='{y - 2}' x2='{x_m}' y2='{y + bar_height + 2}' "
                f"stroke='{color}' stroke-width='2' opacity='0.9'/>"
            )
            svg_parts.append(
                f"<text x='{x_m + 4}' y='{y + bar_height/2 + 4}' class='pct'>{mark.upper()} {row[mark]}ms</text>"
            )

        # Total label
        svg_parts.append(
            f"<text x='{left_margin + usable_width + 6}' y='{y + bar_height*0.65}' class='pct' "
            f"font-size='10'>{row['total']} req</text>"
        )

    # Legend
    legend_y = height - 12
    legend_items = [
        ("Fast (<250ms)", colors["fast"]),
        ("Typical (250-1000ms)", colors["normal"]),
        ("Slow (>1000ms)", colors["slow"]),
        ("p50", "#004b8d"),
        ("p90", "#6a1b9a"),
        ("p99", "#b00020"),
    ]
    legend_x = 12
    for label, color in legend_items:
        svg_parts.append(
            f"<rect x='{legend_x}' y='{legend_y - 10}' width='14' height='14' fill='{color}' rx='3' ry='3'/>"
        )
        svg_parts.append(
            f"<text x='{legend_x + 20}' y='{legend_y + 2}' class='pct' font-size='10'>{label}</text>"
        )
        legend_x += 120

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def render_latency_section(model_names: List[str]) -> str:
    """
    Generate the latency section HTML for given models.
    If model_names empty, generates a default sample set.
    """
    if not model_names:
        model_names = ["model-A", "model-B", "model-C"]

    data = [_generate_latency_distribution(m) for m in model_names]

    svg = _stacked_bar_svg(data)
    table_rows = "".join(
        f"<tr>"
        f"<td style='padding:4px 6px;font-weight:600;color:#002855'>{d['model']}</td>"
        f"<td style='padding:4px 6px;text-align:right;'>{d['p50']} ms</td>"
        f"<td style='padding:4px 6px;text-align:right;'>{d['p90']} ms</td>"
        f"<td style='padding:4px 6px;text-align:right;'>{d['p99']} ms</td>"
        f"<td style='padding:4px 6px;text-align:right;'>{d['fast']}/{d['normal']}/{d['slow']}</td>"
        f"<td style='padding:4px 6px;text-align:right;'>{d['total']}</td>"
        f"</tr>"
        for d in data
    )
    table_html = f"""
    <table style="width:100%;border-collapse:collapse;font-size:0.70rem;margin-top:0.75rem;">
        <thead>
            <tr>
                <th style="text-align:left;padding:6px 6px;color:#0051a8;">Model</th>
                <th style="text-align:right;padding:6px 6px;color:#0051a8;">p50</th>
                <th style="text-align:right;padding:6px 6px;color:#0051a8;">p90</th>
                <th style="text-align:right;padding:6px 6px;color:#0051a8;">p99</th>
                <th style="text-align:right;padding:6px 6px;color:#0051a8;">Fast/Typ/Slow</th>
                <th style="text-align:right;padding:6px 6px;color:#0051a8;">Total Req</th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
    """

    return f"""
    <div class="ms-card" style="margin-top:1.3rem;">
        <h3 class="ms-section-title" style="margin-top:0;font-size:1.05rem;">Latency Distribution</h3>
        <div style="overflow:auto;padding:0.3rem 0 0.6rem 0;">{svg}</div>
        <div class="ms-card" style="padding:0.6rem 0.7rem 0.4rem 0.7rem;margin:0;border:1px solid #eaecef;">
            {table_html}
        </div>
        <div style="text-align:right;font-size:0.55rem;color:#555;margin-top:0.6rem;">
            Synthetic data for visualization only.
        </div>
    </div>
    """