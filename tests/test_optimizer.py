from datetime import datetime, timedelta

import pytest

from optimizer import ScheduleResult, schedule
from slot_generator import TimeSlot
from task_parser import ParsedTask


def _slot(h: int, m: int) -> TimeSlot:
    start = datetime(2026, 5, 9, h, m)
    return TimeSlot(start=start, end=start + timedelta(minutes=15))


def _task(id: str, slots_needed: int, duration_hours: float = 0.25) -> ParsedTask:
    return ParsedTask(id=id, content=f"task-{id}", duration_hours=duration_hours, slots_needed=slots_needed)


def _slots_range(start_h: int, start_m: int, count: int) -> list[TimeSlot]:
    result = []
    current = datetime(2026, 5, 9, start_h, start_m)
    for _ in range(count):
        result.append(TimeSlot(start=current, end=current + timedelta(minutes=15)))
        current += timedelta(minutes=15)
    return result


class TestScheduleEdgeCases:
    def test_empty_tasks_returns_empty_result(self):
        slots = _slots_range(9, 0, 4)
        result = schedule([], slots)
        assert result.scheduled == []
        assert result.unscheduled == []

    def test_empty_slots_returns_all_unscheduled(self):
        tasks = [_task("1", 1)]
        result = schedule(tasks, [])
        assert len(result.unscheduled) == 1
        assert result.scheduled == []

    def test_task_too_large_for_slots(self):
        slots = _slots_range(9, 0, 2)   # 2スロット
        tasks = [_task("1", 4)]         # 4スロット必要
        result = schedule(tasks, slots)
        assert len(result.unscheduled) == 1
        assert result.scheduled == []


class TestScheduleBasic:
    def test_single_task_fits(self):
        slots = _slots_range(9, 0, 4)
        tasks = [_task("1", 2)]
        result = schedule(tasks, slots)
        assert len(result.scheduled) == 1
        assert len(result.unscheduled) == 0

    def test_single_task_starts_at_first_slot(self):
        slots = _slots_range(9, 0, 4)
        tasks = [_task("1", 1)]
        result = schedule(tasks, slots)
        _, slot = result.scheduled[0]
        assert slot.start == datetime(2026, 5, 9, 9, 0)

    def test_multiple_tasks_maintain_order(self):
        slots = _slots_range(9, 0, 8)
        tasks = [_task("1", 2), _task("2", 2), _task("3", 2)]
        result = schedule(tasks, slots)
        assert len(result.scheduled) == 3
        ids = [t.id for t, _ in result.scheduled]
        assert ids == ["1", "2", "3"]

    def test_tasks_do_not_overlap(self):
        slots = _slots_range(9, 0, 8)
        tasks = [_task("1", 2), _task("2", 2)]
        result = schedule(tasks, slots)
        assert len(result.scheduled) == 2
        _, slot1 = result.scheduled[0]
        _, slot2 = result.scheduled[1]
        assert slot1.start < slot2.start

    def test_overflow_tasks_are_unscheduled(self):
        slots = _slots_range(9, 0, 4)  # 4スロット
        tasks = [_task("1", 2), _task("2", 2), _task("3", 2)]  # 計6スロット必要
        result = schedule(tasks, slots)
        assert len(result.scheduled) == 2
        assert len(result.unscheduled) == 1
        # スケジュールされた2タスクのスロットが重ならず昇順であること
        starts = [slot.start for _, slot in result.scheduled]
        assert starts[0] < starts[1]


class TestScheduleLunchGap:
    """ランチをまたぐ配置の禁止を検証する。"""

    def _slots_with_lunch_gap(self) -> list[TimeSlot]:
        # 11:30, 11:45 | gap (12:00-13:00) | 13:00, 13:15, 13:30, 13:45
        pre = [_slot(11, 30), _slot(11, 45)]
        post = [_slot(13, 0), _slot(13, 15), _slot(13, 30), _slot(13, 45)]
        return pre + post

    def test_task_does_not_straddle_lunch_gap(self):
        # 11:45スタートの2スロットタスクはギャップをまたぐため禁止され
        # 11:30 または 13:00 に割り当てられる必要がある
        slots = self._slots_with_lunch_gap()
        task = _task("1", 2, duration_hours=0.5)
        result = schedule([task], slots)

        assert len(result.scheduled) == 1
        _, slot = result.scheduled[0]
        assert slot.start != datetime(2026, 5, 9, 11, 45), (
            "11:45スタートの2スロットタスクはランチをまたぐため禁止されるべき"
        )

    def test_task_assigned_before_lunch_when_possible(self):
        # 2スロットが11:30から収まる場合、ランチ前に配置される
        slots = self._slots_with_lunch_gap()
        task = _task("1", 2, duration_hours=0.5)
        result = schedule([task], slots)

        _, slot = result.scheduled[0]
        assert slot.start == datetime(2026, 5, 9, 11, 30)

    def test_task_assigned_after_lunch_when_only_option(self):
        # 11:45のみが利用可能（ランチ前1スロット）なら、2スロットタスクはランチ後に配置
        slots = [_slot(11, 45)] + [_slot(13, 0), _slot(13, 15), _slot(13, 30)]
        task = _task("1", 2, duration_hours=0.5)
        result = schedule([task], slots)

        assert len(result.scheduled) == 1
        _, slot = result.scheduled[0]
        assert slot.start == datetime(2026, 5, 9, 13, 0)

    def test_1slot_task_can_start_just_before_lunch(self):
        # 1スロットタスクは11:45スタートでも問題ない（ギャップをまたがない）
        slots = self._slots_with_lunch_gap()
        tasks = [_task("1", 1), _task("2", 1)]
        result = schedule(tasks, slots)

        assert len(result.scheduled) == 2
        _, slot1 = result.scheduled[0]
        _, slot2 = result.scheduled[1]
        assert slot1.start == datetime(2026, 5, 9, 11, 30)
        assert slot2.start == datetime(2026, 5, 9, 11, 45)

    def test_tasks_before_and_after_lunch_are_both_scheduled(self):
        slots = self._slots_with_lunch_gap()
        tasks = [_task("1", 2), _task("2", 2)]  # 各30分
        result = schedule(tasks, slots)

        assert len(result.scheduled) == 2
        starts = sorted(slot.start for _, slot in result.scheduled)
        assert starts[0] == datetime(2026, 5, 9, 11, 30)
        assert starts[1] == datetime(2026, 5, 9, 13, 0)
