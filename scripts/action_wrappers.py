"""Action wrappers for task function execution.

These functions are called by auto-generated task_functions.py.
They delegate to the Robot instance's methods, which in turn
use the skills / navigation / action-executor pipeline.
"""

from typing import List, Tuple


def GoToObject(robot, target: str) -> bool:
    """Navigate the robot to an object."""
    return robot.goto(target)


def PickupObject(robot, target: str) -> bool:
    """Pick up a visible object."""
    return robot.pickup(target)


def PutObject(robot, receptacle: str) -> bool:
    """Put the held object into a receptacle."""
    return robot.put(receptacle)


def Explore(robot, target: str, positions: List[Tuple[float, float, float]]) -> int:
    """Explore to find a target object across multiple positions.

    Args:
        robot: Robot instance.
        target: Regex pattern for the target object name.
        positions: List of (x, y, z) positions to try.

    Returns:
        Number of steps taken.
    """
    return robot.explore(target, positions)


def CleanObject(robot, target: str) -> bool:
    """Clean an object (e.g. rinse at the sink)."""
    return robot.clean(target)


# Aliases for LLM variation tolerance
Clean = CleanObject
Wash = CleanObject
WashObject = CleanObject


def SwitchOn(robot, target: str) -> bool:
    """Switch on a toggleable object."""
    return robot.switch_on(target)


def SwitchOff(robot, target: str) -> bool:
    """Switch off a toggleable object."""
    return robot.switch_off(target)


def ToggleOn(robot, target: str) -> bool:
    """Toggle on an object (alias for SwitchOn)."""
    return robot.switch_on(target)


def ToggleOff(robot, target: str) -> bool:
    """Toggle off an object (alias for SwitchOff)."""
    return robot.switch_off(target)


def OpenObject(robot, target: str) -> bool:
    """Open a container or door."""
    return robot.open(target)


def CloseObject(robot, target: str) -> bool:
    """Close a container or door."""
    return robot.close(target)


def SliceObject(robot, target: str) -> bool:
    """Slice an object with a held knife."""
    return robot.slice(target)


def BreakObject(robot, target: str) -> bool:
    """Break an object."""
    return robot.execute_skill("BreakObject", target=target)


def ThrowObject(robot) -> bool:
    """Throw the held object."""
    return robot.throw()


def WashObject(robot, target: str) -> bool:
    """Wash an object (convenience: goto Sink + clean)."""
    return robot.wash(target)


def Wait(robot, seconds: float) -> None:
    """Wait for a specified duration."""
    robot.wait(seconds)
