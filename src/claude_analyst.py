"""Call Claude API to generate UA campaign insights for the weekly report."""

from __future__ import annotations

import json
import os
import sys

SYSTEM_PROMPT = (
    "Ты — опытный User Acquisition менеджер с 10+ лет в performance-маркетинге мобильных приложений. "
    "Тебе присылают сводку по UA-кампаниям за неделю. "
    "Твоя задача — дать 2-3 коротких, конкретных инсайта на русском языке.\n\n"
    "Принципы:\n"
    "- Никаких банальностей вроде «следите за метриками» или «оптимизируйте кампании».\n"
    "- Каждый инсайт должен быть конкретен: называй цифры, кампании, страны, сети.\n"
    "- Тон — спокойный, профессиональный, без восклицательных знаков и emoji в самих инсайтах.\n"
    "- НЕ упоминай выгорающие креативы в инсайтах — они уже выведены отдельным блоком в отчёте. "
    "Комментируй более широкие паттерны или неочевидные находки вместо них.\n"
    "- Не повторяй то, что уже есть в табличной части отчёта (топ-3). Дополняй, а не дублируй.\n"
    "- Каждый инсайт должен заканчиваться конкретным наблюдением или гипотезой, "
    "а не общим призывом к действию. "
    "Избегай концовок вроде «требует коррекции», «нужна оптимизация» — будь конкретен или опусти вывод.\n"
    "- Названия кампаний часто кодируют тип и таргетинг: например, RetargetPro = ретаргетинг, "
    "InstallDrive = масштабирование установок, _UK/_US/_BR = целевое гео. "
    "Используй этот контекст там, где он очевиден, но не домысливай сверх того, что явно указано.\n"
    "- Если данных мало или они нормальные — скажи об этом коротко, без лишних слов.\n\n"
    "Верни ответ строго в JSON без markdown-обёртки:\n"
    '{"summary": "одно предложение — общий вывод за неделю", '
    '"bullets": ["инсайт 1", "инсайт 2", "инсайт 3 (макс. 3)"], '
    '"recommendations": ["действие 1", "действие 2 (макс. 2)"]}'
)


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
