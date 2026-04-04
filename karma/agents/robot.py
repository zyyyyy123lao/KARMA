"""Robot class for KARMA agents.

Unified robot interface that combines controller, navigation, skills, and memory.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from karma.agents.action_executor import ActionExecutor
from karma.agents.navigation import NavigationController
from karma.agents.skills import SkillRegistry
from karma.constants import (
    DEFAULT_ROBOT_NAME,
    DEFAULT_ROBOT_SKILLS,
    ACTION_STEP_DELAY,
    FAUCET_WASH_DURATION,
)
from karma.utils.logger import ExperimentLogger

logger = logging.getLogger("karma.agents.robot")


class Robot:
    """Unified robot agent for KARMA.

    Combines AI2-THOR controller, navigation, skills, and memory management
    into a single interface for task execution.
    """

    def __init__(
        self,
        controller,
        name: str = DEFAULT_ROBOT_NAME,
        skills: Optional[List[str]] = None,
        agent_id: int = 0,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.agent_id = agent_id
        self.skills = skills or DEFAULT_ROBOT_SKILLS
        self.config = config or {}
        self.controller = controller

        # Action queue (shared between Robot and ActionExecutor)
        self.action_queue: List[Dict[str, Any]] = []

        # Initialize components
        self._action_executor = ActionExecutor(
            controller=controller,
            action_queue=self.action_queue,
            agent_count=1,
            save_frames=False,
        )
        self._action_executor.start()
        self._nav = NavigationController(
            controller=controller,
            reachable_positions=controller.reachable_positions,
            action_queue=self.action_queue,
        )
        self._skill_registry = SkillRegistry()

        # State
        self._state: Dict[str, Any] = {}
        self._held_object: Optional[str] = None
        self._experiment_logger: Optional[ExperimentLogger] = None

    # ─── Navigation ────────────────────────────────────────────────────────────

    def goto(self, target: str) -> bool:
        """Navigate to an object by regex pattern."""
        logger.info("Robot %s: goto %s", self.name, target)
        return self._nav.goto_object(self._robot_dict, target, self.agent_id)

    def explore(
        self,
        target: str,
        positions: Optional[List[Tuple[float, float, float]]] = None,
    ) -> int:
        """Explore to find a target object across multiple positions."""
        if positions is None:
            positions = self.config.get(
                "exploration_positions",
                [[1.25, 0, -1.75], [-1.0, 0, 0], [-0.25, 0, -1.5]],
            )
        return self._nav.explore(self._robot_dict, target, positions, self.agent_id)

    def navigate_to_position(self, position: Tuple[float, float, float]) -> None:
        """Navigate directly to an (x, y, z) position."""
        from karma.agents.navigation import closest_reachable_node, get_robot_pose

        goal_thresh = self.config.get("goal_threshold", 0.3)
        while True:
            crp = closest_reachable_node(
                position,
                self.controller.reachable_positions,
                1,
                [0],
            )
            self.action_queue.append({
                "action": "ObjectNavExpertAction",
                "position": {"x": crp[0][0], "y": crp[0][1], "z": crp[0][2]},
                "agent_id": self.agent_id,
            })
            pose = get_robot_pose(self.controller.last_event, self.agent_id)
            dist = ((pose["x"] - position[0]) ** 2 + (pose["z"] - position[2]) ** 2) ** 0.5
            if dist < goal_thresh:
                break
            time.sleep(ACTION_STEP_DELAY)

    # ─── Actions ───────────────────────────────────────────────────────────────

    def pickup(self, target: str) -> bool:
        """Pick up a visible object."""
        skill = self._skill_registry.create_skill("PickupObject", self)
        if skill:
            result = skill.execute(target=target)
            if result:
                self._held_object = target
            return result
        return False

    def put(self, receptacle: str) -> bool:
        """Put the held object into a receptacle."""
        skill = self._skill_registry.create_skill("PutObject", self)
        result = skill.execute(receptacle=receptacle)
        if result:
            self._held_object = None
        return result

    def put_explicit(self, target: str, receptacle: str) -> bool:
        """Put a named object into a named receptacle.

        Unlike put(), both the object and the receptacle are specified explicitly.
        """
        skill = self._skill_registry.create_skill("PutObject", self)
        return skill.execute(target=target, receptacle=receptacle)

    def switch_on(self, target: str) -> bool:
        """Switch on a toggleable object."""
        skill = self._skill_registry.create_skill("SwitchOn", self)
        return skill.execute(target=target)

    def switch_off(self, target: str) -> bool:
        """Switch off a toggleable object."""
        skill = self._skill_registry.create_skill("SwitchOff", self)
        return skill.execute(target=target)

    def open(self, target: str) -> bool:
        """Open a container or door."""
        skill = self._skill_registry.create_skill("OpenObject", self)
        return skill.execute(target=target)

    def close(self, target: str) -> bool:
        """Close a container or door."""
        skill = self._skill_registry.create_skill("CloseObject", self)
        return skill.execute(target=target)

    def slice(self, target: str) -> bool:
        """Slice an object with a held knife."""
        skill = self._skill_registry.create_skill("SliceObject", self)
        return skill.execute(target=target)

    def clean(self, target: str) -> bool:
        """Clean an object."""
        skill = self._skill_registry.create_skill("CleanObject", self)
        return skill.execute(target=target)

    def throw(self) -> bool:
        """Throw the held object."""
        skill = self._skill_registry.create_skill("ThrowObject", self)
        return skill.execute(target="")

    def wash(self, target: str) -> bool:
        """Wash an object at the sink (convenience method)."""
        self.goto("Sink")
        self.clean(target)
        return True

    def wait(self, seconds: float) -> None:
        """Wait for a specified duration."""
        time.sleep(seconds)

    # ─── Action Queue ───────────────────────────────────────────────────────────

    def enqueue_action(self, action: Dict[str, Any]) -> None:
        """Manually enqueue an action dict."""
        self.action_queue.append(action)

    def wait_for_actions(self, timeout: Optional[float] = None) -> bool:
        """Block until the action queue is empty."""
        start = time.time()
        while self.action_queue:
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(0.1)
        return True

    # ─── Skill System ───────────────────────────────────────────────────────────

    def execute_skill(self, skill_name: str, **kwargs) -> bool:
        """Execute a named skill with parameters."""
        skill = self._skill_registry.create_skill(skill_name, self)
        if skill is None:
            logger.error("Unknown skill: %s", skill_name)
            return False
        return skill.execute(**kwargs)

    @property
    def available_skills(self) -> List[str]:
        """List all available skill names."""
        return self._skill_registry.list_skills()

    # ─── Experiment Logging ──────────────────────────────────────────────────────

    def set_logger(self, logger: ExperimentLogger) -> None:
        """Attach an experiment logger for structured tracking."""
        self._experiment_logger = logger

    def log_action(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """Log an action through the experiment logger."""
        if self._experiment_logger:
            self._experiment_logger.log_action(action, params=params, success=success)

    # ─── State ─────────────────────────────────────────────────────────────────

    @property
    def held_object(self) -> Optional[str]:
        """The object currently held by the robot, or None."""
        return self._held_object

    @property
    def position(self) -> Tuple[float, float, float]:
        """Current robot position (x, y, z)."""
        from karma.agents.navigation import get_robot_pose
        pose = get_robot_pose(self.controller.last_event, self.agent_id)
        return (pose["x"], pose["y"], pose["z"])

    @property
    def state(self) -> Dict[str, Any]:
        """Additional robot state."""
        return self._state

    # ─── Internal ───────────────────────────────────────────────────────────────

    @property
    def _robot_dict(self) -> Dict[str, Any]:
        """Convert robot to dict format used by navigation functions."""
        return {"name": self.name}
