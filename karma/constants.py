"""Global constants for the KARMA project.

All hardcoded magic numbers and action-related constants are centralized here.
"""

from typing import Final

# Navigation thresholds
GOAL_THRESH: Final[float] = 0.3
DIST_DELTA_THRESH: Final[float] = 0.2
STUCK_COUNT_LIMIT: Final[int] = 15
REACHABLE_THRESHOLD: Final[float] = 0.3
EXPLORE_EXIT_DISTANCE: Final[float] = 1.5

# AI2-THOR controller defaults
DEFAULT_GRID_SIZE: Final[float] = 0.25
DEFAULT_ROTATE_STEP_DEGREES: Final[int] = 20
DEFAULT_VISIBILITY_DISTANCE: Final[float] = 100.0
DEFAULT_QUALITY: Final[str] = "Low"
DEFAULT_WIDTH: Final[int] = 900
DEFAULT_HEIGHT: Final[int] = 900
DEFAULT_FOV: Final[int] = 90

# Memory limits
SHORT_TERM_MAX_SIZE: Final[int] = 100
POSITION_CHANGE_THRESHOLD: Final[float] = 0.3
SIMILARITY_THRESHOLD: Final[float] = 0.3

# Exploration positions (FloorPlan defaults)
DEFAULT_EXPLORATION_POSITIONS: Final[list] = [
    (1.25, 0.0, -1.75),
    (-1.0, 0.0, 0.0),
    (-0.25, 0.0, -1.5),
    (-1.0, 0.0, -1.5),
    (0.5, 0.0, 1.5),
    (1.5, 0.0, -0.25),
    (1.5, 0.0, 1.0),
    (-2.0, 0.0, 2.0),
]

# Agent configuration
DEFAULT_ROBOT_NAME: Final[str] = "robot1"
DEFAULT_ROBOT_SKILLS: Final[list] = [
    "GoToObject",
    "OpenObject",
    "CloseObject",
    "BreakObject",
    "SliceObject",
    "SwitchOn",
    "SwitchOff",
    "PickupObject",
    "PutObject",
    "DropHandObject",
    "ThrowObject",
    "PushObject",
    "PullObject",
]

# Image analysis
ANALYSIS_STATES: Final[list] = [
    "heated", "cooked", "sliced", "cleaned", "dirty",
    "filled", "used up", "off", "on", "opened", "closed", "none"
]

# Region division
REGION_DIVISIONS: Final[int] = 3

# Sleep intervals
ACTION_STEP_DELAY: Final[float] = 0.5
FAUCET_WASH_DURATION: Final[float] = 5.0

# Robot names pattern extraction
ROBOT_NAME_ID_PATTERN: Final[str] = r"robot(\d+)"
