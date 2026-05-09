from dataclasses import dataclass
from datetime import datetime, date, time, timedelta

SLOT_MINUTES = 15


@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime


def generate_slots(
    target_date: date,
    work_start: time,
    work_end: time,
    lunch_start: time | None = None,
    lunch_end: time | None = None,
) -> list[TimeSlot]:
    slots = []
    current = datetime.combine(target_date, work_start)
    end = datetime.combine(target_date, work_end)

    lunch_dt_start = datetime.combine(target_date, lunch_start) if lunch_start else None
    lunch_dt_end = datetime.combine(target_date, lunch_end) if lunch_end else None

    while current + timedelta(minutes=SLOT_MINUTES) <= end:
        if lunch_dt_start and lunch_dt_end:
            if lunch_dt_start <= current < lunch_dt_end:
                current += timedelta(minutes=SLOT_MINUTES)
                continue
        slots.append(
            TimeSlot(start=current, end=current + timedelta(minutes=SLOT_MINUTES))
        )
        current += timedelta(minutes=SLOT_MINUTES)

    return slots
