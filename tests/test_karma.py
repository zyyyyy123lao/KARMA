"""Tests for karma.agents module."""

import pytest


class TestDistancePts:
    """Tests for the distance_pts utility function."""

    def test_same_point(self):
        from karma.agents.navigation import distance_pts
        assert distance_pts((0, 0, 0), (0, 0, 0)) == pytest.approx(0.0)

    def test_known_distance(self):
        from karma.agents.navigation import distance_pts
        # Distance from (0, 0, 0) to (3, 0, 4) should be 5
        assert distance_pts((0, 0, 0), (3, 0, 4)) == pytest.approx(5.0)

    def test_ignores_y_axis(self):
        from karma.agents.navigation import distance_pts
        # Y difference should not affect result
        assert distance_pts((0, 0, 0), (3, 10, 4)) == pytest.approx(5.0)


class TestComputeRotationAngle:
    """Tests for rotation angle computation."""

    def test_rotate_right(self):
        from karma.agents.navigation import compute_rotation_angle
        angle, direction = compute_rotation_angle(0, 0, 0, 1, 1)
        assert direction == "right"
        assert angle >= 0

    def test_rotate_left(self):
        from karma.agents.navigation import compute_rotation_angle
        angle, direction = compute_rotation_angle(90, 1, 0, 0, 0)
        assert direction == "left"
        assert angle >= 0


class TestSkillRegistry:
    """Tests for the skill registry."""

    def test_default_skills_registered(self):
        from karma.agents.skills import SkillRegistry
        registry = SkillRegistry()
        assert "GoToObject" in registry.list_skills()
        assert "PickupObject" in registry.list_skills()
        assert "PutObject" in registry.list_skills()
        assert "SwitchOn" in registry.list_skills()
        assert "SliceObject" in registry.list_skills()

    def test_get_skill_class(self):
        from karma.agents.skills import SkillRegistry
        registry = SkillRegistry()
        cls = registry.get("PickupObject")
        assert cls is not None
        assert cls.name == "PickupObject"

    def test_unknown_skill(self):
        from karma.agents.skills import SkillRegistry
        registry = SkillRegistry()
        assert registry.get("NonExistentSkill") is None


class TestMemoryModule:
    """Tests for the memory module."""

    def test_object_record_to_dict(self):
        from karma.memory.base import ObjectRecord
        record = ObjectRecord(
            object_type="Apple",
            object_id="Apple|123",
            position={"x": 1.0, "y": 0.0, "z": 2.0},
        )
        d = record.to_dict()
        assert d["objectType"] == "Apple"
        assert d["objectId"] == "Apple|123"
        assert d["position"]["x"] == 1.0

    def test_object_record_from_dict(self):
        from karma.memory.base import ObjectRecord
        data = {
            "objectType": "Tomato",
            "objectId": "Tomato|456",
            "position": {"x": -1.0, "y": 0.5, "z": 3.0},
        }
        record = ObjectRecord.from_dict(data)
        assert record.object_type == "Tomato"
        assert record.position["x"] == -1.0

    def test_short_term_memory_update(self):
        from karma.memory.short_term import ShortTermMemory, ObjectRecord

        class MockEvent:
            def __init__(self):
                self.metadata = {
                    "objects": [
                        {
                            "objectType": "Apple",
                            "objectId": "Apple|001",
                            "position": {"x": 1.0, "y": 0.0, "z": 1.0},
                            "distance": 1.5,
                            "axisAlignedBoundingBox": {},
                        }
                    ]
                }

        mem = ShortTermMemory(max_size=10)
        event = MockEvent()
        mem.update(event)

        assert len(mem.current_snapshot) == 1
        assert "Apple|001" in mem.current_snapshot

    def test_short_term_memory_clear(self):
        from karma.memory.short_term import ShortTermMemory

        class MockEvent:
            def __init__(self):
                self.metadata = {
                    "objects": [
                        {
                            "objectType": "Bowl",
                            "objectId": "Bowl|001",
                            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "distance": 2.0,
                            "axisAlignedBoundingBox": {},
                        }
                    ]
                }

        mem = ShortTermMemory()
        mem.update(MockEvent())
        assert len(mem.current_snapshot) > 0
        mem.clear()
        assert len(mem.current_snapshot) == 0

    def test_calculate_distance(self):
        from karma.memory.short_term import calculate_distance
        p1 = {"x": 0.0, "y": 0.0, "z": 0.0}
        p2 = {"x": 3.0, "y": 0.0, "z": 4.0}
        assert calculate_distance(p1, p2) == pytest.approx(5.0)


class TestLongTermMemory:
    """Tests for long-term memory."""

    def test_to_sentences(self):
        from karma.memory.long_term import LongTermMemory
        mem = LongTermMemory(
            regions={
                (0.0, 0.0, 0.0): [
                    {"objectType": "Sink", "position": {"x": 0, "y": 0, "z": 0}, "objectId": "Sink|1"},
                    {"objectType": "CounterTop", "position": {"x": 1, "y": 0, "z": 0}, "objectId": "CT|1"},
                ]
            }
        )
        sentences = mem.to_sentences()
        assert len(sentences) == 1
        assert "Sink" in sentences[0]
        assert "CounterTop" in sentences[0]


class TestPerceptionModule:
    """Tests for perception utilities."""

    def test_valid_states(self):
        from karma.perception.state_recognizer import is_valid_state
        assert is_valid_state("cleaned") is True
        assert is_valid_state("cooked") is True
        assert is_valid_state("invalid_state") is False

    def test_state_recognizer(self):
        from karma.perception.state_recognizer import StateRecognizer
        recognizer = StateRecognizer()
        result = recognizer.recognize("Apple: cleaned\nTomato: sliced")
        assert result.get("Apple") == "cleaned"
        assert result.get("Tomato") == "sliced"

    def test_extract_task(self):
        from karma.perception.similarity import extract_task_from_description
        desc = "Task 1: Wash the Apple."
        assert extract_task_from_description(desc) == "Wash the Apple"

    def test_extract_task_no_colon(self):
        from karma.perception.similarity import extract_task_from_description
        desc = "Just a plain task"
        assert extract_task_from_description(desc) is None


class TestConfigModule:
    """Tests for configuration management."""

    def test_config_singleton(self):
        from karma.config import Config
        Config._instance = None
        c1 = Config.get_instance()
        c2 = Config.get_instance()
        assert c1 is c2
        Config._instance = None

    def test_config_defaults(self):
        from karma.config import Config
        Config._instance = None
        config = Config()
        assert config.agent.name == "robot1"
        assert config.agent.scene == "FloorPlan1"
        assert config.agent.grid_size == 0.25
        assert config.memory.short_term_max_size == 100
        Config._instance = None

    def test_api_config_from_dict(self):
        from karma.config import APIConfig
        data = {
            "api_key": "test-key",
            "base_url": "https://test.com",
            "model_name": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 2048,
        }
        api = APIConfig.from_dict(data)
        assert api.api_key == "test-key"
        assert api.model_name == "gpt-4o"
        assert api.temperature == 0.5

    def test_agent_config_from_dict(self):
        from karma.config import AgentConfig
        data = {"agent": {"name": "tester", "scene": "FloorPlan5", "grid_size": 0.5}}
        cfg = AgentConfig.from_dict(data)
        assert cfg.name == "tester"
        assert cfg.scene == "FloorPlan5"
        assert cfg.grid_size == 0.5


class TestPathResolver:
    """Tests for path utilities."""

    def test_path_resolver_defaults(self):
        from karma.utils.path import PathResolver
        resolver = PathResolver("/test/path")
        assert resolver.base == resolver._base
        assert "memory" in str(resolver.memory)
        assert "logs" in str(resolver.logs)

    def test_agent_folder(self):
        from karma.utils.path import PathResolver
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = PathResolver(tmpdir)
            folder = resolver.agent_folder(agent_id=2)
            assert "agent_2" in str(folder)


class TestFileUtils:
    """Tests for file utility functions."""

    def test_read_write_json(self, tmp_path):
        from karma.utils.file_utils import read_json, write_json
        test_file = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        write_json(test_file, data)
        loaded = read_json(test_file)
        assert loaded == data

    def test_read_write_text(self, tmp_path):
        from karma.utils.file_utils import read_text, write_text
        test_file = tmp_path / "test.txt"
        write_text(test_file, "hello world")
        assert read_text(test_file) == "hello world"

    def test_append_to_file(self, tmp_path):
        from karma.utils.file_utils import append_to_file, read_text
        test_file = tmp_path / "append.txt"
        append_to_file(test_file, "line1")
        append_to_file(test_file, "line2")
        assert read_text(test_file) == "line1\nline2\n"

    def test_insert_into_file(self, tmp_path):
        from karma.utils.file_utils import insert_into_file, read_text
        test_file = tmp_path / "insert.txt"
        test_file.write_text("line1\nline3\n")
        insert_into_file(test_file, "INSERTED", line_number=2)
        content = read_text(test_file)
        assert "INSERTED" in content


class TestLogger:
    """Tests for logging utilities."""

    def test_experiment_logger_metric(self, tmp_path):
        from karma.utils.logger import ExperimentLogger
        with ExperimentLogger("test_exp", tmp_path) as logger:
            logger.log_metric("accuracy", 0.95)
            logger.log_metric("loss", 0.05)
        assert (tmp_path / "test_exp_metrics.jsonl").exists()
        assert (tmp_path / "test_exp_summary.json").exists()

    def test_experiment_logger_action(self, tmp_path):
        from karma.utils.logger import ExperimentLogger
        with ExperimentLogger("test_exp2", tmp_path) as logger:
            logger.log_action("navigate", params={"target": "Apple"}, success=True)
        assert (tmp_path / "test_exp2_actions.jsonl").exists()
