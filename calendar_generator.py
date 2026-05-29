import json
import calendar
from datetime import date, datetime, timedelta
import sheets_client
import overlap_detector

FACILITIES = ["Church", "Chapel", "Cry Room", "Room A", "Room B", "JP2", "Parking Lot"]

FACILITY_BILINGUAL = {
    "Church": "Church<br>대성당",
    "Chapel": "Chapel<br>소성당",
    "Cry Room": "Cry Room<br>유아방",
    "Room A": "Room A<br>룸 A",
    "Room B": "Room B<br>룸 B",
    "JP2": "JP2<br>체육관",
    "Parking Lot": "Parking Lot<br>주차장"
}

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

def generate_calendar_html():
    print("🔄 Loading bookings to generate calendar view...")
    try:
        rows = sheets_client.get_all_rows()
    except Exception as e:
        print(f"❌ Error loading sheet: {e}")
        return False
        
    events = overlap_detector.load_events_from_rows(rows)
    
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
        database[y][m][d][room].append({
            "group": group,
            "event": name,
            "time": time_str,
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
            is_sunday = curr_date.weekday() == 6
            is_saturday = curr_date.weekday() == 5
            
            day_bookings = {}
            for room in FACILITIES:
                day_bookings[room] = database.get(year, {}).get(month, {}).get(d, {}).get(room, [])
                
            days_data.append({
                "day": d,
                "weekday": weekday_name,
                "is_sunday": is_sunday,
                "is_saturday": is_saturday,
                "bookings": day_bookings
            })
            
        monthly_grids.append({
            "key": f"{year}-{month}",
            "name": month_name,
            "days": days_data
        })
        
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TVKCC Facility Reservation Requests (NOT FINAL) (2026 - 2027)</title>
    
    <!-- Anti-Caching Directives to ensure real-time requests -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Premium Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
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
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 2.5rem 1.5rem;
            min-height: 100vh;
            line-height: 1.5;
            overflow: hidden;
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
            font-family: 'Outfit', sans-serif;
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
            width: 200px;
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
            font-family: 'Outfit', sans-serif;
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
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: #a5b4fc;
            position: sticky;
            top: 0;
            z-index: 10;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}

        /* Double-Sticky Top-Left Corner Header cell */
        thead th:first-child {{
            width: 90px;
            position: sticky;
            top: 0;
            left: 0;
            z-index: 12;
            border-right: 2px solid var(--border-color);
        }}

        /* Day Row Column - STICKY LEFT */
        td:first-child {{
            position: sticky;
            left: 0;
            background-color: var(--surface-lighter);
            font-family: 'Outfit', sans-serif;
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
            <h1>TVKCC Facility Reservation Requests (NOT FINAL)</h1>
            <div class="subtitle">Facility Schedule Planning Year: 8/2026 - 7/2027</div>
        </div>
        <div class="filter-container">
            <div class="group-select">
                <select id="groupFilter" onchange="handleSearch()">
                    <option value="">👥 All Groups</option>
                </select>
            </div>
            <div class="search-box">
                <input type="text" id="search" placeholder="🔍 Search by Event..." oninput="handleSearch()">
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
                        <th>Day</th>
                        {"".join(f"<th>{FACILITY_BILINGUAL.get(room, room)}</th>" for room in FACILITIES)}
                    </tr>
                </thead>
                <tbody id="calendarGrid"></tbody>
            </table>
        </div>
    </div>

    <script>
        // Database injected directly from Python backend expansion
        const calendarData = {json.dumps(monthly_grids)};
        
        let activeMonthKey = "{monthly_grids[0]['key']}";

        // Render Month Navigation Tab Buttons
        const monthTabsEl = document.getElementById("monthTabs");
        calendarData.forEach((month, idx) => {{
            const btn = document.createElement("button");
            btn.className = `month-tab ${{month.key === activeMonthKey ? 'active' : ''}}`;
            btn.innerText = month.name;
            btn.onclick = () => selectMonth(month.key);
            monthTabsEl.appendChild(btn);
        }});

        function selectMonth(monthKey) {{
            activeMonthKey = monthKey;
            
            // Toggle active tabs
            const tabs = document.querySelectorAll(".month-tab");
            calendarData.forEach((month, idx) => {{
                tabs[idx].className = `month-tab ${{month.key === activeMonthKey ? 'active' : ''}}`;
            }});
            
            renderGrid();
        }}

        // Dynamic Group Filter Population
        function populateGroupFilter() {{
            const groupSelect = document.getElementById("groupFilter");
            const currentSelected = groupSelect.value;
            
            groupSelect.innerHTML = '<option value="">👥 All Groups</option>';
            
            const groups = new Set();
            calendarData.forEach(month => {{
                month.days.forEach(day => {{
                    Object.values(day.bookings).forEach(roomBookings => {{
                        roomBookings.forEach(b => {{
                            if (b.group) groups.add(b.group.trim());
                        }});
                    }});
                }});
            }});
            
            const sortedGroups = Array.from(groups).sort();
            sortedGroups.forEach(grp => {{
                const opt = document.createElement("option");
                opt.value = grp.toLowerCase();
                opt.innerText = grp;
                groupSelect.appendChild(opt);
            }});
            
            if (currentSelected && Array.from(groups).some(g => g.toLowerCase() === currentSelected)) {{
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
                dayCell.innerHTML = `<div>${{day.day}}</div><div style="font-size: 0.75rem; font-weight: 500; opacity: 0.6">${{day.weekday}}</div>`;
                row.appendChild(dayCell);
                
                {json.dumps(FACILITIES)}.forEach(room => {{
                    const cell = document.createElement("td");
                    const bookings = day.bookings[room] || [];
                    
                    if (bookings.length === 0) {{
                        cell.innerHTML = '<span class="empty-cell-text">-</span>';
                    }} else {{
                        const listWrapper = document.createElement("div");
                        listWrapper.className = "booking-list";
                        
                        bookings.forEach(b => {{
                            const card = document.createElement("div");
                            const isLiturgy = b.group.toLowerCase().includes("liturgy");
                            card.className = `booking-card ${{isLiturgy ? 'liturgy' : ''}}`;
                            card.dataset.searchable = `${{b.group.toLowerCase()}} ${{b.event.toLowerCase()}}`;
                            
                            card.innerHTML = `
                                <div class="booking-time">${{b.time}}</div>
                                <div class="booking-event">${{b.event}}</div>
                                <div class="booking-group">${{b.group}}</div>
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
                const groupAttr = card.querySelector(".booking-group").innerText.toLowerCase().trim();
                
                const matchesQuery = searchableText.includes(query);
                const matchesGroup = groupFilter === "" || groupAttr === groupFilter;
                
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

        populateGroupFilter();
        renderGrid();
    </script>
</body>
</html>
"""
    
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "index.html")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✨ Successfully generated calendar view at index.html!")
        return True
    except Exception as e:
        print(f"❌ Error writing calendar HTML: {e}")
        return False

if __name__ == "__main__":
    generate_calendar_html()
