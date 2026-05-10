"""Build a Slack Block Kit weekly report from computed metrics."""

from __future__ import annotations

import pandas as pd


def _delta(change: float, invert: bool = False) -> str:
    """Format a fractional change as a coloured arrow string.

    Args:
        change: Fractional delta (0.12 = +12%, -0.05 = -5%).
        invert: Set True for metrics where higher is bad (e.g. CPI).
    """
    if abs(change) < 0.001:
        return "— 0%"

    is_good = (change > 0) if not invert else (change < 0)
    emoji   = "🟢" if is_good else "🔴"
    arrow   = "↑" if change > 0 else "↓"
    return f"{emoji} {arrow} {abs(change):.1%}"


def build_weekly_report(
    metrics: dict,
    top_campaigns: pd.DataFrame,
    burning: list[dict],
    week_label: str,
    insights: dict | None = None,
) -> tuple[list[dict], str]:
    """Assemble Slack Block Kit blocks and a fallback text string.

    Args:
        metrics:       Output of compare_weeks() — keys "totals" and "deltas".
        top_campaigns: Output of top_n_by() — DataFrame with campaign rows.
        burning:       Output of detect_burning_creatives() — list of dicts.
        week_label:    Human-readable week label shown in the header (Russian).

    Returns:
        (blocks, fallback_text) ready to pass to SlackClient.send_blocks().
    """
    totals = metrics["totals"]
    deltas = metrics["deltas"]
    blocks: list[dict] = []

    # ── Header ──────────────────────────────────────────────────────────────
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"📊 UA Отчёт — {week_label}"},
    })

    # ── Top-line summary ─────────────────────────────────────────────────────
    summary = "\n".join([
        f"*Затраты:* ${totals['cost']:,.2f}  {_delta(deltas['cost'])}",
        f"*Установки:* {int(totals['installs']):,}  {_delta(deltas['installs'])}",
        f"*CPI:* ${totals['CPI']:.2f}  {_delta(deltas['CPI'], invert=True)}",
        f"*ROAS D7:* {totals['ROAS_d7']:.1%}  {_delta(deltas['ROAS_d7'])}",
        f"*CTR:* {totals['CTR']:.2%}  {_delta(deltas['CTR'])}",
    ])
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": summary},
    })

    # ── Claude insights ──────────────────────────────────────────────────────
    if isinstance(insights, dict):
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "💡 *Инсайты недели*"},
        })
        summary = insights.get("summary", "")
        bullets = insights.get("bullets", [])
        recommendations = insights.get("recommendations", [])

        insight_lines = []
        if summary:
            insight_lines.append(f"_{summary}_")
        for b in bullets:
            insight_lines.append(f"• {b}")
        if recommendations:
            insight_lines.append("*Действия:*")
            for r in recommendations:
                insight_lines.append(f"• {r}")

        if insight_lines:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(insight_lines)},
            })

    blocks.append({"type": "divider"})

    # ── Top-3 campaigns by ROAS D7 ───────────────────────────────────────────
    fields = []
    for i, (_, row) in enumerate(top_campaigns.iterrows(), start=1):
        fields.append({
            "type": "mrkdwn",
            "text": (
                f"*{i}. {row['campaign']}*\n"
                f"ROAS D7: {row['ROAS_d7']:.1%} | CPI: ${row['CPI']:.2f} | "
                f"Установки: {int(row['installs']):,}"
            ),
        })
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*🏆 Топ-3 кампании по ROAS D7:*"},
        "fields": fields,
    })

    blocks.append({"type": "divider"})

    # ── Burning creatives ────────────────────────────────────────────────────
    if burning:
        lines = ["*🔥 Выгорающие креативы:*"]
        for b in burning:
            lines.append(
                f"• *{b['campaign']}* — "
                f"CTR ↓ {abs(b['CTR_change']):.1%}  |  "
                f"CPI ↑ {b['CPI_change']:.1%}  "
                f"(${b['CPI_prev']:.2f} → ${b['CPI_curr']:.2f})"
            )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Выгорающих креативов нет 🎉"},
        })

    # ── Footer context ───────────────────────────────────────────────────────
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"Сформировано автоматически · {week_label} · UA Weekly Report Bot",
        }],
    })

    fallback_text = (
        f"UA Отчёт {week_label} — "
        f"Затраты: ${totals['cost']:,.2f}, "
        f"Установки: {int(totals['installs']):,}, "
        f"ROAS D7: {totals['ROAS_d7']:.1%}"
    )

    return blocks, fallback_text
