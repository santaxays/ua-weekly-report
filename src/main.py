"""Entry point: load campaign data, build Slack report, send it."""

import os
import sys

from dotenv import load_dotenv

from slack_client import SlackClient
from metrics import (
    load_campaigns,
    aggregate_by,
    compare_weeks,
    detect_burning_creatives,
    top_n_by,
)
from report_builder import build_weekly_report
from claude_analyst import get_insights

CURRENT_WEEK  = "2026-04-28"   # start date of the week being reported
PREVIOUS_WEEK = "2026-04-21"   # start date of the comparison week
WEEK_LABEL    = "28 апр – 4 мая 2026"
DATA_PATH     = "data/sample_campaigns.csv"


def main():
    load_dotenv()

    token      = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("SLACK_CHANNEL_ID")

    if not token:
        print("Error: SLACK_BOT_TOKEN is missing.")
        print("Copy .env.example to .env and fill in your Slack Bot token.")
        sys.exit(1)

    if not channel_id:
        print("Error: SLACK_CHANNEL_ID is missing.")
        print("Copy .env.example to .env and fill in your Slack channel ID.")
        sys.exit(1)

    try:
        df = load_campaigns(DATA_PATH)

        metrics = compare_weeks(df, current_week=CURRENT_WEEK, previous_week=PREVIOUS_WEEK)

        top_campaigns = top_n_by(
            aggregate_by(df, group_by=["campaign"], week=CURRENT_WEEK),
            metric="ROAS_d7",
            n=3,
        )

        burning = detect_burning_creatives(df)

        top_roas_list = top_campaigns.to_dict(orient="records")
        insights = get_insights(
            week_data=metrics,
            prev_week_data={},
            burning=burning,
            top_roas=top_roas_list,
            week_label=WEEK_LABEL,
        )

        blocks, fallback = build_weekly_report(metrics, top_campaigns, burning, WEEK_LABEL, insights)

    except Exception as e:
        print(f"Error building report: {e}")
        sys.exit(1)

    try:
        client = SlackClient(token=token)
        client.send_blocks(channel_id=channel_id, blocks=blocks, fallback_text=fallback)
    except RuntimeError as e:
        print(f"Error sending to Slack: {e}")
        sys.exit(1)

    print("Sent OK")


if __name__ == "__main__":
    main()
