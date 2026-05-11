"""
Daily Report: Fetch Adjust + MAX data at daily granularity,
push to Google Sheets tab "Daily Report".

First run: pulls all days from 2026-04-06 to today.
Subsequent runs: updates yesterday + adds today.
"""
import pandas as pd
from datetime import datetime, timedelta

from api_fetchers import (
    fetch_adjust, fetch_max_impressions,
    aggregate_max_impressions_daily, build_report_table,
)
from sheets_helper import get_worksheet, update_or_append_columns_incremental

# =========================
# CONFIG
# =========================
SHEET_TAB = "Daily Report"
FIRST_RUN_START = "2026-04-06"


def get_date_range():
    """
    Determine date range.
    Always fetches from FIRST_RUN_START to today.
    The sheet logic handles deduplication.
    """
    today = datetime.today()
    date_from = FIRST_RUN_START
    date_to = today.strftime("%Y-%m-%d")
    return date_from, date_to


def main():
    date_from, date_to = get_date_range()
    print(f"Daily Report: {date_from} → {date_to}")

    # 1. Fetch data
    print("  Fetching Adjust data (daily)...")
    adj = fetch_adjust(date_from, date_to, dimension="day")

    print("  Fetching MAX impressions...")
    max_raw = fetch_max_impressions(date_from, date_to)
    max_imp = aggregate_max_impressions_daily(max_raw)

    # 2. Build report table
    report = build_report_table(adj, max_imp, is_weekly=False)

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
