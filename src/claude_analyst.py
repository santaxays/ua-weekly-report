"""Call Claude API to generate UA campaign insights for the weekly report."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_system_prompt() -> str:
    """Load the system prompt from prompts/, preferring the private .ru.md file."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    ru_path = prompts_dir / "system_prompt.ru.md"
    example_path = prompts_dir / "system_prompt.example.md"

    if ru_path.exists():
        return ru_path.read_text(encoding="utf-8")

    print(
        "WARN: using example system prompt; create prompts/system_prompt.ru.md for the real one",
        file=sys.stderr,
    )
    return example_path.read_text(encoding="utf-8")


SYSTEM_PROMPT = load_system_prompt()


def _build_user_message(
    week_data: dict,
    prev_week_data: dict,
    burning: list,
    top_roas: list,
    week_label: str = "",
) -> str:
    totals = week_data.get("totals", {})
    deltas = week_data.get("deltas", {})

    def pct(val: float) -> str:
        sign = "↑" if val >= 0 else "↓"
        return f"{sign}{abs(val):.1%}"

    lines = [f"Данные за неделю {week_label}:\n"]
    lines.append(f"Затраты: ${totals.get('cost', 0):,.0f} ({pct(deltas.get('cost', 0))})")
    lines.append(f"Установки: {int(totals.get('installs', 0)):,} ({pct(deltas.get('installs', 0))})")
    lines.append(f"CPI: ${totals.get('CPI', 0):.2f} ({pct(deltas.get('CPI', 0))})")
    lines.append(f"ROAS D7: {totals.get('ROAS_d7', 0):.1%} ({pct(deltas.get('ROAS_d7', 0))})")
    lines.append(f"CTR: {totals.get('CTR', 0):.2%} ({pct(deltas.get('CTR', 0))})")

    if top_roas:
        lines.append("\nТоп-3 по ROAS D7:")
        for i, row in enumerate(top_roas, start=1):
            lines.append(
                f"{i}. {row.get('campaign', '?')} — "
                f"ROAS D7: {row.get('ROAS_d7', 0):.1%}, "
                f"CPI ${row.get('CPI', 0):.2f}"
            )

    if burning:
        lines.append("\nВыгорающие креативы:")
        for b in burning:
            lines.append(
                f"- {b.get('campaign', '?')}: "
                f"CTR ↓{abs(b.get('CTR_change', 0)):.1%}, "
                f"CPI ↑{b.get('CPI_change', 0):.1%}"
            )

    lines.append("\nДай 2-3 инсайта и 1-2 рекомендации.")
    return "\n".join(lines)


def get_insights(
    week_data: dict,
    prev_week_data: dict,
    burning: list,
    top_roas: list,
    week_label: str = "",
) -> dict | None:
    """Ask Claude for UA insights and return a structured dict, or None on any failure."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not set — skipping Claude insights.", file=sys.stderr)
        return None

    try:
        import anthropic
    except ImportError:
        print("Warning: anthropic package not installed — skipping Claude insights.", file=sys.stderr)
        return None

    user_message = _build_user_message(week_data, prev_week_data, burning, top_roas, week_label)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        if not isinstance(parsed.get("summary"), str):
            raise ValueError("Missing 'summary' key")
        if not isinstance(parsed.get("bullets"), list):
            raise ValueError("Missing 'bullets' key")
        if "recommendations" not in parsed:
            parsed["recommendations"] = []

        return parsed

    except Exception as e:
        print(f"Warning: Claude insights failed ({type(e).__name__}: {e}) — continuing without insights.", file=sys.stderr)
        return None
