from scheduler_engine import Event, clean_room_name

def load_events_from_rows(rows):
    """
    Parses spreadsheet rows into a list of Event objects.
    Skips headers, section headers, and empty lines.
    """
    events = []
    if not rows:
        return events
        
    for idx, row in enumerate(rows):
        # Pad row to at least 7 columns to avoid IndexError
        if len(row) < 7:
            row = list(row) + [""] * (7 - len(row))
            
        group = row[0].strip()
        event_name = row[1].strip()
        dates_str = row[2].strip()
        time_str = row[3].strip()
        room_str = row[4].strip()
        exclusions_str = row[5].strip()
        notes = row[6].strip()
        
        # Skip header rows
        if group.lower() in ["group", "group name", "tvkcc liturgy", "tvkcc community events", ""]:
            continue
            
        # Skip rows that don't have core scheduling details
        if not dates_str or not time_str or not room_str:
            continue
            
        try:
            event = Event(group, event_name, dates_str, time_str, room_str, exclusions_str, notes)
            events.append(event)
        except Exception as e:
            print(f"Warning: Skipped invalid row #{idx+1} ({row}): {e}")
            
    return events

def find_overlaps(new_event, existing_events):
    """
    Checks if new_event overlaps with any event in existing_events.
    Returns a list of conflict dictionaries:
    {
        "date": datetime.date,
        "room": str,
        "new_time": str,
        "existing_group": str,
        "existing_event": str,
        "existing_time": str
    }
    """
    # Expand new event into intervals
    try:
        new_intervals = new_event.get_intervals()
    except Exception as e:
        raise ValueError(f"Failed to expand new request dates/times: {e}")
        
    # Expand existing events into intervals
    existing_intervals = []
    for ext_ev in existing_events:
        try:
            existing_intervals.extend(ext_ev.get_intervals())
        except Exception as e:
            # If an existing event fails to expand, we skip it with a warning
            print(f"Warning: Failed to expand existing event '{ext_ev.name}': {e}")
            
    conflicts = []
    
    # Check for overlaps
    # Interval format: (room, start_dt, end_dt, group, name)
    for new_room, new_start, new_end, new_grp, new_name in new_intervals:
        for ext_room, ext_start, ext_end, ext_grp, ext_name in existing_intervals:
            if new_room == ext_room:
                # Direct room match
                # Intervals overlap if: start1 < end2 and start2 < end1
                if new_start < ext_end and ext_start < new_end:
                    # Construct clean time strings
                    new_time_str = f"{new_start.strftime('%I:%M %p')} - {new_end.strftime('%I:%M %p')}"
                    ext_time_str = f"{ext_start.strftime('%I:%M %p')} - {ext_end.strftime('%I:%M %p')}"
                    
                    conflict = {
                        "date": new_start.date(),
                        "room": new_room,
                        "new_time": new_time_str,
                        "existing_group": ext_grp,
                        "existing_event": ext_name,
                        "existing_time": ext_time_str
                    }
                    conflicts.append(conflict)
                    
    # Sort conflicts by date, then room, then start time
    conflicts.sort(key=lambda c: (c["date"], c["room"]))
    return conflicts

def format_conflicts(conflicts):
    """Formats conflict dictionaries into a highly readable, elegant text report."""
    if not conflicts:
        return "No overlaps detected!"
        
    report = []
    report.append(f"### ⚠️ Facility Overlaps Detected ({len(conflicts)})")
    report.append("Please resolve the following conflicts before adding this request:\n")
    
    current_date = None
    for conf in conflicts:
        date_str = conf["date"].strftime("%A, %m/%d/%Y")
        if date_str != current_date:
            report.append(f"**📅 {date_str}**")
            current_date = date_str
            
        report.append(
            f"  - **{conf['room']}**: Proposed `{conf['new_time']}` overlaps with:\n"
            f"    👉 *{conf['existing_group']} - {conf['existing_event']}* `{conf['existing_time']}`"
        )
        
    return "\n".join(report)
