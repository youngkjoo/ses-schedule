"""
Responsive Calendar Generator Module
Provides backwards-compatible entry point that delegates to calendar_generator.
"""
from calendar_generator import (
    FACILITIES,
    MONTHS_LIST,
    load_translations,
    translate_group,
    translate_event,
    format_korean_time,
    render_responsive_html,
    generate_calendar_html
)

def generate_responsive_calendar_html():
    return generate_calendar_html()

if __name__ == "__main__":
    generate_responsive_calendar_html()
