from datetime import date, datetime, time, timedelta

import pytest

from slot_generator import TimeSlot, generate_slots

DATE = date(2026, 5, 9)


def dt(h: int, m: int) -> datetime:
    return datetime(2026, 5, 9, h, m)


class TestGenerateSlotsWithoutLunch:
    def test_slot_count(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0))
        assert len(slots) == 36  # (18-9)*60/15

    def test_first_slot_starts_at_work_start(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0))
        assert slots[0].start == dt(9, 0)

    def test_last_slot_ends_at_work_end(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0))
        assert slots[-1].end == dt(18, 0)

    def test_each_slot_is_15_minutes(self):
        slots = generate_slots(DATE, time(9, 0), time(10, 0))
        for slot in slots:
            assert slot.end - slot.start == timedelta(minutes=15)

    def test_slots_are_consecutive(self):
        slots = generate_slots(DATE, time(9, 0), time(10, 0))
        for i in range(len(slots) - 1):
            assert slots[i].end == slots[i + 1].start

    def test_returns_empty_when_start_equals_end(self):
        slots = generate_slots(DATE, time(9, 0), time(9, 0))
        assert slots == []


class TestGenerateSlotsWithLunch:
    def test_slot_count_excludes_lunch(self):
        # 9:00-18:00 (36 slots) - 12:00-13:00 (4 slots) = 32
        slots = generate_slots(DATE, time(9, 0), time(18, 0), time(12, 0), time(13, 0))
        assert len(slots) == 32

    def test_no_slot_starts_during_lunch(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0), time(12, 0), time(13, 0))
        for slot in slots:
            assert not (dt(12, 0) <= slot.start < dt(13, 0))

    def test_slot_before_lunch_ends_at_lunch_start(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0), time(12, 0), time(13, 0))
        pre_lunch = [s for s in slots if s.start < dt(12, 0)]
        assert pre_lunch[-1].end == dt(12, 0)

    def test_first_slot_after_lunch_is_at_lunch_end(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0), time(12, 0), time(13, 0))
        post_lunch = [s for s in slots if s.start >= dt(13, 0)]
        assert post_lunch[0].start == dt(13, 0)

    def test_gap_exists_between_pre_and_post_lunch(self):
        slots = generate_slots(DATE, time(9, 0), time(18, 0), time(12, 0), time(13, 0))
        gap_idx = next(
            i for i in range(len(slots) - 1) if slots[i + 1].start != slots[i].end
        )
        assert slots[gap_idx].end == dt(12, 0)
        assert slots[gap_idx + 1].start == dt(13, 0)
