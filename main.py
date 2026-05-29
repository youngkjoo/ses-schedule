import sys
import argparse
import json
import os
from scheduler_engine import Event, clean_room_name
import sheets_client
import overlap_detector
import calendar_generator

LITURGY_EVENTS_2026_2027 = [
    ["x", "Liturgy", "TVKCC Sunday Block", "Every Sun", "7 AM - 1:00PM", "Church\nChapel\nCry Room\nRoom A\nRoom B\nVestibule\nKitchen", "9/13 & 9/20: Chapel", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Daily Mass", "Every Tue, Thr, Fri", "9:30 AM - 11 AM", "Chapel", "9/10/2026, 9/11/2026, 9/17/2026, 9/18/2026, 12/25/2026, 1/1/2027", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Assumption of Mary Mass", "8/15/2026 (Sat)", "9:30 AM - 11 AM\n7:30 PM - 9 PM", "Chapel", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "새신자 환영회", "8/16/2026 (Sun)", "11 AM - 12 PM", "Room A", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Vigil Mass for TVKCC Bazaar Volunteers", "9/26/2026 (Sat)", "5:30 PM - 7 PM", "Chapel", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "TVKCC Bazaar", "9/27/2026 (Sun)", "7 AM - 5 PM", "JP2\nParking lot", "Yes", "NOTHING SCHEDULED - AS LONG AS GREG IS OK WITH THIS", "", ""],
    ["x", "Liturgy", "Advent Sacrament of Reconciliation", "12/16/2026 (Wed)", "6 PM - 8 PM", "Chapel", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Nativity of the Lord Night Mass", "12/24/2026 (Thr)", "7 PM - 10 PM", "Church", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Christmas - Reception", "12/24/2026 (Thr)", "2 PM - 11:55 PM", "JP2", "Yes", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Nativity of the Lord Mass", "12/25/2026 (Fri)", "8 AM - 10:30 AM", "Church", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "New Year's Eve Mass", "12/31/2026 (Thr)", "8 PM - 9 PM", "Chapel", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Solemnity of Mary, the Holy Mother of God Mass", "1/1/2027 (Fri)", "9:30 AM - 11:30 AM", "Chapel", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Ash Wednesday Mass", "2/10/2027 (Wed)", "9:30 AM - 11:00 AM\n7:30 PM - 9:00 PM", "Chapel", "", "SCHEDULED AS REQUESTED", "", ""],
    ["x", "Liturgy", "Lent Stations of the Crosss", "2/12, 2/19, 2/26, 3/5, 3/12, 3/19", "7:00 PM - 9:00 PM", "Church", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Palm Sunday Prep", "3/17/2027 (Wed)", "10 AM - 1 PM", "Room A", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Lent Sacrament of Reconciliation", "3/17/2027 (Wed)", "7 PM - 9 PM", "Chapel", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Holy Thursday Prep", "3/24/2027 (Wed)", "3:00 PM - 5:00 PM", "Chapel", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Holy Thursday Mass", "3/25/2027 (Thr)", "7:00 PM - 10:00 PM", "Church", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Eucharistic Adoration", "3/25/2027 (Thr) - 3/26/2027 (Fri)", "9:00 PM - 7:00 AM", "Chapel", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Holy Friday Stations of the Cross", "3/26/2027 (Fri)", "3:00 PM - 4:00 PM", "Church", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Holy Friday Liturgy", "3/26/2027 (Fri)", "8:00 PM - 9:00 PM", "Church", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Easter Vigil", "3/27/2027 (Sat)", "7:00 PM - 10:00 PM", "Church", "", "SCHEDULED", "", ""],
    ["x", "Liturgy", "Triduum - Easter Mass", "3/27/2027 (Sat)", "2 PM - 11:55 PM", "JP2", "Yes", "SCHEDULED", "", ""]
]

def insert_row_by_layout(all_rows, new_row):
    """
    Inserts a row into the spreadsheet data array preserving structure:
    - Liturgy events go under "TVKCC Liturgy" section (before "TVKCC Community Events")
    - Other events go at the end of the sheet
    """
    new_row = list(new_row) + [""] * (10 - len(new_row))
    
    group = new_row[1].strip()
    is_liturgy = "liturgy" in group.lower()
    
    if is_liturgy:
        insert_idx = len(all_rows)
        for idx, row in enumerate(all_rows):
            if len(row) > 1 and "tvkcc community events" in row[1].strip().lower():
                insert_idx = idx
                break
        
        all_rows.insert(insert_idx, new_row)
        print(f"Positioned Liturgy event under TVKCC Liturgy section (Row index {insert_idx})")
    else:
        all_rows.append(new_row)
        print("Positioned Community event at the end of the sheet")
        
    return all_rows

def cmd_check(args):
    try:
        new_event = Event(
            args.group, args.event, args.dates, args.time, args.room, args.exclusions, args.notes or ""
        )
    except Exception as e:
        print(f"❌ Error parsing request fields: {e}")
        return False
        
    print(f"🔄 Checking request '{new_event.name}' for {new_event.group} in rooms {new_event.rooms}...")
    
    try:
        rows = sheets_client.get_all_rows()
    except Exception as e:
        print(f"❌ Error fetching sheet: {e}")
        return False
        
    existing_events = overlap_detector.load_events_from_rows(rows)
    print(f"ℹ️ Loaded {len(existing_events)} existing scheduled events.")
    
    conflicts = overlap_detector.find_overlaps(new_event, existing_events)
    if conflicts:
        print(overlap_detector.format_conflicts(conflicts))
        return False
    else:
        print("✨ Success: No overlaps detected!")
        return True

def cmd_add(args):
    try:
        new_event = Event(
            args.group, args.event, args.dates, args.time, args.room, args.exclusions or "", args.notes or ""
        )
    except Exception as e:
        print(f"❌ Error parsing request fields: {e}")
        return False
        
    print(f"🔄 Checking overlaps for '{new_event.name}'...")
    
    try:
        rows = sheets_client.get_all_rows()
    except Exception as e:
        print(f"❌ Error fetching sheet: {e}")
        return False
        
    existing_events = overlap_detector.load_events_from_rows(rows)
    conflicts = overlap_detector.find_overlaps(new_event, existing_events)
    
    if conflicts:
        print(overlap_detector.format_conflicts(conflicts))
        print("❌ Overlaps found. Request was NOT added to the sheet.")
        return False
        
    # No conflicts, proceed to write using the standardized fields from new_event!
    new_row = [
        "x", # status code
        new_event.group,
        new_event.name,
        new_event.dates_str,
        new_event.time_str,
        new_event.room_str,
        new_event.exclusions_str or "",
        new_event.notes or "",
        "", ""
    ]
    
    updated_rows = insert_row_by_layout(rows, new_row)
    
    try:
        sheets_client.overwrite_all(updated_rows)
        print(f"✨ Successfully booked and saved '{new_event.name}' for {new_event.group}!")
        
        # Automatically regenerate the calendar HTML view in real-time
        calendar_generator.generate_calendar_html()
        
        return True
    except Exception as e:
        print(f"❌ Error updating sheet: {e}")
        return False

def cmd_load_liturgy(args):
    print("🔄 Preparing to batch load all 2026-2027 TVKCC Liturgy events...")
    
    try:
        rows = sheets_client.get_all_rows()
    except Exception as e:
        print(f"❌ Error reading sheet: {e}")
        return False
        
    updated_rows = list(rows)
    for row in LITURGY_EVENTS_2026_2027:
        updated_rows = insert_row_by_layout(updated_rows, row)
        
    try:
        sheets_client.overwrite_all(updated_rows)
        print(f"✨ Successfully batch-loaded all {len(LITURGY_EVENTS_2026_2027)} Liturgy events into the Google Sheet!")
        
        # Automatically regenerate the calendar HTML view in real-time
        calendar_generator.generate_calendar_html()
        
        return True
    except Exception as e:
        print(f"❌ Error saving batch Liturgy load: {e}")
        return False

def cmd_setup_url(args):
    sheets_client.set_web_app_url(args.url)
    return True

def main():
    parser = argparse.ArgumentParser(description="Church Facility Booking System CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    url_parser = subparsers.add_parser("setup-url", help="Configure Google Sheets Apps Script Web App URL")
    url_parser.add_argument("url", help="Web App URL")
    
    check_parser = subparsers.add_parser("check", help="Check request for overlaps")
    check_parser.add_argument("--group", required=True)
    check_parser.add_argument("--event", required=True)
    check_parser.add_argument("--dates", required=True)
    check_parser.add_argument("--time", required=True)
    check_parser.add_argument("--room", required=True)
    check_parser.add_argument("--exclusions", default="")
    check_parser.add_argument("--notes", default="")
    
    add_parser = subparsers.add_parser("add", help="Add request to sheet if no overlaps exist")
    add_parser.add_argument("--group", required=True)
    add_parser.add_argument("--event", required=True)
    add_parser.add_argument("--dates", required=True)
    add_parser.add_argument("--time", required=True)
    add_parser.add_argument("--room", required=True)
    add_parser.add_argument("--exclusions", default="")
    add_parser.add_argument("--notes", default="")
    
    subparsers.add_parser("load-liturgy", help="Batch load the 2026-2027 TVKCC Liturgy schedule")
    
    args = parser.parse_args()
    
    if args.command == "setup-url":
        cmd_setup_url(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "load-liturgy":
        cmd_load_liturgy(args)

if __name__ == "__main__":
    main()
