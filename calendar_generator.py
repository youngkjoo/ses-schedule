import json
import calendar
import os
import re
from datetime import date, datetime, timedelta
import sheets_client
import overlap_detector

FACILITIES = ["Church", "Chapel", "Cry Room", "Room A", "Room B", "JP2", "Parking Lot"]

MONTHS_LIST = [
    (2026, 8, "August 2026"),
    (2026, 9, "September 2026"),
    (2026, 10, "October 2026"),
    (2026, 11, "November 2026"),
    (2026, 12, "December 2026"),
    (2027, 1, "January 2027"),
    (2027, 2, "February 2027"),
    (2027, 3, "March 2027"),
    (2027, 4, "April 2027"),
    (2027, 5, "May 2027"),
    (2027, 6, "June 2027"),
    (2027, 7, "July 2027"),
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSLATIONS_FILE = os.path.join(SCRIPT_DIR, "translations.json")

def load_translations():
    """Loads the canonical translation glossary."""
    if os.path.exists(TRANSLATIONS_FILE):
        try:
            with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not load translations.json: {e}")
    return {"ui": {}, "facilities": {}, "months": {}, "weekdays": {}, "groups": {}, "events": {}, "pattern_rules": []}

def translate_group(group_name, translations):
    """Translates group name using glossary with case-insensitive fallback."""
    if not group_name:
        return ""
    groups_map = translations.get("groups", {})
    if group_name in groups_map:
        return groups_map[group_name]
    for k, v in groups_map.items():
        if k.lower() == group_name.lower():
            return v
    return group_name

def translate_event(event_name, group_name, translations):
    """Translates event name using glossary and regex pattern rules."""
    if not event_name:
        return ""
    events_map = translations.get("events", {})
    if event_name in events_map:
        return events_map[event_name]
    for k, v in events_map.items():
        if k.lower() == event_name.lower():
            return v
    
    rules = translations.get("pattern_rules", [])
    for rule in rules:
        pat = rule.get("pattern")
        rep = rule.get("replacement")
        if pat and rep and re.search(pat, event_name):
            return re.sub(pat, rep, event_name)
            
    return event_name

def format_korean_time(start_dt, end_dt):
    """Formats time in standard Korean convention (오전/오후 H:MM - 오전/오후 H:MM)."""
    start_ampm = "오전" if start_dt.strftime("%p") == "AM" else "오후"
    end_ampm = "오전" if end_dt.strftime("%p") == "AM" else "오후"
    start_str = f"{start_ampm} {start_dt.strftime('%-I:%M')}"
    end_str = f"{end_ampm} {end_dt.strftime('%-I:%M')}"
    return f"{start_str} - {end_str}"

def render_responsive_html(monthly_grids, translations, default_lang="en", is_ko_subdir=False):
    """Generates the multi-screen responsive calendar HTML with Agenda and Matrix views."""
    ui = translations.get("ui", {}).get(default_lang, translations.get("ui", {}).get("en", {}))
    
    # Facility headers for Table View
    facility_headers_html = []
    for room in FACILITIES:
        room_data = translations.get("facilities", {}).get(room, {})
        cell_content = room_data.get(f"bilingual_{default_lang}", room)
        room_id = "th_" + re.sub(r"[^a-zA-Z0-9_]", "_", room)
        col_class = "col-" + re.sub(r"[^a-zA-Z0-9_]", "_", room).lower()
        facility_headers_html.append(f'<th id="{room_id}" class="{col_class}">{cell_content}</th>')
    facility_headers_str = "".join(facility_headers_html)

    # Room filter chips for Table View
    room_chips_html = []
    for room in FACILITIES:
        r_label = translations.get("facilities", {}).get(room, {}).get("ko" if default_lang == "ko" else "en", room)
        room_chips_html.append(f'<button class="room-filter-chip" data-room="{room}" onclick="selectRoomFilter(\'{room}\')">{r_label}</button>')
    room_chips_str = "".join(room_chips_html)

    # Determine initial month key matching today's date
    today_dt = date.today()
    candidate_key = f"{today_dt.year}-{today_dt.month}"
    available_keys = [m["key"] for m in monthly_grids]
    if candidate_key in available_keys:
        initial_month_key = candidate_key
    elif today_dt < date(2026, 8, 1):
        initial_month_key = available_keys[0]
    else:
        initial_month_key = available_keys[-1]

    return f"""<!DOCTYPE html>
<html lang="{default_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{ui.get('title', 'TVKCC Facility Reservation Requests')}</title>
    
    <!-- Anti-Caching Directives -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-color: #080b11;
            --surface-color: #121824;
            --surface-lighter: #1b2436;
            --surface-card: #182030;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            --sunday-bg: rgba(239, 68, 68, 0.08);
            --sunday-border: rgba(239, 68, 68, 0.2);
            --sunday-text: #f87171;
            --saturday-bg: rgba(59, 130, 246, 0.06);
            --saturday-text: #60a5fa;
            --accent-glow: 0 0 20px rgba(99, 102, 241, 0.25);
            --tag-liturgy: #3b82f6;
            --tag-community: #10b981;
            
            /* Facility Color Tags */
            --room-church-bg: rgba(59, 130, 246, 0.15);
            --room-church-text: #93c5fd;
            --room-church-border: rgba(59, 130, 246, 0.35);

            --room-chapel-bg: rgba(99, 102, 241, 0.15);
            --room-chapel-text: #c7d2fe;
            --room-chapel-border: rgba(99, 102, 241, 0.35);

            --room-cry-bg: rgba(168, 85, 247, 0.15);
            --room-cry-text: #e9d5ff;
            --room-cry-border: rgba(168, 85, 247, 0.35);

            --room-rooma-bg: rgba(16, 185, 129, 0.15);
            --room-rooma-text: #a7f3d0;
            --room-rooma-border: rgba(16, 185, 129, 0.35);

            --room-roomb-bg: rgba(20, 184, 166, 0.15);
            --room-roomb-text: #99f6e4;
            --room-roomb-border: rgba(20, 184, 166, 0.35);

            --room-jp2-bg: rgba(245, 158, 11, 0.15);
            --room-jp2-text: #fde68a;
            --room-jp2-border: rgba(245, 158, 11, 0.35);

            --room-parking-bg: rgba(148, 163, 184, 0.15);
            --room-parking-text: #cbd5e1;
            --room-parking-border: rgba(148, 163, 184, 0.35);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 1rem;
            min-height: 100dvh;
            line-height: 1.5;
            overflow-x: hidden;
            -webkit-tap-highlight-color: transparent;
        }}

        @media (min-width: 768px) {{
            body {{
                padding: 2rem 1.5rem;
            }}
        }}

        /* Header Container */
        header {{
            max-width: 1600px;
            margin: 0 auto 1.25rem auto;
            background: rgba(18, 24, 36, 0.7);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            padding: 1.25rem 1.25rem;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        @media (min-width: 992px) {{
            header {{
                flex-direction: row;
                justify-content: space-between;
                align-items: center;
                padding: 1.5rem 2rem;
                border-radius: 20px;
                margin-bottom: 1.75rem;
            }}
        }}

        .brand {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}

        h1 {{
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-size: clamp(1.25rem, 2.5vw, 1.75rem);
            font-weight: 700;
            background: linear-gradient(90deg, #a5b4fc 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.25;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: clamp(0.8rem, 1.5vw, 0.9rem);
            font-weight: 500;
        }}

        /* Header Controls Toolbar */
        .header-toolbar {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            width: 100%;
        }}

        @media (min-width: 992px) {{
            .header-toolbar {{
                width: auto;
                align-items: flex-end;
            }}
        }}

        .toolbar-row-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}

        @media (min-width: 992px) {{
            .toolbar-row-top {{
                justify-content: flex-end;
            }}
        }}

        .toolbar-row-bottom {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
            width: 100%;
        }}

        @media (min-width: 992px) {{
            .toolbar-row-bottom {{
                width: auto;
            }}
        }}

        /* Segmented Button Groups (View & Language Switchers) */
        .segmented-control {{
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            padding: 3px;
            border-radius: 100px;
            border: 1px solid var(--border-color);
            gap: 2px;
        }}

        .seg-btn, .lang-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.45rem 0.85rem;
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-size: 0.85rem;
            font-weight: 600;
            border-radius: 100px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            white-space: nowrap;
        }}

        .seg-btn:hover, .lang-btn:hover {{
            color: var(--text-color);
        }}

        .seg-btn.active, .lang-btn.active {{
            background: var(--primary-gradient);
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
        }}

        /* Search & Group Filters */
        .filter-wrapper {{
            display: flex;
            gap: 0.75rem;
            align-items: center;
            width: 100%;
            flex-wrap: wrap;
        }}

        @media (min-width: 600px) {{
            .filter-wrapper {{
                flex-wrap: nowrap;
            }}
        }}

        .search-box, .group-select {{
            flex: 1 1 180px;
            position: relative;
        }}

        .search-box input, .group-select select {{
            width: 100%;
            min-height: 44px; /* Accessible touch target */
            padding: 0.65rem 1rem;
            border-radius: 12px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            font-family: inherit;
            font-size: 16px; /* Prevents iOS auto-zoom */
            transition: all 0.25s ease;
        }}

        .group-select select {{
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml;utf8,<svg fill='white' height='24' viewBox='0 0 24 24' width='24' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/><path d='M0 0h24v24H0z' fill='none'/></svg>");
            background-repeat: no-repeat;
            background-position: right 0.75rem center;
            background-size: 1.25rem;
            padding-right: 2.25rem;
        }}

        .group-select select option {{
            background-color: var(--surface-color);
            color: var(--text-color);
        }}

        .search-box input:focus, .group-select select:focus {{
            outline: none;
            border-color: #6366f1;
            box-shadow: var(--accent-glow);
        }}

        /* Month Tab Bar Switcher */
        .month-tabs-container {{
            max-width: 1600px;
            margin: 0 auto 1.25rem auto;
            overflow-x: auto;
            white-space: nowrap;
            padding-bottom: 0.4rem;
            scrollbar-width: none;
            -webkit-overflow-scrolling: touch;
        }}

        .month-tabs-container::-webkit-scrollbar {{
            display: none;
        }}

        .month-tabs {{
            display: flex;
            gap: 0.5rem;
        }}

        .month-tab {{
            min-height: 40px;
            padding: 0.5rem 1.15rem;
            border-radius: 100px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            flex-shrink: 0;
        }}

        .month-tab:hover {{
            color: var(--text-color);
            border-color: var(--border-hover);
            background-color: var(--surface-lighter);
        }}

        .month-tab.active {{
            background: var(--primary-gradient);
            color: #ffffff;
            border-color: transparent;
            box-shadow: var(--accent-glow);
        }}

        /* ==========================================================================
           VIEW 1: AGENDA VIEW (Mobile-First / Card Layout)
           ========================================================================== */
        #agendaView {{
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        /* Responsive Grid for Tablets & Desktops in Agenda mode */
        @media (min-width: 768px) {{
            .agenda-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
                gap: 1.25rem;
                align-items: start;
            }}
        }}

        .agenda-day-card {{
            background-color: var(--surface-color);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        .agenda-day-card:hover {{
            border-color: var(--border-hover);
        }}

        .agenda-day-card.sunday {{
            border-top: 3px solid #ef4444;
        }}

        .agenda-day-card.saturday {{
            border-top: 3px solid #3b82f6;
        }}

        .agenda-day-card.today {{
            border: 2px solid #818cf8;
            box-shadow: 0 0 24px rgba(99, 102, 241, 0.4);
            position: relative;
        }}

        .today-badge {{
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            color: #ffffff;
            font-size: 0.68rem;
            font-weight: 700;
            padding: 0.15rem 0.55rem;
            border-radius: 100px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
            display: inline-flex;
            align-items: center;
        }}

        tr.today {{
            background-color: rgba(99, 102, 241, 0.12) !important;
        }}

        tr.today td:first-child {{
            background-color: #1e2842 !important;
            border-left: 4px solid #818cf8;
            box-shadow: inset 0 0 10px rgba(99, 102, 241, 0.3);
            color: #a5b4fc !important;
        }}

        .agenda-day-header {{
            background: var(--surface-lighter);
            padding: 0.75rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }}

        .agenda-day-title {{
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }}

        .agenda-day-number {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
        }}

        .agenda-day-card.sunday .agenda-day-number {{
            color: var(--sunday-text);
        }}

        .agenda-day-card.saturday .agenda-day-number {{
            color: var(--saturday-text);
        }}

        .agenda-day-weekday {{
            font-size: 0.85rem;
            font-weight: 600;
            opacity: 0.75;
        }}

        .agenda-count-badge {{
            font-size: 0.75rem;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.08);
            padding: 0.2rem 0.6rem;
            border-radius: 100px;
            color: var(--text-muted);
        }}

        .agenda-events-list {{
            padding: 0.75rem 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        .agenda-event-item {{
            background: var(--surface-card);
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
            border-left: 4px solid var(--tag-community);
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            transition: all 0.2s ease;
        }}

        .agenda-event-item.liturgy {{
            border-left-color: var(--tag-liturgy);
        }}

        .agenda-event-item:hover {{
            background: rgba(255, 255, 255, 0.06);
            transform: translateX(2px);
        }}

        .agenda-event-meta {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .agenda-event-time {{
            font-size: 0.8rem;
            font-weight: 700;
            color: #cbd5e1;
            font-variant-numeric: tabular-nums;
        }}

        /* Room Pill Badges */
        .room-badge {{
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            border: 1px solid transparent;
            white-space: nowrap;
        }}

        .room-badge.church {{ background: var(--room-church-bg); color: var(--room-church-text); border-color: var(--room-church-border); }}
        .room-badge.chapel {{ background: var(--room-chapel-bg); color: var(--room-chapel-text); border-color: var(--room-chapel-border); }}
        .room-badge.cry_room {{ background: var(--room-cry-bg); color: var(--room-cry-text); border-color: var(--room-cry-border); }}
        .room-badge.room_a {{ background: var(--room-rooma-bg); color: var(--room-rooma-text); border-color: var(--room-rooma-border); }}
        .room-badge.room_b {{ background: var(--room-roomb-bg); color: var(--room-roomb-text); border-color: var(--room-roomb-border); }}
        .room-badge.jp2 {{ background: var(--room-jp2-bg); color: var(--room-jp2-text); border-color: var(--room-jp2-border); }}
        .room-badge.parking_lot {{ background: var(--room-parking-bg); color: var(--room-parking-text); border-color: var(--room-parking-border); }}

        .agenda-event-name {{
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-color);
            line-height: 1.35;
        }}

        .agenda-event-group {{
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 500;
        }}

        /* Empty State */
        .empty-state {{
            padding: 3rem 1.5rem;
            text-align: center;
            color: var(--text-muted);
            background: var(--surface-color);
            border-radius: 16px;
            border: 1px dashed var(--border-color);
            font-size: 0.95rem;
        }}

        /* ==========================================================================
           VIEW 2: MATRIX GRID VIEW (Full Facility Table)
           ========================================================================== */
        #gridView {{
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        /* Room Filter Bar for Mobile/Tablet Grid View */
        .grid-room-filter-container {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            overflow-x: auto;
            scrollbar-width: none;
            padding-bottom: 0.35rem;
            -webkit-overflow-scrolling: touch;
        }}

        .grid-room-filter-container::-webkit-scrollbar {{
            display: none;
        }}

        .grid-room-filter-label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 600;
            white-space: nowrap;
            margin-right: 0.25rem;
        }}

        .room-filter-chip {{
            min-height: 34px;
            padding: 0.35rem 0.85rem;
            border-radius: 100px;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
            flex-shrink: 0;
        }}

        .room-filter-chip:hover {{
            color: var(--text-color);
            border-color: var(--border-hover);
        }}

        .room-filter-chip.active {{
            background: var(--surface-lighter);
            color: #ffffff;
            border-color: #6366f1;
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.25);
        }}

        .calendar-wrapper {{
            background-color: var(--surface-color);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}

        @media (min-width: 768px) {{
            .calendar-wrapper {{
                border-radius: 20px;
            }}
        }}

        .table-responsive {{
            width: 100%;
            overflow-x: auto;
            overflow-y: auto;
            max-height: calc(100dvh - 300px);
            scrollbar-width: thin;
        }}

        .table-responsive::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}

        .table-responsive::-webkit-scrollbar-thumb {{
            background-color: rgba(255, 255, 255, 0.15);
            border-radius: 3px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            table-layout: fixed;
            min-width: 900px;
        }}

        th, td {{
            padding: 1rem 0.85rem;
            border-bottom: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            vertical-align: top;
        }}

        th:last-child, td:last-child {{
            border-right: none;
        }}

        thead th {{
            background-color: var(--surface-lighter);
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-weight: 700;
            font-size: 0.9rem;
            color: #a5b4fc;
            position: sticky;
            top: 0;
            z-index: 10;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            line-height: 1.35;
        }}

        .sub-lang {{
            font-size: 0.75rem;
            font-weight: 500;
            opacity: 0.7;
        }}

        thead th:first-child {{
            width: 80px;
            position: sticky;
            top: 0;
            left: 0;
            z-index: 12;
            border-right: 2px solid var(--border-color);
            text-align: center;
        }}

        td:first-child {{
            position: sticky;
            left: 0;
            background-color: var(--surface-lighter);
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-weight: 700;
            font-size: 1rem;
            z-index: 5;
            text-align: center;
            border-right: 2px solid var(--border-color);
            width: 80px;
        }}

        tbody tr:hover {{
            background-color: rgba(255, 255, 255, 0.02);
        }}

        tr.sunday {{
            background-color: var(--sunday-bg);
        }}

        tr.sunday td:first-child {{
            background-color: #2a1616;
            color: var(--sunday-text);
            border-right: 2px solid var(--sunday-border);
        }}

        tr.saturday {{
            background-color: var(--saturday-bg);
        }}

        tr.saturday td:first-child {{
            background-color: #121c33;
            color: var(--saturday-text);
        }}

        .booking-list {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .booking-card {{
            background: var(--surface-lighter);
            border-left: 4px solid var(--tag-community);
            border-radius: 8px;
            padding: 0.6rem 0.75rem;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .booking-card.liturgy {{
            border-left-color: var(--tag-liturgy);
        }}

        .booking-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            background-color: rgba(255, 255, 255, 0.06);
        }}

        .booking-time {{
            font-weight: 700;
            color: #cbd5e1;
            margin-bottom: 0.2rem;
            font-size: 0.78rem;
        }}

        .booking-event {{
            font-weight: 600;
            color: var(--text-color);
            margin-bottom: 0.1rem;
            line-height: 1.3;
        }}

        .booking-group {{
            color: var(--text-muted);
            font-size: 0.75rem;
            font-weight: 500;
        }}

        .empty-cell-text {{
            color: rgba(255, 255, 255, 0.05);
            font-size: 0.8rem;
            font-style: italic;
            user-select: none;
        }}

        .hidden-booking, .hidden-room-col, .hidden-agenda-item {{
            display: none !important;
        }}
    </style>
</head>
<body>

    <!-- Responsive Glassmorphic Header -->
    <header>
        <div class="brand">
            <h1 id="pageHeading">{ui.get('heading', 'TVKCC Facility Reservation Requests')}</h1>
            <div class="subtitle" id="pageSubtitle">{ui.get('subtitle', 'Facility Schedule Planning Year: 8/2026 - 7/2027')}</div>
        </div>
        
        <div class="header-toolbar">
            <!-- Top row: View Switcher + Language Switcher -->
            <div class="toolbar-row-top">
                <!-- View Switcher -->
                <div class="segmented-control" role="group" aria-label="View Switcher">
                    <button class="seg-btn active" id="viewBtnAgenda" onclick="setViewMode('agenda')">
                        <span id="labelViewAgenda">{ui.get('view_agenda', '📋 Agenda')}</span>
                    </button>
                    <button class="seg-btn" id="viewBtnGrid" onclick="setViewMode('grid')">
                        <span id="labelViewGrid">{ui.get('view_grid', '⊞ Grid')}</span>
                    </button>
                </div>
                
                <!-- Language Switcher -->
                <div class="segmented-control" role="group" aria-label="Language Switcher">
                    <button class="lang-btn {'active' if default_lang == 'en' else ''}" id="langBtnEn" onclick="switchLanguage('en')">EN</button>
                    <button class="lang-btn {'active' if default_lang == 'ko' else ''}" id="langBtnKo" onclick="switchLanguage('ko')">한국어</button>
                </div>
            </div>

            <!-- Bottom row: Search + Group Filters -->
            <div class="toolbar-row-bottom">
                <div class="filter-wrapper">
                    <div class="group-select">
                        <select id="groupFilter" onchange="handleFilter()">
                            <option value="">{ui.get('all_groups', '👥 All Groups')}</option>
                        </select>
                    </div>
                    <div class="search-box">
                        <input type="text" id="search" placeholder="{ui.get('search_placeholder', '🔍 Search by Event...')}" oninput="handleFilter()" autocomplete="off">
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Month Tab Bar Switcher -->
    <div class="month-tabs-container">
        <div class="month-tabs" id="monthTabs"></div>
    </div>

    <!-- VIEW 1: AGENDA VIEW (Mobile & Tablet friendly cards) -->
    <main id="agendaView">
        <div class="agenda-grid" id="agendaList"></div>
    </main>

    <!-- VIEW 2: MATRIX GRID VIEW (Full Facility Table) -->
    <main id="gridView" style="display: none;">
        <!-- Quick Room Filter Chips (especially helpful on mobile / tablet) -->
        <div class="grid-room-filter-container" id="roomFilterContainer">
            <span class="grid-room-filter-label" id="filterRoomLabel">{ui.get('filter_by_room', 'Filter Room:')}</span>
            <button class="room-filter-chip active" data-room="all" onclick="selectRoomFilter('all')">{ui.get('all_rooms', 'All Facilities')}</button>
            {room_chips_str}
        </div>

        <div class="calendar-wrapper">
            <div class="table-responsive">
                <table id="facilityTable">
                    <thead>
                        <tr>
                            <th id="dayColHeader">{ui.get('day_header', 'Day')}</th>
                            {facility_headers_str}
                        </tr>
                    </thead>
                    <tbody id="calendarGrid"></tbody>
                </table>
            </div>
        </div>
    </main>

    <script>
        // Injected data and translations
        const calendarData = {json.dumps(monthly_grids, ensure_ascii=False)};
        const translations = {json.dumps(translations, ensure_ascii=False)};
        const FACILITIES = {json.dumps(FACILITIES)};
        const IS_KO_SUBDIR = {str(is_ko_subdir).lower()};
        const INITIAL_DEFAULT_LANG = "{default_lang}";

        // Language resolution: URL Param > Subdirectory mode > LocalStorage > Default
        function resolveInitialLanguage() {{
            const urlParams = new URLSearchParams(window.location.search);
            const paramLang = urlParams.get("lang");
            if (paramLang === "ko" || paramLang === "en") return paramLang;
            if (IS_KO_SUBDIR) return "ko";
            const saved = localStorage.getItem("ses_calendar_lang");
            if (saved === "ko" || saved === "en") return saved;
            return INITIAL_DEFAULT_LANG;
        }}

        // Initial View Mode: Agenda on Mobile (< 768px), Grid on Desktop (>= 768px)
        function resolveInitialView() {{
            const savedView = localStorage.getItem("ses_calendar_view");
            if (savedView === "agenda" || savedView === "grid") return savedView;
            return window.innerWidth < 768 ? "agenda" : "grid";
        }}

        // Resolve Initial Month: Today's Month if within planning year (8/2026 - 7/2027)
        function resolveInitialMonthKey() {{
            const today = new Date();
            const y = today.getFullYear();
            const m = today.getMonth() + 1;
            const candidateKey = `${{y}}-${{m}}`;
            if (calendarData.some(month => month.key === candidateKey)) {{
                return candidateKey;
            }}
            if (y < 2026 || (y === 2026 && m < 8)) {{
                return calendarData[0].key;
            }}
            return calendarData[calendarData.length - 1].key;
        }}

        let currentLang = resolveInitialLanguage();
        let currentView = resolveInitialView();
        let activeMonthKey = resolveInitialMonthKey();
        let selectedRoomFilter = "all";

        // Render Month Navigation Tab Buttons
        const monthTabsEl = document.getElementById("monthTabs");
        calendarData.forEach((month) => {{
            const btn = document.createElement("button");
            btn.className = `month-tab ${{month.key === activeMonthKey ? 'active' : ''}}`;
            btn.id = `monthTab_${{month.key}}`;
            btn.innerText = currentLang === "ko" ? (month.name_ko || month.name) : month.name;
            btn.onclick = () => selectMonth(month.key);
            monthTabsEl.appendChild(btn);
        }});

        function selectMonth(monthKey) {{
            activeMonthKey = monthKey;
            document.querySelectorAll(".month-tab").forEach(tab => {{
                tab.classList.toggle("active", tab.id === `monthTab_${{monthKey}}`);
            }});
            renderCurrentViews();
            
            const activeTab = document.getElementById(`monthTab_${{monthKey}}`);
            if (activeTab) {{
                activeTab.scrollIntoView({{ inline: "center", block: "nearest", behavior: "smooth" }});
            }}
            
            const today = new Date();
            if (monthKey === `${{today.getFullYear()}}-${{today.getMonth() + 1}}`) {{
                scrollToToday(true);
            }}
        }}

        // View Mode Switcher: Agenda vs Grid
        function setViewMode(mode) {{
            currentView = mode;
            localStorage.setItem("ses_calendar_view", mode);
            
            document.getElementById("viewBtnAgenda").classList.toggle("active", mode === "agenda");
            document.getElementById("viewBtnGrid").classList.toggle("active", mode === "grid");
            
            const agendaView = document.getElementById("agendaView");
            const gridView = document.getElementById("gridView");
            
            if (mode === "agenda") {{
                agendaView.style.display = "flex";
                gridView.style.display = "none";
            }} else {{
                agendaView.style.display = "none";
                gridView.style.display = "flex";
            }}
            
            handleFilter();
        }}

        // Room Filter in Grid View
        function selectRoomFilter(room) {{
            selectedRoomFilter = room;
            document.querySelectorAll(".room-filter-chip").forEach(chip => {{
                chip.classList.toggle("active", chip.dataset.room === room);
            }});
            
            FACILITIES.forEach(r => {{
                const colClass = "col-" + r.replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
                const isMatch = (room === "all" || room === r);
                document.querySelectorAll("." + colClass).forEach(cell => {{
                    cell.classList.toggle("hidden-room-col", !isMatch);
                }});
            }});
        }}

        // Format room class helper for CSS
        function getRoomClass(roomName) {{
            return roomName.toLowerCase().replace(/[^a-z0-9]/g, "_");
        }}

        // Render Agenda View
        function renderAgendaView() {{
            const agendaList = document.getElementById("agendaList");
            agendaList.innerHTML = "";
            
            const monthData = calendarData.find(m => m.key === activeMonthKey);
            if (!monthData) return;
            
            let totalEventsRendered = 0;
            const todayObj = new Date();
            const todayY = todayObj.getFullYear();
            const todayM = todayObj.getMonth() + 1;
            const todayD = todayObj.getDate();
            const isTodayMonth = (activeMonthKey === `${{todayY}}-${{todayM}}`);
            const todayLabel = (translations.ui && translations.ui[currentLang] && translations.ui[currentLang].today) || "Today";
            
            monthData.days.forEach(day => {{
                // Collect and sort all bookings for this day chronologically
                const dayEvents = [];
                FACILITIES.forEach(room => {{
                    const roomBookings = day.bookings[room] || [];
                    roomBookings.forEach(b => {{
                        dayEvents.push({{ ...b, room: room }});
                    }});
                }});
                
                if (dayEvents.length === 0) return;
                
                dayEvents.sort((a, b) => (a.start_time_sort || "").localeCompare(b.start_time_sort || ""));
                totalEventsRendered += dayEvents.length;
                
                const isToday = isTodayMonth && (day.day === todayD);
                const card = document.createElement("div");
                card.className = `agenda-day-card ${{day.is_sunday ? 'sunday' : (day.is_saturday ? 'saturday' : '')}} ${{isToday ? 'today' : ''}}`;
                card.dataset.day = day.day;
                if (isToday) card.dataset.isToday = "true";
                
                const weekdayLabel = currentLang === 'ko' ? (day.weekday_ko || day.weekday) : day.weekday;
                const countSuffix = currentLang === 'ko' ? '건' : (dayEvents.length === 1 ? 'event' : 'events');
                
                let eventsHtml = "";
                dayEvents.forEach(b => {{
                    const isLiturgy = b.group.toLowerCase().includes("liturgy") || b.group.toLowerCase() === "tvkcc";
                    const displayEvent = currentLang === 'ko' ? (b.event_ko || b.event) : b.event;
                    const displayGroup = currentLang === 'ko' ? (b.group_ko || b.group) : b.group;
                    const displayTime = currentLang === 'ko' ? (b.time_ko || b.time) : b.time;
                    
                    const roomData = (translations.facilities && translations.facilities[b.room]) || {{}};
                    const displayRoom = currentLang === 'ko' ? (roomData.ko || b.room) : (roomData.en || b.room);
                    const roomCss = getRoomClass(b.room);
                    
                    const searchable = `${{b.group.toLowerCase()}} ${{b.event.toLowerCase()}} ${{(b.group_ko || '').toLowerCase()}} ${{(b.event_ko || '').toLowerCase()}} ${{b.room.toLowerCase()}}`;
                    
                    eventsHtml += `
                        <div class="agenda-event-item ${{isLiturgy ? 'liturgy' : ''}}" 
                             data-searchable="${{searchable}}" 
                             data-group-canonical="${{b.group.toLowerCase().trim()}}">
                            <div class="agenda-event-meta">
                                <span class="agenda-event-time">${{displayTime}}</span>
                                <span class="room-badge ${{roomCss}}">${{displayRoom}}</span>
                            </div>
                            <div class="agenda-event-name">${{displayEvent}}</div>
                            <div class="agenda-event-group">${{displayGroup}}</div>
                        </div>
                    `;
                }});
                
                card.innerHTML = `
                    <div class="agenda-day-header">
                        <div class="agenda-day-title">
                            <span class="agenda-day-number">${{day.day}}</span>
                            <span class="agenda-day-weekday">${{weekdayLabel}}</span>
                            ${{isToday ? `<span class="today-badge">${{todayLabel}}</span>` : ''}}
                        </div>
                        <span class="agenda-count-badge">${{dayEvents.length}} ${{countSuffix}}</span>
                    </div>
                    <div class="agenda-events-list">
                        ${{eventsHtml}}
                    </div>
                `;
                
                agendaList.appendChild(card);
            }});
            
            if (totalEventsRendered === 0) {{
                const ui = (translations.ui && translations.ui[currentLang]) || {{}};
                agendaList.innerHTML = `<div class="empty-state">${{ui.no_events_day || "No events scheduled for this month"}}</div>`;
            }}
        }}

        // Render Matrix Grid View
        function renderGridView() {{
            const gridEl = document.getElementById("calendarGrid");
            gridEl.innerHTML = "";
            
            const monthData = calendarData.find(m => m.key === activeMonthKey);
            if (!monthData) return;
            
            const todayObj = new Date();
            const todayY = todayObj.getFullYear();
            const todayM = todayObj.getMonth() + 1;
            const todayD = todayObj.getDate();
            const isTodayMonth = (activeMonthKey === `${{todayY}}-${{todayM}}`);
            const todayLabel = (translations.ui && translations.ui[currentLang] && translations.ui[currentLang].today) || "Today";
            
            monthData.days.forEach(day => {{
                const isToday = isTodayMonth && (day.day === todayD);
                const row = document.createElement("tr");
                row.dataset.day = day.day;
                if (isToday) {{
                    row.className = "today";
                }} else if (day.is_sunday) {{
                    row.className = "sunday";
                }} else if (day.is_saturday) {{
                    row.className = "saturday";
                }}
                
                const dayCell = document.createElement("td");
                const weekdayLabel = currentLang === 'ko' ? (day.weekday_ko || day.weekday) : day.weekday;
                dayCell.innerHTML = `
                    <div>${{day.day}}</div>
                    <div style="font-size: 0.75rem; font-weight: 500; opacity: 0.6">${{weekdayLabel}}</div>
                    ${{isToday ? `<div style="margin-top: 4px;"><span class="today-badge" style="font-size: 0.62rem; padding: 2px 6px;">${{todayLabel}}</span></div>` : ''}}
                `;
                row.appendChild(dayCell);
                
                FACILITIES.forEach(room => {{
                    const cell = document.createElement("td");
                    const colClass = "col-" + room.replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
                    cell.className = colClass;
                    
                    if (selectedRoomFilter !== "all" && selectedRoomFilter !== room) {{
                        cell.classList.add("hidden-room-col");
                    }}
                    
                    const bookings = day.bookings[room] || [];
                    if (bookings.length === 0) {{
                        cell.innerHTML = '<span class="empty-cell-text">-</span>';
                    }} else {{
                        const listWrapper = document.createElement("div");
                        listWrapper.className = "booking-list";
                        
                        bookings.forEach(b => {{
                            const card = document.createElement("div");
                            const isLiturgy = b.group.toLowerCase().includes("liturgy") || b.group.toLowerCase() === "tvkcc";
                            card.className = `booking-card ${{isLiturgy ? 'liturgy' : ''}}`;
                            
                            const searchableText = `${{b.group.toLowerCase()}} ${{b.event.toLowerCase()}} ${{(b.group_ko || '').toLowerCase()}} ${{(b.event_ko || '').toLowerCase()}} ${{room.toLowerCase()}}`;
                            card.dataset.searchable = searchableText;
                            card.dataset.groupCanonical = b.group.toLowerCase().trim();
                            
                            const displayEvent = currentLang === 'ko' ? (b.event_ko || b.event) : b.event;
                            const displayGroup = currentLang === 'ko' ? (b.group_ko || b.group) : b.group;
                            const displayTime = currentLang === 'ko' ? (b.time_ko || b.time) : b.time;
                            
                            card.innerHTML = `
                                <div class="booking-time">${{displayTime}}</div>
                                <div class="booking-event">${{displayEvent}}</div>
                                <div class="booking-group">${{displayGroup}}</div>
                            `;
                            listWrapper.appendChild(card);
                        }});
                        cell.appendChild(listWrapper);
                    }}
                    row.appendChild(cell);
                }});
                
                gridEl.appendChild(row);
            }});
        }}

        function renderCurrentViews() {{
            renderAgendaView();
            renderGridView();
            handleFilter();
        }}

        // Dynamic Group Filter Population
        function populateGroupFilter() {{
            const groupSelect = document.getElementById("groupFilter");
            const currentSelected = groupSelect.value;
            const allLabel = (translations.ui[currentLang] && translations.ui[currentLang].all_groups) || "👥 All Groups";
            
            groupSelect.innerHTML = `<option value="">${{allLabel}}</option>`;
            
            const groupsMap = new Map();
            calendarData.forEach(month => {{
                month.days.forEach(day => {{
                    Object.values(day.bookings).forEach(roomBookings => {{
                        roomBookings.forEach(b => {{
                            if (b.group) {{
                                const canonical = b.group.trim();
                                if (!groupsMap.has(canonical)) {{
                                    groupsMap.set(canonical, {{
                                        canonical: canonical,
                                        en: canonical,
                                        ko: b.group_ko || canonical
                                    }});
                                }}
                            }}
                        }});
                    }});
                }});
            }});
            
            const sorted = Array.from(groupsMap.values()).sort((a, b) => {{
                const nameA = currentLang === 'ko' ? a.ko : a.en;
                const nameB = currentLang === 'ko' ? b.ko : b.en;
                return nameA.localeCompare(nameB);
            }});
            
            sorted.forEach(grp => {{
                const opt = document.createElement("option");
                opt.value = grp.canonical.toLowerCase();
                opt.innerText = currentLang === 'ko' ? grp.ko : grp.en;
                groupSelect.appendChild(opt);
            }});
            
            if (currentSelected) groupSelect.value = currentSelected;
        }}

        // Combined Filter Handler (Agenda & Grid Views)
        function handleFilter() {{
            const query = document.getElementById("search").value.toLowerCase().trim();
            const groupFilter = document.getElementById("groupFilter").value;
            
            // 1. Filter Grid View Cards
            const gridCards = document.querySelectorAll(".booking-card");
            gridCards.forEach(card => {{
                const searchable = card.dataset.searchable || "";
                const groupCanonical = card.dataset.groupCanonical || "";
                const matches = searchable.includes(query) && (groupFilter === "" || groupCanonical === groupFilter);
                card.classList.toggle("hidden-booking", !matches);
            }});
            
            document.querySelectorAll("#calendarGrid td:not(:first-child)").forEach(cell => {{
                const list = cell.querySelector(".booking-list");
                if (list) {{
                    const visibleCards = list.querySelectorAll(".booking-card:not(.hidden-booking)");
                    let emptyText = cell.querySelector(".empty-cell-text");
                    if (visibleCards.length === 0) {{
                        if (!emptyText) {{
                            emptyText = document.createElement("span");
                            emptyText.className = "empty-cell-text search-hidden";
                            emptyText.innerText = "-";
                            cell.appendChild(emptyText);
                        }}
                        list.style.display = "none";
                    }} else {{
                        if (emptyText) emptyText.remove();
                        list.style.display = "flex";
                    }}
                }}
            }});
            
            // 2. Filter Agenda View Items
            const dayCards = document.querySelectorAll(".agenda-day-card");
            let visibleDaysCount = 0;
            
            dayCards.forEach(dayCard => {{
                const items = dayCard.querySelectorAll(".agenda-event-item");
                let visibleInDay = 0;
                
                items.forEach(item => {{
                    const searchable = item.dataset.searchable || "";
                    const groupCanonical = item.dataset.groupCanonical || "";
                    const matches = searchable.includes(query) && (groupFilter === "" || groupCanonical === groupFilter);
                    item.classList.toggle("hidden-agenda-item", !matches);
                    if (matches) visibleInDay++;
                }});
                
                dayCard.style.display = visibleInDay > 0 ? "block" : "none";
                if (visibleInDay > 0) visibleDaysCount++;
            }});
            
            let noMatchEl = document.getElementById("agendaNoMatchMsg");
            if (visibleDaysCount === 0 && dayCards.length > 0) {{
                if (!noMatchEl) {{
                    noMatchEl = document.createElement("div");
                    noMatchEl.id = "agendaNoMatchMsg";
                    noMatchEl.className = "empty-state";
                    const ui = (translations.ui && translations.ui[currentLang]) || {{}};
                    noMatchEl.innerText = ui.no_matching_events || "No matching reservations found";
                    document.getElementById("agendaList").appendChild(noMatchEl);
                }}
            }} else if (noMatchEl) {{
                noMatchEl.remove();
            }}
        }}

        // Language Switcher Handler
        function switchLanguage(lang, updateUrl = true) {{
            currentLang = lang;
            localStorage.setItem("ses_calendar_lang", lang);
            document.documentElement.lang = lang;
            
            document.getElementById("langBtnEn").classList.toggle("active", lang === "en");
            document.getElementById("langBtnKo").classList.toggle("active", lang === "ko");
            
            const ui = (translations.ui && translations.ui[lang]) || {{}};
            if (ui.title) document.title = ui.title;
            if (ui.heading) document.getElementById("pageHeading").innerText = ui.heading;
            if (ui.subtitle) document.getElementById("pageSubtitle").innerText = ui.subtitle;
            if (ui.search_placeholder) document.getElementById("search").placeholder = ui.search_placeholder;
            if (ui.day_header) document.getElementById("dayColHeader").innerText = ui.day_header;
            if (ui.view_agenda) document.getElementById("labelViewAgenda").innerText = ui.view_agenda;
            if (ui.view_grid) document.getElementById("labelViewGrid").innerText = ui.view_grid;
            if (ui.filter_by_room) document.getElementById("filterRoomLabel").innerText = ui.filter_by_room;
            
            // Localize Room filter chips in Grid View
            document.querySelectorAll(".room-filter-chip").forEach(chip => {{
                const r = chip.dataset.room;
                if (r === "all") {{
                    chip.innerText = ui.all_rooms || "All Facilities";
                }} else {{
                    const roomData = (translations.facilities && translations.facilities[r]) || {{}};
                    chip.innerText = lang === 'ko' ? (roomData.ko || r) : (roomData.en || r);
                }}
            }});
            
            // Localize Table Headers
            FACILITIES.forEach(room => {{
                const roomData = (translations.facilities && translations.facilities[room]) || {{}};
                const roomTh = document.getElementById("th_" + room.replace(/[^a-zA-Z0-9_]/g, "_"));
                if (roomTh) {{
                    roomTh.innerHTML = roomData[`bilingual_${{lang}}`] || room;
                }}
            }});
            
            // Localize Month Tabs
            calendarData.forEach(month => {{
                const tab = document.getElementById(`monthTab_${{month.key}}`);
                if (tab) tab.innerText = lang === "ko" ? (month.name_ko || month.name) : month.name;
            }});
            
            populateGroupFilter();
            renderCurrentViews();
            
            // Dynamic URL synchronization for / and /ko/ (or /responsive/ and /responsive/ko/)
            if (updateUrl && window.location.protocol.startsWith("http")) {{
                const isSubdir = /\/ko(\/index\.html|\/)?$/.test(window.location.pathname);
                if (lang === "ko" && !isSubdir) {{
                    let newPath = window.location.pathname.replace(/(index\.html)?$/, "");
                    if (!newPath.endsWith("/")) newPath += "/";
                    newPath += "ko/";
                    window.history.pushState({{ lang: "ko" }}, "", newPath + window.location.search);
                }} else if (lang === "en" && isSubdir) {{
                    let newPath = window.location.pathname.replace(/\/ko(\/index\.html|\/)?$/, "/");
                    window.history.pushState({{ lang: "en" }}, "", newPath + window.location.search);
                }}
            }}
        }}

        // Handle browser back/forward buttons
        window.addEventListener("popstate", (e) => {{
            const isSubdir = /\/ko(\/index\.html|\/)?$/.test(window.location.pathname);
            const targetLang = (e.state && e.state.lang) || (isSubdir ? "ko" : "en");
            if (targetLang !== currentLang) {{
                switchLanguage(targetLang, false);
            }}
        }});

        // Auto-Scroll to Today's date
        function scrollToToday(smooth = true) {{
            const todayObj = new Date();
            const todayY = todayObj.getFullYear();
            const todayM = todayObj.getMonth() + 1;
            const todayD = todayObj.getDate();
            const isTodayMonth = (activeMonthKey === `${{todayY}}-${{todayM}}`);
            
            // Scroll active tab into view in month tabs container
            const activeTab = document.getElementById(`monthTab_${{activeMonthKey}}`);
            if (activeTab) {{
                activeTab.scrollIntoView({{ inline: "center", block: "nearest", behavior: smooth ? "smooth" : "auto" }});
            }}
            
            if (!isTodayMonth) return;
            
            if (currentView === "agenda") {{
                const todayCard = document.querySelector(`.agenda-day-card.today`);
                if (todayCard) {{
                    todayCard.scrollIntoView({{ behavior: smooth ? "smooth" : "auto", block: "center" }});
                }} else {{
                    const cards = Array.from(document.querySelectorAll(".agenda-day-card"));
                    const upcoming = cards.find(c => parseInt(c.dataset.day, 10) >= todayD);
                    if (upcoming) {{
                        upcoming.scrollIntoView({{ behavior: smooth ? "smooth" : "auto", block: "center" }});
                    }}
                }}
            }} else {{
                const todayRow = document.querySelector(`tr.today`);
                if (todayRow) {{
                    todayRow.scrollIntoView({{ behavior: smooth ? "smooth" : "auto", block: "center" }});
                }}
            }}
        }}

        // Initialization
        populateGroupFilter();
        setViewMode(currentView);
        if (currentLang !== INITIAL_DEFAULT_LANG) {{
            switchLanguage(currentLang, false);
        }} else {{
            renderCurrentViews();
        }}

        // Auto-focus on today's date upon page load
        setTimeout(() => {{
            scrollToToday(false);
        }}, 120);
    </script>
</body>
</html>
"""

def generate_calendar_html():
    print("🔄 Loading bookings to generate bilingual calendar view...")
    try:
        rows = sheets_client.get_all_rows()
    except Exception as e:
        print(f"❌ Error loading sheet: {e}")
        return False
        
    events = overlap_detector.load_events_from_rows(rows)
    translations = load_translations()
    
    all_intervals = []
    for ev in events:
        try:
            all_intervals.extend(ev.get_intervals())
        except Exception as e:
            print(f"Warning: Failed to expand '{ev.name}' during calendar generation: {e}")
            
    database = {}
    for room, start_dt, end_dt, group, name in all_intervals:
        y, m, d = start_dt.year, start_dt.month, start_dt.day
        
        database.setdefault(y, {}).setdefault(m, {}).setdefault(d, {}).setdefault(room, [])
        
        time_str = f"{start_dt.strftime('%-I:%M %p')} - {end_dt.strftime('%-I:%M %p')}"
        time_ko = format_korean_time(start_dt, end_dt)
        
        database[y][m][d][room].append({
            "group": group,
            "group_ko": translate_group(group, translations),
            "event": name,
            "event_ko": translate_event(name, group, translations),
            "time": time_str,
            "time_ko": time_ko,
            "start_time_sort": start_dt.strftime('%H:%M')
        })
        
    for y in database:
        for m in database[y]:
            for d in database[y][m]:
                for room in database[y][m][d]:
                    database[y][m][d][room].sort(key=lambda b: b["start_time_sort"])
                    
    monthly_grids = []
    
    for year, month, month_name in MONTHS_LIST:
        num_days = calendar.monthrange(year, month)[1]
        days_data = []
        
        for d in range(1, num_days + 1):
            curr_date = date(year, month, d)
            weekday_name = curr_date.strftime("%a")
            weekday_ko = translations.get("weekdays", {}).get(weekday_name, weekday_name)
            is_sunday = curr_date.weekday() == 6
            is_saturday = curr_date.weekday() == 5
            
            day_bookings = {}
            for room in FACILITIES:
                day_bookings[room] = database.get(year, {}).get(month, {}).get(d, {}).get(room, [])
                
            days_data.append({
                "day": d,
                "weekday": weekday_name,
                "weekday_ko": weekday_ko,
                "is_sunday": is_sunday,
                "is_saturday": is_saturday,
                "bookings": day_bookings
            })
            
        month_name_ko = translations.get("months", {}).get(month_name, month_name)
        monthly_grids.append({
            "key": f"{year}-{month}",
            "name": month_name,
            "name_ko": month_name_ko,
            "days": days_data
        })
        
    # 1. Output production root index.html (English default)
    html_en = render_responsive_html(monthly_grids, translations, default_lang="en", is_ko_subdir=False)
    output_en = os.path.join(SCRIPT_DIR, "index.html")
    try:
        with open(output_en, "w", encoding="utf-8") as f:
            f.write(html_en)
        print("✨ Successfully generated English calendar view at index.html")
    except Exception as e:
        print(f"❌ Error writing index.html: {e}")
        return False
        
    # 2. Output production dedicated ko/index.html (Korean default)
    ko_dir = os.path.join(SCRIPT_DIR, "ko")
    os.makedirs(ko_dir, exist_ok=True)
    html_ko = render_responsive_html(monthly_grids, translations, default_lang="ko", is_ko_subdir=True)
    output_ko = os.path.join(ko_dir, "index.html")
    try:
        with open(output_ko, "w", encoding="utf-8") as f:
            f.write(html_ko)
        print("✨ Successfully generated Korean dedicated calendar view at ko/index.html")
    except Exception as e:
        print(f"❌ Error writing ko/index.html: {e}")
        return False

    # 3. Output responsive preview responsive/index.html (English default)
    responsive_dir = os.path.join(SCRIPT_DIR, "responsive")
    os.makedirs(responsive_dir, exist_ok=True)
    output_resp_en = os.path.join(responsive_dir, "index.html")
    try:
        with open(output_resp_en, "w", encoding="utf-8") as f:
            f.write(html_en)
        print("✨ Successfully generated responsive calendar at responsive/index.html")
    except Exception as e:
        print(f"❌ Error writing responsive/index.html: {e}")
        return False

    # 4. Output responsive preview responsive/ko/index.html (Korean default)
    responsive_ko_dir = os.path.join(responsive_dir, "ko")
    os.makedirs(responsive_ko_dir, exist_ok=True)
    output_resp_ko = os.path.join(responsive_ko_dir, "index.html")
    try:
        with open(output_resp_ko, "w", encoding="utf-8") as f:
            f.write(html_ko)
        print("✨ Successfully generated responsive Korean calendar at responsive/ko/index.html")
    except Exception as e:
        print(f"❌ Error writing responsive/ko/index.html: {e}")
        return False

    return True

# Backwards-compatible aliases
render_html_page = render_responsive_html

if __name__ == "__main__":
    generate_calendar_html()
