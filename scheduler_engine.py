import re
from datetime import datetime, date, timedelta

# Global configuration for the booking year
BOOKING_YEAR_START = date(2026, 8, 1)
BOOKING_YEAR_END = date(2027, 7, 31)

FACILITY_MAPPING = {
    "gym": "JP2",
    "jp2": "JP2",
    "church": "Church",
    "chapel": "Chapel",
    "cry room": "Cry Room",
    "room a": "Room A",
    "room b": "Room B",
    "parking lot": "Parking Lot",
    # Korean facility mappings
    "대성당": "Church",
    "성당": "Church",
    "소성당": "Chapel",
    "유아방": "Cry Room",
    "룸a": "Room A",
    "룸 a": "Room A",
    "룸b": "Room B",
    "룸 b": "Room B",
    "체육관": "JP2"
}

DAY_MAP = {
    "sun": 6, "sunday": 6,
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thr": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5
}

def clean_room_name(room_str):
    """Normalize facility names and apply custom mappings (e.g. Gym/체육관 -> JP2)."""
    room_clean = room_str.strip().lower()
    if room_clean in FACILITY_MAPPING:
        return FACILITY_MAPPING[room_clean]
    # Check if it starts with one of our known rooms
    for k, v in FACILITY_MAPPING.items():
        if room_clean.startswith(k):
            return v
    return room_str.strip()

def preprocess_korean_dates(dates_str):
    """
    Translates common Korean natural calendar phrases to standard English formats.
    Also normalizes ISO timestamp formats like 2026-10-03T07:00:00.000Z to 10/3/2026.
    Example: "8/9 부터 연말까지 매주일" -> "Every Sunday (8/9 - 12/31/2026)"
    """
    s = dates_str.strip()
    
    # 1. Defensive parsing: Check for ISO timestamp format (e.g. 2026-10-03T07:00:00.000Z)
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})T.*$", s)
    if iso_match:
        y, m, d = map(int, iso_match.groups())
        from datetime import datetime
        dt = datetime(y, m, d)
        day_str = dt.strftime("%a")
        return f"{m}/{d}/{y} ({day_str})"
        
    s = s.lower()
    
    # If the string contains no Korean characters, return as is
    if not any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in dates_str):
        return dates_str
        
    # Translate "연말" -> "12/31/2026"
    s = s.replace("연말", "12/31/2026")
    
    start_date = None
    end_date = None
    
    # Look for start date: "부터" or "시작"
    start_match = re.search(r"(\d+/\d+(?:/\d+)?)\s*부터", s)
    if start_match:
        start_date = start_match.group(1)
        
    # Look for end date: "Y 까지" or "Y까지"
    end_match = re.search(r"(\d+/\d+(?:/\d+)?)\s*까지", s)
    if end_match:
        end_date = end_match.group(1)
        
    # Translate ordinals (including multiple ordinals like 1,3,4번째 or 첫째, 셋째 주일)
    s_clean_ord = s.lower()
    s_clean_ord = s_clean_ord.replace("첫번째", "1").replace("첫째", "1").replace("첫", "1")
    s_clean_ord = s_clean_ord.replace("두번째", "2").replace("둘째", "2")
    s_clean_ord = s_clean_ord.replace("세번째", "3").replace("셋째", "3")
    s_clean_ord = s_clean_ord.replace("네번째", "4").replace("넷째", "4")
    
    # Remove dates to prevent conflict with year/month/day digits
    s_no_dates = re.sub(r"\d+/\d+", "", s_clean_ord)
    s_no_dates = re.sub(r"\d+년|\d+월|\d+일", "", s_no_dates)
    
    ordinal_list = []
    if "마지막" in s_no_dates:
        ordinal_list.append("last")
        
    digits = re.findall(r"\d+", s_no_dates)
    for d_str in digits:
        d = int(d_str)
        if d == 1 and "1st" not in ordinal_list:
            ordinal_list.append("1st")
        elif d == 2 and "2nd" not in ordinal_list:
            ordinal_list.append("2nd")
        elif d == 3 and "3rd" not in ordinal_list:
            ordinal_list.append("3rd")
        elif d == 4 and "4th" not in ordinal_list:
            ordinal_list.append("4th")
            
    # Sort ordinals numerically
    def sort_key(ord_str):
        if ord_str == "1st": return 1
        if ord_str == "2nd": return 2
        if ord_str == "3rd": return 3
        if ord_str == "4th": return 4
        return 5 # last
        
    ordinal_list.sort(key=sort_key)
    
    ordinal = ""
    if ordinal_list:
        if len(ordinal_list) == 1:
            ordinal = f"{ordinal_list[0]} "
        else:
            last = ordinal_list.pop()
            ordinal = ", ".join(ordinal_list) + f" & {last} "

    # Determine days of week (strip recurring prefixes first to avoid matching "월" inside "매월")
    s_clean_days = s.replace("요일", "").replace("매주", "").replace("매월", "").replace("매달", "").replace("매", "")
    days = []
    if "일" in s_clean_days or "주일" in s_clean_days:
        days.append("Sunday")
    if "토" in s_clean_days:
        days.append("Saturday")
    if "금" in s_clean_days:
        days.append("Friday")
    if "목" in s_clean_days:
        days.append("Thursday")
    if "수" in s_clean_days:
        days.append("Wednesday")
    if "화" in s_clean_days:
        days.append("Tuesday")
    if "월" in s_clean_days:
        days.append("Monday")
        
    is_recurring = "매" in s or "매주" in s or "매달" in s or "매월" in s
    
    if is_recurring and days:
        day_str = " & ".join(days)
        if start_date and end_date:
            return f"Every {ordinal}{day_str} ({start_date} - {end_date})"
        elif start_date:
            return f"Every {ordinal}{day_str} ({start_date} - 7/31/2027)"
        else:
            return f"Every {ordinal}{day_str}"
            
    return dates_str

def normalize_time_str(time_str):
    s = time_str.strip().lower()
    if not any(char in s for char in ["오전", "오후", "시", "분"]):
        return time_str
        
    parts = s.split("-")
    if len(parts) == 2:
        p1, p2 = parts[0].strip(), parts[1].strip()
        is_pm1 = "오후" in p1
        is_am1 = "오전" in p1
        is_pm2 = "오후" in p2
        is_am2 = "오전" in p2
        
        if is_pm1 and not is_pm2 and not is_am2:
            is_pm2 = True
        if is_am1 and not is_pm2 and not is_am2:
            if p2.startswith("12"):
                is_pm2 = True
            else:
                is_am2 = True
        if is_pm2 and not is_pm1 and not is_am1:
            is_pm1 = True
        if is_am2 and not is_pm1 and not is_am1:
            is_am1 = True
            
        def clean_num(p, is_pm, is_am):
            colon_match = re.search(r"(\d+)\s*시\s*(\d+)\s*분", p)
            if colon_match:
                h = colon_match.group(1)
                m = int(colon_match.group(2))
                m_str = f"{m:02d}"
                ampm = "PM" if is_pm else "AM"
                return f"{h}:{m_str}{ampm}"
                
            digits = re.findall(r"\d+", p)
            if digits:
                h = digits[0]
                m_str = "00"
                if "분" in p and len(digits) > 1:
                    m = int(digits[1])
                    m_str = f"{m:02d}"
                ampm = "PM" if is_pm else "AM"
                return f"{h}:{m_str}{ampm}"
            return ""
            
        t1 = clean_num(p1, is_pm1, is_am1)
        t2 = clean_num(p2, is_pm2, is_am2)
        if t1 and t2:
            return f"{t1} - {t2}"
            
    return time_str

def parse_time_block(time_str):
    """
    Parses a time range string like "7 AM - 1:00PM" or "9:30 AM - 11 AM" or "2 PM - 11:55 PM"
    Returns tuple of (start_hour, start_minute, end_hour, end_minute, is_overnight)
    """
    # Normalize spacing
    time_str = time_str.replace(" ", "").upper()
    # Match pattern like "7AM-1:00PM" or "9:30AM-11AM"
    match = re.match(r"(\d+(?::\d+)?)(AM|PM)?-(\d+(?::\d+)?)(AM|PM)?", time_str)
    if not match:
        raise ValueError(f"Could not parse time range: '{time_str}'")
        
    start_val, start_ampm, end_val, end_ampm = match.groups()
    
    def parse_part(val, ampm, default_ampm=None):
        if ":" in val:
            h, m = map(int, val.split(":"))
        else:
            h, m = int(val), 0
            
        ampm = ampm or default_ampm
        if ampm == "PM" and h < 12:
            h += 12
        elif ampm == "AM" and h == 12:
            h = 0
        return h, m

    # Heuristic: if start AM/PM is omitted, infer from end AM/PM if logical
    if not start_ampm and end_ampm:
        h_end, _ = parse_part(end_val, end_ampm)
        h_start_pm, _ = parse_part(start_val, "PM")
        h_start_am, _ = parse_part(start_val, "AM")
        if h_start_am < h_end:
            start_ampm = "AM"
        else:
            start_ampm = "PM"
    elif not start_ampm and not end_ampm:
        start_ampm = "AM"
        end_ampm = "AM"

    start_h, start_m = parse_part(start_val, start_ampm)
    end_h, end_m = parse_part(end_val, end_ampm, default_ampm=start_ampm)
    
    is_overnight = False
    if end_h < start_h or (end_h == start_h and end_m < start_m):
        is_overnight = True
        
    return start_h, start_m, end_h, end_m, is_overnight

def parse_time_string(time_str):
    """
    Parses a possibly multi-line or multi-time-range string.
    Returns a list of time blocks: [(start_h, start_m, end_h, end_m, is_overnight)]
    """
    blocks = []
    lines = re.split(r"[\n;]|\band\b", time_str)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            line_normalized = normalize_time_str(line)
            blocks.append(parse_time_block(line_normalized))
        except ValueError:
            pass
    return blocks

def parse_single_date(date_str, default_year=2026):
    """
    Parses a date string like "8/15/2026", "8/17/2025 (Sun)" or just "9/28"
    """
    date_str = re.sub(r"\([A-Za-z]+\)", "", date_str).strip()
    parts = list(map(int, re.findall(r"\d+", date_str)))
    if len(parts) == 3:
        m, d, y = parts
        if y < 100:
            y += 2000
        return date(y, m, d)
    elif len(parts) == 2:
        m, d = parts
        y = 2026 if m >= 8 else 2027
        return date(y, m, d)
    else:
        raise ValueError(f"Could not parse date: '{date_str}'")

def parse_exclusions(exclusion_str):
    """
    Parses exclusions string and returns a list of dictionaries:
    {"date": datetime.date, "room": str or None}
    """
    if not exclusion_str or exclusion_str.strip().lower() in ["", "none", "no", "yes"]:
        return []
        
    exclusions = []
    
    if ":" in exclusion_str:
        dates_part, room_part = exclusion_str.split(":", 1)
        room = clean_room_name(room_part)
        date_tokens = re.split(r"[,&]|\band\b", dates_part)
        for tok in date_tokens:
            tok = tok.strip()
            if not tok:
                continue
            try:
                d = parse_single_date(tok)
                exclusions.append({"date": d, "room": room})
            except ValueError:
                pass
    else:
        tokens = re.split(r"[,;\n]|\band\b", exclusion_str)
        for tok in tokens:
            tok = tok.strip()
            tok = re.sub(r"\(.*?\)|\[.*?\]", "", tok).strip()
            if not tok:
                continue
            try:
                d = parse_single_date(tok)
                exclusions.append({"date": d, "room": None})
            except ValueError:
                pass
                
    return exclusions

def parse_dates_field(dates_str):
    """
    Parses the Dates column string. Supports pre-processed Korean input.
    """
    dates_str_clean = dates_str.strip().lower()
    
    # 1. Date Range: e.g. "8/1/2026 (Fri) - 8/2/2026 (Sat)"
    if "-" in dates_str and not "every" in dates_str_clean:
        parts = dates_str.split("-")
        if len(parts) == 2:
            try:
                start_d = parse_single_date(parts[0].strip())
                end_d = parse_single_date(parts[1].strip())
                return ('range', start_d, end_d)
            except ValueError:
                pass
                
    # 2. Recurring pattern: e.g. "Every Sunday", "Every Sun (8/10/2026 - 5/3/2027)"
    if "every" in dates_str_clean:
        start_d = BOOKING_YEAR_START
        end_d = BOOKING_YEAR_END
        range_match = re.search(r"\((.*?)-(.*?)\)", dates_str)
        if range_match:
            try:
                start_d = parse_single_date(range_match.group(1).strip())
                end_d = parse_single_date(range_match.group(2).strip())
            except ValueError:
                pass
                
        pat_str = re.sub(r"\(.*?\)", "", dates_str_clean).strip()
        ordinals = re.findall(r"\b(\d+)(?:st|nd|rd|th)\b", pat_str)
        is_last = "last" in pat_str
        
        days = []
        for day_name, day_idx in DAY_MAP.items():
            if re.search(r"\b" + day_name + r"\b", pat_str):
                if day_idx not in days:
                    days.append(day_idx)
                    
        days.sort()
        if not days:
            if "weekend" in pat_str:
                days = [5, 6]
                
        return ('recurring', days, ordinals, is_last, start_d, end_d)
        
    # 3. List of specific dates
    tokens = re.split(r"[,;\n]|\band\b", dates_str)
    dates_list = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        try:
            dates_list.append(parse_single_date(tok))
        except ValueError:
            pass
            
    if dates_list:
        return ('single', dates_list)
        
    raise ValueError(f"Could not parse dates field: '{dates_str}'")

def is_date_matching_recurring(d, days_of_week, ordinals, is_last):
    if d.weekday() not in days_of_week:
        return False
        
    if not ordinals and not is_last:
        return True
        
    ord_idx = (d.day - 1) // 7 + 1
    if str(ord_idx) in ordinals:
        return True
        
    if is_last:
        if (d + timedelta(days=7)).month != d.month:
            return True
            
    return False

def expand_dates(dates_str, exclusions_str=""):
    dates_str = preprocess_korean_dates(dates_str)
    try:
        parsed_dates = parse_dates_field(dates_str)
    except ValueError:
        return {}
        
    exclusions = parse_exclusions(exclusions_str)
    
    excl_by_date = {}
    for excl in exclusions:
        d = excl["date"]
        r = excl["room"]
        excl_by_date.setdefault(d, []).append(r)
        
    expanded = {}
    
    def add_date_with_exclusions(d):
        if d in excl_by_date:
            if None in excl_by_date[d]:
                return
        expanded[d] = excl_by_date.get(d, [])

    if parsed_dates[0] == 'single':
        for d in parsed_dates[1]:
            add_date_with_exclusions(d)
            
    elif parsed_dates[0] == 'range':
        start_d, end_d = parsed_dates[1], parsed_dates[2]
        curr = start_d
        while curr <= end_d:
            add_date_with_exclusions(curr)
            curr += timedelta(days=1)
            
    elif parsed_dates[0] == 'recurring':
        _, days_of_week, ordinals, is_last, start_d, end_d = parsed_dates
        curr = start_d
        while curr <= end_d:
            if is_date_matching_recurring(curr, days_of_week, ordinals, is_last):
                add_date_with_exclusions(curr)
            curr += timedelta(days=1)
            
    return expanded

class Event:
    def __init__(self, group, name, dates_str, time_str, room_str, exclusions_str="", notes=""):
        self.group = group.strip()
        self.name = name.strip()
        
        # 1. Standardize and preprocess natural Korean and ISO dates directly in memory
        self.dates_str = preprocess_korean_dates(dates_str.strip())
        
        self.time_str = time_str.strip()
        self.exclusions_str = exclusions_str.strip()
        self.notes = notes.strip()
        
        # 2. Split room string by newline or comma
        raw_rooms = re.split(r"[\n,]", room_str.strip())
        self.rooms = [clean_room_name(r) for r in raw_rooms if r.strip()]
        
        # 3. Standardize and normalize room names in English
        self.room_str = "\n".join(self.rooms)
        
        # Parse time blocks
        self.time_blocks = parse_time_string(self.time_str)
        
        # Expand active dates and exclusions using our standardized dates_str
        self.date_exclusions = expand_dates(self.dates_str, self.exclusions_str)
        
    def get_intervals(self):
        intervals = []
        for d in self.date_exclusions.keys():
            excluded_rooms = self.date_exclusions[d]
            if None in excluded_rooms:
                continue
                
            for room in self.rooms:
                if room in excluded_rooms:
                    continue
                    
                for start_h, start_m, end_h, end_m, is_overnight in self.time_blocks:
                    start_dt = datetime(d.year, d.month, d.day, start_h, start_m)
                    
                    if is_overnight:
                        end_date = d + timedelta(days=1)
                        end_dt = datetime(end_date.year, end_date.month, end_date.day, end_h, end_m)
                    else:
                        end_dt = datetime(d.year, d.month, d.day, end_h, end_m)
                        
                    intervals.append((room, start_dt, end_dt, self.group, self.name))
                    
        return intervals
