import subprocess
import sys
import re

# Keywords mapping for English and Korean fields
FIELD_MAPS = {
    "group": ["group name", "그룹이름", "그룹 이름"],
    "event": ["meeting/event name", "이벤트/모임", "이벤트", "모임"],
    "dates": ["date", "날짜", "요일"],
    "time": ["time", "시간"],
    "room": ["facility requested", "facility", "모임장소", "장소", "모임 장소"],
    "exclusions": ["exclusions", "정기모임 - 모임이 없는 날짜", "모임이 없는 날짜", "제외"]
}

def parse_raw_text(text):
    lines = text.split("\n")
    data = {
        "group": "",
        "event": "",
        "dates": "",
        "time": "",
        "room": "",
        "exclusions": "",
        "notes": ""
    }
    
    current_key = None
    accumulated_value = []
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        # Check if line starts with any of our keywords (allowing optional leading list bullets like -, *, •)
        found_key = False
        for key, keywords in FIELD_MAPS.items():
            for kw in keywords:
                pattern = r"^[-*•\s]*" + re.escape(kw) + r"\s*[:：]"
                if re.match(pattern, line_strip, re.IGNORECASE):
                    # Save previous key accumulation
                    if current_key:
                        data[current_key] = "\n".join(accumulated_value).strip()
                        
                    current_key = key
                    # Extract everything after the colon
                    val = re.sub(pattern + r"\s*", "", line_strip, flags=re.IGNORECASE)
                    accumulated_value = [val] if val else []
                    found_key = True
                    break
            if found_key:
                break
                
        if not found_key:
            if current_key:
                accumulated_value.append(line_strip)
            else:
                # If there's content before any keyword, treat as general notes
                data["notes"] = (data["notes"] + "\n" + line_strip).strip()
                
    # Save the last key
    if current_key:
        data[current_key] = "\n".join(accumulated_value).strip()
        
    return data

def main():
    print("==========================================================")
    # Print instructions in both English and Korean
    print("📋 Paste the raw request below (English or Korean).")
    print("   When finished, press Ctrl+D (Mac/Linux) or Ctrl+Z then Enter (Windows) to run:")
    print("----------------------------------------------------------")
    print("그룹이름: ...  /  Group Name: ...")
    print("이벤트/모임: ...  /  Meeting/Event Name: ...")
    print("==========================================================")
    
    try:
        raw_input_text = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nAborted.")
        return
        
    parsed = parse_raw_text(raw_input_text)
    
    # Check if we parsed core fields
    if not parsed["group"] or not parsed["dates"] or not parsed["time"] or not parsed["room"]:
        print("\n❌ Error: Could not extract necessary fields (Group, Dates, Time, Room).")
        print("Please make sure the text has colons (:) separating the headers and values.")
        print("\nParsed Data so far:")
        for k, v in parsed.items():
            print(f"  {k.capitalize()}: {v}")
        return
        
    print("\n----------------------------------------------------------")
    print("🔍 Extracted Fields:")
    print(f"  👥 Group:      {parsed['group']}")
    print(f"  📅 Event Name: {parsed['event']}")
    print(f"  📆 Dates:      {parsed['dates']}")
    print(f"  ⏰ Time:       {parsed['time']}")
    print(f"  🚪 Facility:   {parsed['room']}")
    print(f"  🚫 Exclusions: {parsed['exclusions']}")
    print("----------------------------------------------------------")
    
    # Run main.py check
    cmd = [
        "python3", "main.py", "add",
        "--group", parsed["group"],
        "--event", parsed["event"],
        "--dates", parsed["dates"],
        "--time", parsed["time"],
        "--room", parsed["room"],
        "--exclusions", parsed["exclusions"],
        "--notes", parsed["notes"]
    ]
    
    print("🔄 Running overlap check and attempting to write to Google Sheet...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print the program stdout & stderr
    print(result.stdout)
    if result.stderr:
        print("Error details:", result.stderr)

if __name__ == "__main__":
    main()
