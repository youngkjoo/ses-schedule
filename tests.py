import unittest
from datetime import datetime, date
from scheduler_engine import (
    clean_room_name,
    parse_time_block,
    parse_single_date,
    parse_dates_field,
    parse_exclusions,
    expand_dates,
    preprocess_korean_dates,
    Event
)
import overlap_detector

class TestSchedulerEngine(unittest.TestCase):

    def test_room_name_normalization(self):
        self.assertEqual(clean_room_name("gym"), "JP2")
        self.assertEqual(clean_room_name("Gym"), "JP2")
        self.assertEqual(clean_room_name("JP2"), "JP2")
        self.assertEqual(clean_room_name("church"), "Church")
        self.assertEqual(clean_room_name("room a"), "Room A")
        self.assertEqual(clean_room_name("parking lot"), "Parking Lot")

    def test_korean_facility_mapping(self):
        self.assertEqual(clean_room_name("대성당"), "Church")
        self.assertEqual(clean_room_name("성당"), "Church")
        self.assertEqual(clean_room_name("소성당"), "Chapel")
        self.assertEqual(clean_room_name("유아방"), "Cry Room")
        self.assertEqual(clean_room_name("룸A"), "Room A")
        self.assertEqual(clean_room_name("룸 A"), "Room A")
        self.assertEqual(clean_room_name("룸 B"), "Room B")
        self.assertEqual(clean_room_name("체육관"), "JP2")

    def test_korean_date_preprocessing(self):
        # "8/9 부터 연말까지 매주일" -> "Every Sunday (8/9 - 12/31/2026)"
        preprocessed = preprocess_korean_dates("8/9 부터 연말까지 매주일")
        self.assertEqual(preprocessed, "Every Sunday (8/9 - 12/31/2026)")
        
        # Test Korean ordinals:
        self.assertEqual(preprocess_korean_dates("매달 3번째 주일"), "Every 3rd Sunday")
        self.assertEqual(preprocess_korean_dates("매월 첫째 토요일"), "Every 1st Saturday")
        self.assertEqual(preprocess_korean_dates("매달 1,3,4번째 주일"), "Every 1st, 3rd & 4th Sunday")
        self.assertEqual(preprocess_korean_dates("매달 첫째, 셋째 주일"), "Every 1st & 3rd Sunday")
        
        # Test ISO date preprocessing:
        self.assertEqual(preprocess_korean_dates("2026-10-03T07:00:00.000Z"), "10/3/2026 (Sat)")
        
        # Test full date expansion:
        # 8/9/2026 is Sunday, 12/27/2026 is Sunday. There should be exactly 21 Sundays between these two dates.
        dates_expanded = expand_dates("8/9 부터 연말까지 매주일")
        self.assertIn(date(2026, 8, 9), dates_expanded)
        self.assertIn(date(2026, 12, 27), dates_expanded)
        self.assertNotIn(date(2027, 1, 3), dates_expanded) # Outside the "until end of year" range

    def test_time_parsing(self):
        self.assertEqual(parse_time_block("7 AM - 1:00PM"), (7, 0, 13, 0, False))
        self.assertEqual(parse_time_block("9:30 AM - 11 AM"), (9, 30, 11, 0, False))
        self.assertEqual(parse_time_block("2 PM - 11:55 PM"), (14, 0, 23, 55, False))
        self.assertEqual(parse_time_block("9:00 PM - 7:00 AM"), (21, 0, 7, 0, True))
        
        # Test Korean time range normalization:
        from scheduler_engine import parse_time_string
        self.assertEqual(parse_time_string("오후 12 - 1시"), [(12, 0, 13, 0, False)])
        self.assertEqual(parse_time_string("오전 10 - 12시"), [(10, 0, 12, 0, False)])

    def test_single_date_parsing(self):
        self.assertEqual(parse_single_date("8/15/2026"), date(2026, 8, 15))
        self.assertEqual(parse_single_date("8/17/2025 (Sun)"), date(2025, 8, 17))
        self.assertEqual(parse_single_date("9/28"), date(2026, 9, 28))
        self.assertEqual(parse_single_date("1/25"), date(2027, 1, 25))

    def test_exclusion_parsing(self):
        excl1 = parse_exclusions("9/13 & 9/20: Chapel")
        self.assertEqual(len(excl1), 2)
        self.assertEqual(excl1[0], {"date": date(2026, 9, 13), "room": "Chapel"})
        self.assertEqual(excl1[1], {"date": date(2026, 9, 20), "room": "Chapel"})
        
        excl2 = parse_exclusions("9/10/2026, 9/11/2026, 12/25/2026")
        self.assertEqual(len(excl2), 3)
        self.assertEqual(excl2[0], {"date": date(2026, 9, 10), "room": None})
        self.assertEqual(excl2[2], {"date": date(2026, 12, 25), "room": None})

    def test_date_range_expansion(self):
        dates_expanded = expand_dates("8/1/2026 (Fri) - 8/3/2026 (Sun)")
        self.assertIn(date(2026, 8, 1), dates_expanded)
        self.assertIn(date(2026, 8, 2), dates_expanded)
        self.assertIn(date(2026, 8, 3), dates_expanded)
        self.assertEqual(len(dates_expanded), 3)

    def test_recurring_date_expansion(self):
        dates_expanded = expand_dates("Every Sun (8/1/2026 - 8/31/2026)")
        self.assertEqual(len(dates_expanded), 5)
        self.assertIn(date(2026, 8, 2), dates_expanded)
        self.assertIn(date(2026, 8, 30), dates_expanded)

        dates_2nd_sun = expand_dates("Every 2nd Sun (8/1/2026 - 8/31/2026)")
        self.assertEqual(list(dates_2nd_sun.keys()), [date(2026, 8, 9)])

    def test_room_specific_exclusion_handling(self):
        event = Event(
            "Liturgy", "Sunday Block", 
            "Every Sun (9/1/2026 - 9/30/2026)", 
            "7 AM - 1 PM", 
            "Church, Chapel, Room A", 
            "9/13: Chapel"
        )
        intervals = event.get_intervals()
        
        sept_13_bookings = [intv for intv in intervals if intv[1].date() == date(2026, 9, 13)]
        sept_13_rooms = [intv[0] for intv in sept_13_bookings]
        
        self.assertIn("Church", sept_13_rooms)
        self.assertIn("Room A", sept_13_rooms)
        self.assertNotIn("Chapel", sept_13_rooms)
        
        sept_20_bookings = [intv for intv in intervals if intv[1].date() == date(2026, 9, 20)]
        sept_20_rooms = [intv[0] for intv in sept_20_bookings]
        self.assertIn("Chapel", sept_20_rooms)

    def test_overlap_detector(self):
        ev1 = Event("Group 1", "Meeting 1", "Every Sun (8/1/2026 - 8/31/2026)", "1 PM - 4 PM", "Room A")
        
        ev2 = Event("Group 2", "Meeting 2", "8/9/2026", "2 PM - 3 PM", "Room A")
        conflicts = overlap_detector.find_overlaps(ev2, [ev1])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["room"], "Room A")
        self.assertEqual(conflicts[0]["date"], date(2026, 8, 9))
        
        ev3 = Event("Group 3", "Meeting 3", "8/9/2026", "4 PM - 5 PM", "Room A")
        conflicts_back_to_back = overlap_detector.find_overlaps(ev3, [ev1])
        self.assertEqual(len(conflicts_back_to_back), 0)

if __name__ == "__main__":
    unittest.main()
