from dataclasses import dataclass, field
from ortools.sat.python import cp_model
from task_parser import ParsedTask
from slot_generator import TimeSlot


@dataclass
class ScheduleResult:
    scheduled: list[tuple[ParsedTask, TimeSlot]] = field(default_factory=list)
    unscheduled: list[ParsedTask] = field(default_factory=list)


def schedule(tasks: list[ParsedTask], slots: list[TimeSlot]) -> ScheduleResult:
    model = cp_model.CpModel()
    n_tasks = len(tasks)
    n_slots = len(slots)

    if n_tasks == 0 or n_slots == 0:
        return ScheduleResult(unscheduled=list(tasks))

    starts = [model.NewIntVar(0, n_slots, f"start_{i}") for i in range(n_tasks)]
    assigned = [model.NewBoolVar(f"assigned_{i}") for i in range(n_tasks)]

    for i, task in enumerate(tasks):
        sn = task.slots_needed
        model.Add(starts[i] + sn <= n_slots).OnlyEnforceIf(assigned[i])
        model.Add(starts[i] + sn > n_slots).OnlyEnforceIf(assigned[i].Not())
        model.Add(starts[i] == n_slots).OnlyEnforceIf(assigned[i].Not())

    intervals = []
    for i, task in enumerate(tasks):
        interval = model.NewOptionalIntervalVar(
            starts[i],
            task.slots_needed,
            starts[i] + task.slots_needed,
            assigned[i],
            f"interval_{i}",
        )
        intervals.append(interval)
    model.AddNoOverlap(intervals)

    for i in range(n_tasks - 1):
        both = model.NewBoolVar(f"both_{i}")
        model.AddBoolAnd([assigned[i], assigned[i + 1]]).OnlyEnforceIf(both)
        model.AddBoolOr([assigned[i].Not(), assigned[i + 1].Not()]).OnlyEnforceIf(
            both.Not()
        )
        model.Add(starts[i] + tasks[i].slots_needed <= starts[i + 1]).OnlyEnforceIf(
            both
        )

    # ギャップ（ランチ等）をまたぐ配置を禁止する
    # スロットリスト上で時刻が連続していない境界を検出し、タスクがその境界をまたげないよう制約する
    gaps = [g for g in range(n_slots - 1) if slots[g + 1].start != slots[g].end]
    for g in gaps:
        for i, task in enumerate(tasks):
            ends_before = model.NewBoolVar(f"ends_before_{g}_{i}")
            starts_after = model.NewBoolVar(f"starts_after_{g}_{i}")
            model.Add(starts[i] + task.slots_needed <= g + 1).OnlyEnforceIf(ends_before)
            model.Add(starts[i] + task.slots_needed > g + 1).OnlyEnforceIf(
                ends_before.Not()
            )
            model.Add(starts[i] >= g + 1).OnlyEnforceIf(starts_after)
            model.Add(starts[i] < g + 1).OnlyEnforceIf(starts_after.Not())
            model.AddBoolOr([ends_before, starts_after]).OnlyEnforceIf(assigned[i])

    model.Maximize(
        sum(assigned[i] * (n_slots + 1) for i in range(n_tasks))
        - sum(starts[i] for i in range(n_tasks))
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    result = ScheduleResult()
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, task in enumerate(tasks):
            if solver.Value(assigned[i]):
                slot_idx = solver.Value(starts[i])
                result.scheduled.append((task, slots[slot_idx]))
            else:
                result.unscheduled.append(task)
    else:
        result.unscheduled = list(tasks)
    return result
