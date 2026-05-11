"""
Weekly Report: Fetch Adjust + MAX data, push to Google Sheets tab "weekly report".

First run: pulls all weeks from 2026-04-07 (Monday) to today.
Subsequent runs: only updates the current week column (or adds a new one).
"""
import pandas as pd
from datetime import datetime, timedelta

from api_fetchers import (
    fetch_adjust, fetch_max_impressions,
    aggregate_max_impressions_weekly, build_report_table,
)
from sheets_helper import get_worksheet, update_or_append_columns_incremental

# =========================
# CONFIG
# =========================
SHEET_TAB = "Weekly Report"
FIRST_RUN_START = "2026-04-07"  # Monday, first week to include


def get_date_range():
    """
    Determine date range.
    Always starts from FIRST_RUN_START to capture all historical weeks.
    The sheet logic handles deduplication (existing columns are overwritten).
    """
    today = datetime.today()
    date_from = FIRST_RUN_START
    date_to = today.strftime("%Y-%m-%d")
    return date_from, date_to


def main():
    date_from, date_to = get_date_range()
    print(f"Weekly Report: {date_from} → {date_to}")

    # 1. Fetch data
    print("  Fetching Adjust data (weekly)...")
    adj = fetch_adjust(date_from, date_to, dimension="week")

    print("  Fetching MAX impressions...")
    max_raw = fetch_max_impressions(date_from, date_to)
    max_imp = aggregate_max_impressions_weekly(max_raw)

    # 2. Build report table
    report = build_report_table(adj, max_imp, is_weekly=True)

    if report.empty:
        print("  ⚠️  No data to report.")
        return

    # Print to console
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    print("\n" + report.to_string())

    # 3. Push to Google Sheets
    print(f"\n  Pushing to Google Sheets tab '{SHEET_TAB}'...")
    ws = get_worksheet(SHEET_TAB)
    update_or_append_columns_incremental(ws, report)

    print("  Done!")


if __name__ == "__main__":
    main()
