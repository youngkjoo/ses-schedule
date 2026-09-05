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
    
    # Try pattern replacement rules
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

def render_html_page(monthly_grids, translations, default_lang="en", is_ko_subdir=False):
    """Renders the HTML content for either English (default) or Korean (dedicated)."""
    ui = translations.get("ui", {}).get(default_lang, translations.get("ui", {}).get("en", {}))
    other_lang = "en" if default_lang == "ko" else "ko"
    
    # Static header cells based on initial language
    facility_headers_html = []
    for room in FACILITIES:
        room_data = translations.get("facilities", {}).get(room, {})
        cell_content = room_data.get(f"bilingual_{default_lang}", room)
        room_id = "th_" + re.sub(r"[^a-zA-Z0-9_]", "_", room)
        facility_headers_html.append(f'<th id="{room_id}">{cell_content}</th>')
    facility_headers_str = "".join(facility_headers_html)
    
    nav_to_other_target = "../" if is_ko_subdir and default_lang == "ko" else "ko/"

    return f"""<!DOCTYPE html>
<html lang="{default_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ui.get('title', 'TVKCC Facility Reservation Requests')}</title>
    
    <!-- Anti-Caching Directives to ensure real-time requests -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Premium Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-color: #080b11;
            --surface-color: #121824;
            --surface-lighter: #1b2436;
            --border-color: rgba(255, 255, 255, 0.08);
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
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 2.5rem 1.5rem;
            min-height: 100vh;
            line-height: 1.5;
            overflow-x: hidden;
        }}

        /* Header Container */
        header {{
            max-width: 1600px;
            margin: 0 auto 2rem auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
            background: rgba(18, 24, 36, 0.6);
            backdrop-filter: blur(12px);
            padding: 1.5rem 2.5rem;
            border-radius: 20px;
            border: 1px solid var(--border-color);
        }}

        .brand {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}

        h1 {{
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(90deg, #a5b4fc 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 0.9rem;
            font-weight: 500;
        }}

        /* Header Controls (Filter + Language Toggle) */
        .header-controls {{
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}

        /* Filter Container */
        .filter-container {{
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .search-box input, .group-select select {{
            padding: 0.75rem 1.25rem;
            border-radius: 12px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            font-family: inherit;
            font-size: 0.95rem;
            transition: all 0.25s ease;
        }}

        .group-select {{
            position: relative;
        }}

        .group-select select {{
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml;utf8,<svg fill='white' height='24' viewBox='0 0 24 24' width='24' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/><path d='M0 0h24v24H0z' fill='none'/></svg>");
            background-repeat: no-repeat;
            background-position: right 0.75rem center;
            background-size: 1.25rem;
            padding-right: 2.75rem;
            width: 220px;
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

        /* Language Switcher Segmented Control */
        .lang-switch-container {{
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            padding: 4px;
            border-radius: 100px;
            border: 1px solid var(--border-color);
            gap: 2px;
        }}

        .lang-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.5rem 1rem;
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            border-radius: 100px;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}

        .lang-btn:hover {{
            color: var(--text-color);
        }}

        .lang-btn.active {{
            background: var(--primary-gradient);
            color: #ffffff;
            box-shadow: 0 2px 10px rgba(99, 102, 241, 0.4);
        }}

        /* Month Switcher Tab Bar */
        .month-tabs-container {{
            max-width: 1600px;
            margin: 0 auto 1.5rem auto;
            overflow-x: auto;
            white-space: nowrap;
            padding-bottom: 0.5rem;
            scrollbar-width: thin;
        }}

        .month-tabs-container::-webkit-scrollbar {{
            height: 6px;
        }}

        .month-tabs-container::-webkit-scrollbar-thumb {{
            background-color: var(--border-color);
            border-radius: 3px;
        }}

        .month-tabs {{
            display: flex;
            gap: 0.75rem;
        }}

        .month-tab {{
            padding: 0.75rem 1.5rem;
            border-radius: 100px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .month-tab:hover {{
            color: var(--text-color);
            border-color: rgba(255, 255, 255, 0.15);
            background-color: var(--surface-lighter);
        }}

        .month-tab.active {{
            background: var(--primary-gradient);
            color: #ffffff;
            border-color: transparent;
            box-shadow: var(--accent-glow);
        }}

        /* Main Grid Wrapper */
        .calendar-wrapper {{
            max-width: 1600px;
            margin: 0 auto;
            background-color: var(--surface-color);
            border-radius: 20px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}

        .table-responsive {{
            width: 100%;
            overflow-x: auto;
            overflow-y: auto;
            max-height: calc(100vh - 280px);
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
            min-width: 1200px;
        }}

        th, td {{
            padding: 1.25rem 1rem;
            border-bottom: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            vertical-align: top;
        }}

        th:last-child, td:last-child {{
            border-right: none;
        }}

        /* Table Headers - STICKY TOP */
        thead th {{
            background-color: var(--surface-lighter);
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 0.03em;
            color: #a5b4fc;
            position: sticky;
            top: 0;
            z-index: 10;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            line-height: 1.35;
        }}

        .sub-lang {{
            font-size: 0.78rem;
            font-weight: 500;
            opacity: 0.7;
            letter-spacing: normal;
        }}

        /* Double-Sticky Top-Left Corner Header cell */
        thead th:first-child {{
            width: 90px;
            position: sticky;
            top: 0;
            left: 0;
            z-index: 12;
            border-right: 2px solid var(--border-color);
            text-align: center;
        }}

        /* Day Row Column - STICKY LEFT */
        td:first-child {{
            position: sticky;
            left: 0;
            background-color: var(--surface-lighter);
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            font-weight: 700;
            font-size: 1.05rem;
            z-index: 5;
            text-align: center;
            border-right: 2px solid var(--border-color);
            width: 90px;
        }}

        tbody tr:hover {{
            background-color: rgba(255, 255, 255, 0.02);
        }}

        /* Weekend Highlighting */
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

        /* Booking Cards */
        .booking-list {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .booking-card {{
            background: var(--surface-lighter);
            border-left: 4px solid var(--tag-community);
            border-radius: 8px;
            padding: 0.6rem 0.8rem;
            font-size: 0.85rem;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
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
            margin-bottom: 0.25rem;
            font-size: 0.8rem;
        }}

        .booking-event {{
            font-weight: 600;
            color: var(--text-color);
            margin-bottom: 0.1rem;
            line-height: 1.35;
        }}

        .booking-group {{
            color: var(--text-muted);
            font-size: 0.75rem;
            font-weight: 500;
        }}

        /* Search Highlight matching */
        .hidden-booking {{
            display: none !important;
        }}

        .empty-cell-text {{
            color: rgba(255, 255, 255, 0.05);
            font-size: 0.8rem;
            font-style: italic;
            user-select: none;
        }}
    </style>
</head>
<body>

    <!-- Glassmorphic Header -->
    <header>
        <div class="brand">
            <h1 id="pageHeading">{ui.get('heading', 'TVKCC Facility Reservation Requests')}</h1>
            <div class="subtitle" id="pageSubtitle">{ui.get('subtitle', 'Facility Schedule Planning Year: 8/2026 - 7/2027')}</div>
        </div>
        <div class="header-controls">
            <div class="filter-container">
                <div class="group-select">
                    <select id="groupFilter" onchange="handleSearch()">
                        <option value="">{ui.get('all_groups', '👥 All Groups')}</option>
                    </select>
                </div>
                <div class="search-box">
                    <input type="text" id="search" placeholder="{ui.get('search_placeholder', '🔍 Search by Event...')}" oninput="handleSearch()">
                </div>
            </div>
            <div class="lang-switch-container">
                <button class="lang-btn {'active' if default_lang == 'en' else ''}" id="langBtnEn" onclick="switchLanguage('en')">EN</button>
                <button class="lang-btn {'active' if default_lang == 'ko' else ''}" id="langBtnKo" onclick="switchLanguage('ko')">한국어</button>
            </div>
        </div>
    </header>

    <!-- Month Tab Bar Switcher -->
    <div class="month-tabs-container">
        <div class="month-tabs" id="monthTabs"></div>
    </div>

    <!-- Main Grid View -->
    <div class="calendar-wrapper">
        <div class="table-responsive">
            <table>
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
            if (paramLang === "ko" || paramLang === "en") {{
                return paramLang;
            }}
            if (IS_KO_SUBDIR) {{
                return "ko";
            }}
            const saved = localStorage.getItem("ses_calendar_lang");
            if (saved === "ko" || saved === "en") {{
                return saved;
            }}
            return INITIAL_DEFAULT_LANG;
        }}

        let currentLang = resolveInitialLanguage();
        let activeMonthKey = "{monthly_grids[0]['key']}";

        // Month Navigation Tabs
        const monthTabsEl = document.getElementById("monthTabs");
        calendarData.forEach((month, idx) => {{
            const btn = document.createElement("button");
            btn.className = `month-tab ${{month.key === activeMonthKey ? 'active' : ''}}`;
            btn.id = `monthTab_${{month.key}}`;
            btn.innerText = currentLang === "ko" ? (month.name_ko || month.name) : month.name;
            btn.onclick = () => selectMonth(month.key);
            monthTabsEl.appendChild(btn);
        }});

        function selectMonth(monthKey) {{
            activeMonthKey = monthKey;
            const tabs = document.querySelectorAll(".month-tab");
            calendarData.forEach((month, idx) => {{
                tabs[idx].className = `month-tab ${{month.key === activeMonthKey ? 'active' : ''}}`;
            }});
            renderGrid();
        }}

        // Dynamic Group Filter Population (Localized)
        function populateGroupFilter() {{
            const groupSelect = document.getElementById("groupFilter");
            const currentSelected = groupSelect.value;
            const allLabel = (translations.ui[currentLang] && translations.ui[currentLang].all_groups) || "👥 All Groups";
            
            groupSelect.innerHTML = `<option value="">${{allLabel}}</option>`;
            
            // Map canonical English groups to localized labels
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
            
            // Sort by current language display name
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
            
            if (currentSelected) {{
                groupSelect.value = currentSelected;
            }}
        }}

        function renderGrid() {{
            const gridEl = document.getElementById("calendarGrid");
            gridEl.innerHTML = "";
            
            const monthData = calendarData.find(m => m.key === activeMonthKey);
            if (!monthData) return;
            
            monthData.days.forEach(day => {{
                const row = document.createElement("tr");
                if (day.is_sunday) row.className = "sunday";
                else if (day.is_saturday) row.className = "saturday";
                
                const dayCell = document.createElement("td");
                const weekdayLabel = currentLang === 'ko' ? (day.weekday_ko || day.weekday) : day.weekday;
                dayCell.innerHTML = `<div>${{day.day}}</div><div style="font-size: 0.75rem; font-weight: 500; opacity: 0.6">${{weekdayLabel}}</div>`;
                row.appendChild(dayCell);
                
                FACILITIES.forEach(room => {{
                    const cell = document.createElement("td");
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
                            
                            // Searchable string includes BOTH English and Korean terms
                            const searchableText = `${{b.group.toLowerCase()}} ${{b.event.toLowerCase()}} ${{(b.group_ko || '').toLowerCase()}} ${{(b.event_ko || '').toLowerCase()}}`;
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
            
            handleSearch();
        }}

        function handleSearch() {{
            const query = document.getElementById("search").value.toLowerCase().trim();
            const groupFilter = document.getElementById("groupFilter").value;
            const cards = document.querySelectorAll(".booking-card");
            
            cards.forEach(card => {{
                const searchableText = card.dataset.searchable || "";
                const groupCanonical = card.dataset.groupCanonical || "";
                
                const matchesQuery = searchableText.includes(query);
                const matchesGroup = groupFilter === "" || groupCanonical === groupFilter;
                
                if (matchesQuery && matchesGroup) {{
                    card.classList.remove("hidden-booking");
                }} else {{
                    card.classList.add("hidden-booking");
                }}
            }});
            
            const cells = document.querySelectorAll("td");
            cells.forEach(cell => {{
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
        }}

        // Language Switcher Handler
        function switchLanguage(lang, updateUrl = true) {{
            currentLang = lang;
            localStorage.setItem("ses_calendar_lang", lang);
            
            // Update HTML lang attribute
            document.documentElement.lang = lang;
            
            // Update toggle buttons active state
            document.getElementById("langBtnEn").classList.toggle("active", lang === "en");
            document.getElementById("langBtnKo").classList.toggle("active", lang === "ko");
            
            // Localized UI Texts
            const ui = (translations.ui && translations.ui[lang]) || {{}};
            if (ui.title) document.title = ui.title;
            if (ui.heading) document.getElementById("pageHeading").innerText = ui.heading;
            if (ui.subtitle) document.getElementById("pageSubtitle").innerText = ui.subtitle;
            if (ui.search_placeholder) document.getElementById("search").placeholder = ui.search_placeholder;
            if (ui.day_header) document.getElementById("dayColHeader").innerText = ui.day_header;
            
            // Localize Facility Headers
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
                if (tab) {{
                    tab.innerText = lang === "ko" ? (month.name_ko || month.name) : month.name;
                }}
            }});
            
            // Re-populate and retain selected filter
            populateGroupFilter();
            
            // Re-render calendar grid in new language
            renderGrid();
            
            // Manage clean URLs
            if (updateUrl && window.location.protocol.startsWith("http")) {{
                const isSubdir = window.location.pathname.endsWith("/ko/") || window.location.pathname.endsWith("/ko");
                if (lang === "ko" && !isSubdir) {{
                    let newPath = window.location.pathname;
                    if (!newPath.endsWith("/")) newPath += "/";
                    newPath += "ko/";
                    window.history.pushState({{ lang: "ko" }}, "", newPath + window.location.search);
                }} else if (lang === "en" && isSubdir) {{
                    const newPath = window.location.pathname.replace(/\/ko\/?$/, "/");
                    window.history.pushState({{ lang: "en" }}, "", newPath + window.location.search);
                }}
            }}
        }}

        // Handle browser back/forward navigation
        window.addEventListener("popstate", (e) => {{
            const isSubdir = window.location.pathname.endsWith("/ko/") || window.location.pathname.endsWith("/ko");
            const targetLang = (e.state && e.state.lang) || (isSubdir ? "ko" : "en");
            if (targetLang !== currentLang) {{
                switchLanguage(targetLang, false);
            }}
        }});

        // Initial setup
        if (currentLang !== INITIAL_DEFAULT_LANG) {{
            switchLanguage(currentLang, false);
        }} else {{
            populateGroupFilter();
            renderGrid();
        }}
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
        
    # 1. Generate English root index.html
    html_en = render_html_page(monthly_grids, translations, default_lang="en", is_ko_subdir=False)
    output_en = os.path.join(SCRIPT_DIR, "index.html")
    try:
        with open(output_en, "w", encoding="utf-8") as f:
            f.write(html_en)
        print("✨ Successfully generated English calendar view at index.html")
    except Exception as e:
        print(f"❌ Error writing index.html: {e}")
        return False
        
    # 2. Generate Korean dedicated ko/index.html
    ko_dir = os.path.join(SCRIPT_DIR, "ko")
    os.makedirs(ko_dir, exist_ok=True)
    html_ko = render_html_page(monthly_grids, translations, default_lang="ko", is_ko_subdir=True)
    output_ko = os.path.join(ko_dir, "index.html")
    try:
        with open(output_ko, "w", encoding="utf-8") as f:
            f.write(html_ko)
        print("✨ Successfully generated Korean dedicated calendar view at ko/index.html")
    except Exception as e:
        print(f"❌ Error writing ko/index.html: {e}")
        return False

    return True

if __name__ == "__main__":
    generate_calendar_html()
