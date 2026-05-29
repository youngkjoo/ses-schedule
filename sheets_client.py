import json
import urllib.request
import urllib.parse
import os
import csv

CONFIG_FILE = "config.json"

def get_web_app_url():
    """Reads the Web App URL from config.json if it exists."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("web_app_url")
        except Exception:
            pass
    return None

def set_web_app_url(url):
    """Saves the Web App URL to config.json."""
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    data["web_app_url"] = url.strip()
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Saved Web App URL to {CONFIG_FILE}")

def get_all_rows(sheet_name="8/2026 - 7/2027"):
    """
    Fetches all rows from the spreadsheet.
    If the web_app_url is set, queries the Google Sheets Web App.
    Otherwise, falls back to the local sheet_2026_2027.csv or sheet_2025_2026.csv.
    """
    url = get_web_app_url()
    if url:
        try:
            query = urllib.parse.urlencode({"sheet": sheet_name})
            full_url = f"{url}?{query}"
            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if "rows" in res_data:
                    return res_data["rows"]
                elif "error" in res_data:
                    raise Exception(f"Apps Script Error: {res_data['error']}")
        except Exception as e:
            print(f"Warning: Failed to connect to Google Sheets Web App ({e}). Falling back to local CSV.")
            
    # Fallback to local CSV files
    csv_filename = "sheet_2026_2027.csv" if "2026" in sheet_name else "sheet_2025_2026.csv"
    if os.path.exists(csv_filename):
        rows = []
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
        return rows
    else:
        raise Exception(f"No Web App URL configured and local CSV file '{csv_filename}' not found.")

def overwrite_all(rows, sheet_name="8/2026 - 7/2027"):
    """Overwrites the entire sheet with the provided rows."""
    if not rows:
        return True
        
    # Rectangular Normalization:
    # Ensure every single row has the exact same number of columns.
    # This prevents the Apps Script "number of columns does not match" error.
    max_cols = max(len(row) for row in rows)
    normalized_rows = [list(row) + [""] * (max_cols - len(row)) for row in rows]
    
    url = get_web_app_url()
    if url:
        try:
            payload = json.dumps({
                "action": "overwrite_all",
                "rows": normalized_rows,
                "sheet": sheet_name
            }).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=payload, 
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("success"):
                    return True
                else:
                    raise Exception(f"Apps Script Error: {res_data.get('error')}")
        except Exception as e:
            print(f"Warning: Failed to connect to Google Sheets Web App ({e}). Overwriting local CSV.")
            
    # Local fallback
    csv_filename = "sheet_2026_2027.csv" if "2026" in sheet_name else "sheet_2025_2026.csv"
    with open(csv_filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(normalized_rows)
    print(f"Offline: Overwrote local CSV '{csv_filename}' with {len(normalized_rows)} rows.")
    return True

def append_row(row, sheet_name="8/2026 - 7/2027"):
    """
    Appends a single row to the sheet.
    Queries the Web App if configured, otherwise appends to the local CSV.
    """
    url = get_web_app_url()
    if url:
        try:
            payload = json.dumps({
                "action": "append",
                "row": row,
                "sheet": sheet_name
            }).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=payload, 
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("success"):
                    return True
                else:
                    raise Exception(f"Apps Script Error: {res_data.get('error')}")
        except Exception as e:
            print(f"Warning: Failed to connect to Google Sheets Web App ({e}). Appending to local CSV.")
            
    # Local fallback
    csv_filename = "sheet_2026_2027.csv" if "2026" in sheet_name else "sheet_2025_2026.csv"
    if os.path.exists(csv_filename):
        with open(csv_filename, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        print(f"Offline: Appended row to local CSV: {row}")
        return True
    else:
        raise Exception(f"No Web App URL configured and local CSV file '{csv_filename}' not found.")

def batch_append_rows(rows, sheet_name="8/2026 - 7/2027"):
    """
    Appends a list of rows to the sheet in a single batch.
    Queries the Web App if configured, otherwise appends to the local CSV.
    """
    url = get_web_app_url()
    if url:
        try:
            payload = json.dumps({
                "action": "batch_append",
                "rows": rows,
                "sheet": sheet_name
            }).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=payload, 
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("success"):
                    return True
                else:
                    raise Exception(f"Apps Script Error: {res_data.get('error')}")
        except Exception as e:
            print(f"Warning: Failed to connect to Google Sheets Web App ({e}). Batch appending to local CSV.")
            
    # Local fallback
    csv_filename = "sheet_2026_2027.csv" if "2026" in sheet_name else "sheet_2025_2026.csv"
    if os.path.exists(csv_filename):
        with open(csv_filename, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
        print(f"Offline: Batch appended {len(rows)} rows to local CSV.")
        return True
    else:
        raise Exception(f"No Web App URL configured and local CSV file '{csv_filename}' not found.")
