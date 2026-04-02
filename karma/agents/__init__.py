"""Agents module for KARMA.

Provides the Robot class, AI2-THOR controller wrapper, navigation system,
action execution engine, and skill registry.
"""

# Lazy imports via __getattr__ to avoid hard dependency on ai2thor at import time.
# Use 'from karma.agents.controller import AI2ThorController' or
# 'from karma.agents import AI2ThorController' — both work.
_SUBMODULES = {
    "AI2ThorController": "controller",
    "Robot": "robot",
    "NavigationController": "navigation",
    "ActionExecutor": "action_executor",
    "Skill": "skills",
    "SkillRegistry": "skills",
    "GoToObjectSkill": "skills",
    "PickupObjectSkill": "skills",
    "PutObjectSkill": "skills",
    "SwitchOnSkill": "skills",
    "SwitchOffSkill": "skills",
    "OpenObjectSkill": "skills",
    "CloseObjectSkill": "skills",
    "SliceObjectSkill": "skills",
    "CleanObjectSkill": "skills",
    "ThrowObjectSkill": "skills",
    "distance_pts": "navigation",
    "closest_reachable_node": "navigation",
    "find_object_in_scene": "navigation",
    "find_object_by_type": "navigation",
    "get_robot_pose": "navigation",
    "compute_rotation_angle": "navigation",
}
_loaded = {}


def __getattr__(name: str):
    if name not in _SUBMODULES:
        raise AttributeError(f"module 'karma.agents' has no attribute '{name}'")
    if name not in _loaded:
        import importlib
        mod_name = _SUBMODULES[name]
        mod = importlib.import_module(f"karma.agents.{mod_name}")
        _loaded[name] = getattr(mod, name)
    return _loaded[name]


def __dir__():
    return list(_SUBMODULES.keys())