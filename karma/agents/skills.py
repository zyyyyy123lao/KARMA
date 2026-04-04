"""Skill system for KARMA agents.

Provides a skill registry and base class for agent capabilities.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("karma.agents.skills")


class Skill(ABC):
    """Abstract base class for agent skills."""

    name: str = ""
    description: str = ""

    def __init__(self, robot: "Robot"):
        self.robot = robot

    @abstractmethod
    def execute(self, **kwargs) -> bool:
        """Execute the skill. Returns True on success."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Skill: {self.name}>"


class GoToObjectSkill(Skill):
    """Navigate to a target object."""

    name = "GoToObject"
    description = "Navigate to an object by pattern match."

    def execute(self, target: str, **kwargs) -> bool:
        from karma.agents.navigation import find_object_by_type

        event = self.robot.controller.last_event
        result = find_object_by_type(event, target)
        if result is None:
            logger.error("GoToObject: target '%s' not found", target)
            return False
        dest_obj_id, dest_obj_center = result
        self.robot.navigate_to_position(
            [dest_obj_center["x"], dest_obj_center["y"], dest_obj_center["z"]]
        )
        return True


class PickupObjectSkill(Skill):
    """Pick up a visible object."""

    name = "PickupObject"
    description = "Pick up an object that is visible to the agent."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "PickupObject",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("PickupObject: target '%s' not found", target)
        return False


class PutObjectSkill(Skill):
    """Put a held object into a receptacle."""

    name = "PutObject"
    description = "Put the held object into a receptacle."

    def execute(self, receptacle: str = None, target: str = None, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if receptacle is not None and re.match(receptacle, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "PutObject",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        # Fallback: if no receptacle match, try to find and put the target object
        if target is not None:
            inventory = self.robot.controller.last_event.metadata.get(
                "inventoryObjects", []
            )
            for inv_obj in inventory:
                if re.match(target, inv_obj["objectId"]):
                    for obj in objs:
                        if re.match(receptacle or "Sink", obj["objectId"]):
                            self.robot.enqueue_action({
                                "action": "PutObject",
                                "objectId": obj["objectId"],
                                "agent_id": agent_id,
                            })
                            return True
        logger.error("PutObject: receptacle '%s' not found", receptacle)
        return False


class SwitchOnSkill(Skill):
    """Switch on a toggleable object."""

    name = "SwitchOn"
    description = "Turn on a switchable object (faucet, lamp, etc.)."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "ToggleObjectOn",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("SwitchOn: target '%s' not found", target)
        return False


class SwitchOffSkill(Skill):
    """Switch off a toggleable object."""

    name = "SwitchOff"
    description = "Turn off a switchable object."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "ToggleObjectOff",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("SwitchOff: target '%s' not found", target)
        return False


class OpenObjectSkill(Skill):
    """Open an openable object."""

    name = "OpenObject"
    description = "Open a container or door."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "OpenObject",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("OpenObject: target '%s' not found", target)
        return False


class CloseObjectSkill(Skill):
    """Close an openable object."""

    name = "CloseObject"
    description = "Close a container or door."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "CloseObject",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("CloseObject: target '%s' not found", target)
        return False


class SliceObjectSkill(Skill):
    """Slice an object with a held knife."""

    name = "SliceObject"
    description = "Slice an object (apple, tomato, bread, etc.)."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "SliceObject",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("SliceObject: target '%s' not found", target)
        return False


class CleanObjectSkill(Skill):
    """Clean an object."""

    name = "CleanObject"
    description = "Clean an object (e.g., wash in sink)."

    def execute(self, target: str, **kwargs) -> bool:
        agent_id = self.robot.agent_id
        # First check if the object is being held (in inventory)
        inventory = self.robot.controller.last_event.metadata.get(
            "inventoryObjects", []
        )
        for inv_obj in inventory:
            if re.match(target, inv_obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "CleanObject",
                    "objectId": inv_obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        # Fall back to objects in the scene
        objs = self.robot.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target, obj["objectId"]):
                self.robot.enqueue_action({
                    "action": "CleanObject",
                    "objectId": obj["objectId"],
                    "agent_id": agent_id,
                })
                return True
        logger.error("CleanObject: target '%s' not found in inventory or scene", target)
        return False


class ThrowObjectSkill(Skill):
    """Throw the currently held object."""

    name = "ThrowObject"
    description = "Throw the held object."

    def execute(self, target: str = "", **kwargs) -> bool:
        agent_id = self.robot.agent_id
        self.robot.enqueue_action({
            "action": "ThrowObject",
            "objectId": target,
            "agent_id": agent_id,
        })
        return True


class SkillRegistry:
    """Registry for agent skills with registration and execution support."""

    _DEFAULT_SKILLS: List[Type[Skill]] = [
        GoToObjectSkill,
        PickupObjectSkill,
        PutObjectSkill,
        SwitchOnSkill,
        SwitchOffSkill,
        OpenObjectSkill,
        CloseObjectSkill,
        SliceObjectSkill,
        CleanObjectSkill,
        ThrowObjectSkill,
    ]

    def __init__(self):
        self._skills: Dict[str, Type[Skill]] = {}
        for skill_cls in self._DEFAULT_SKILLS:
            self.register(skill_cls)

    def register(self, skill_class: Type[Skill]) -> None:
        """Register a skill class by its name."""
        instance = skill_cls(None) if (skill_cls := skill_class) and False else None
        name = skill_class.name or skill_class.__name__
        self._skills[name] = skill_class

    def get(self, name: str) -> Optional[Type[Skill]]:
        """Get a skill class by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        """Return names of all registered skills."""
        return list(self._skills.keys())

    def create_skill(self, name: str, robot: "Robot") -> Optional[Skill]:
        """Create a skill instance for a robot."""
        skill_cls = self.get(name)
        if skill_cls is None:
            return None
        return skill_cls(robot)
