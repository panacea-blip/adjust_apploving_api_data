"""
Google Sheets helper for reading/writing report data.
Authenticates via GOOGLE_CREDENTIALS env var (JSON string) or local credentials.json file.
"""
import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1RxUSB-W2gLSCLxUCSmN6l-Pgegb1kO9mcP8egHzT834"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    """Authenticate and return a gspread client."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")

    if creds_json:
        # From environment variable (GitHub Actions)
        creds_info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        # From local file
        creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                "No Google credentials found. Either set GOOGLE_CREDENTIALS env var "
                "or place a credentials.json file in the project directory."
            )
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    return gspread.authorize(creds)


def get_worksheet(tab_name):
    """Get or create a worksheet tab in the spreadsheet."""
    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows=100, cols=50)

    return worksheet


def update_or_append_columns(worksheet, report_df):
    """
    Smart upsert: write report_df to the worksheet.

    report_df: DataFrame where index = metric names, columns = period labels (week or date strings)

    Logic:
    - Row 1 = headers: ["Metric", period1, period2, ...]
    - Column A = metric labels
    - For periods already in the sheet: overwrite that column
    - For new periods: append as new column(s) to the right
    """
    metric_labels = report_df.index.tolist()
    new_periods = report_df.columns.tolist()

    # Read existing headers from row 1
    existing_data = worksheet.get_all_values()

    if not existing_data or not existing_data[0]:
        # Sheet is empty — write everything fresh
        existing_periods = []
    else:
        existing_periods = existing_data[0][1:]  # skip "Metric" in A1

    # Build the full ordered list of period columns
    all_periods = list(existing_periods)
    for p in new_periods:
        if p not in all_periods:
            all_periods.append(p)
    all_periods.sort()

    # Build the full grid
    num_rows = len(metric_labels) + 1  # +1 for header
    num_cols = len(all_periods) + 1     # +1 for metric label column

    # Header row
    header = ["Metric"] + all_periods

    # Data rows
    rows = [header]
    for i, label in enumerate(metric_labels):
        row = [label]
        for period in all_periods:
            if period in new_periods:
                val = report_df.loc[label, period]
                # Format number
                try:
                    val = round(float(val), 2)
                except (ValueError, TypeError):
                    val = 0
            elif existing_data and i + 1 < len(existing_data):
                # Preserve existing data for periods we're not updating
                period_idx = existing_periods.index(period) + 1 if period in existing_periods else None
                if period_idx is not None and period_idx < len(existing_data[i + 1]):
                    val = existing_data[i + 1][period_idx]
                else:
                    val = ""
            else:
                val = ""
            row.append(val)
        rows.append(row)

    # Write all at once (batch update for performance)
    worksheet.clear()
    worksheet.update(rows, f"A1:{gspread.utils.rowcol_to_a1(num_rows, num_cols)}")

    print(f"  ✅ Updated {len(new_periods)} period(s) in sheet. Total columns: {len(all_periods)}")
