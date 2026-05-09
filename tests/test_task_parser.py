import pytest

from task_parser import ParseError, ParsedTask, parse


def _task(id: str, content: str, description: str) -> dict:
    return {"id": id, "content": content, "description": description}


class TestParse:
    def test_valid_float_description(self):
        parsed, errors = parse([_task("1", "タスクA", "1.0")])
        assert len(parsed) == 1
        assert len(errors) == 0
        assert parsed[0].duration_hours == 1.0

    def test_empty_description_returns_error(self):
        parsed, errors = parse([_task("1", "タスクA", "")])
        assert len(parsed) == 0
        assert len(errors) == 1
        assert errors[0].id == "1"
        assert "空" in errors[0].reason

    def test_whitespace_only_description_returns_error(self):
        parsed, errors = parse([_task("1", "タスクA", "   ")])
        assert len(parsed) == 0
        assert len(errors) == 1
        assert "空" in errors[0].reason

    def test_non_numeric_description_returns_error(self):
        parsed, errors = parse([_task("1", "タスクA", "来週まで")])
        assert len(parsed) == 0
        assert len(errors) == 1
        assert "数値ではありません" in errors[0].reason
        assert "来週まで" in errors[0].reason

    def test_missing_description_field_returns_error(self):
        parsed, errors = parse([{"id": "1", "content": "タスクA"}])
        assert len(parsed) == 0
        assert len(errors) == 1

    def test_mixed_valid_and_invalid(self):
        tasks = [
            _task("1", "A", "1.0"),
            _task("2", "B", ""),
            _task("3", "C", "0.5"),
            _task("4", "D", "abc"),
        ]
        parsed, errors = parse(tasks)
        assert len(parsed) == 2
        assert len(errors) == 2
        assert parsed[0].id == "1"
        assert parsed[1].id == "3"

    @pytest.mark.parametrize(
        "duration_hours, expected_slots",
        [
            (0.25, 1),   # 15分 → 1スロット
            (0.5, 2),    # 30分 → 2スロット
            (1.0, 4),    # 60分 → 4スロット
            (1.5, 6),    # 90分 → 6スロット
            (0.1, 1),    # 6分 → 切り上げ1スロット（最小1）
            (0.4, 2),    # 24分 → 切り上げ2スロット
        ],
    )
    def test_slots_needed_calculation(self, duration_hours, expected_slots):
        parsed, _ = parse([_task("1", "A", str(duration_hours))])
        assert parsed[0].slots_needed == expected_slots
