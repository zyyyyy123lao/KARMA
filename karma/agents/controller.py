"""AI2-THOR Controller wrapper for KARMA.

Provides a clean interface to the AI2-THOR simulator with configuration support.
"""

import logging
import random
from typing import List, Optional, Tuple, Any

import numpy as np
from ai2thor.controller import Controller

from karma.config import AgentConfig
from karma.constants import (
    DEFAULT_GRID_SIZE,
    DEFAULT_ROTATE_STEP_DEGREES,
    DEFAULT_VISIBILITY_DISTANCE,
    DEFAULT_QUALITY,
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_FOV,
)

logger = logging.getLogger("karma.agents.controller")


class AI2ThorController:
    """Wrapper around AI2-THOR Controller with configurable parameters."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self._controller: Optional[Controller] = None
        self._reachable_positions: Optional[List[Tuple[float, float, float]]] = None
        self._last_event = None

    @property
    def controller(self) -> Controller:
        """Lazy initialization of the AI2-THOR controller."""
        if self._controller is None:
            self._controller = self._build_controller()
        return self._controller

    @property
    def last_event(self):
        """Get the last event from the controller."""
        return self._last_event

    def _build_controller(self) -> Controller:
        """Build the AI2-THOR controller with current configuration."""
        c = Controller(
            agentMode=self.config.agent_mode,
            visibilityDistance=self.config.visibility_distance,
            scene=self.config.scene,
            gridSize=self.config.grid_size,
            snapToGrid=self.config.snap_to_grid,
            rotateStepDegrees=self.config.rotate_step_degrees,
            quality=self.config.quality,
            renderDepthImage=self.config.render_depth_image,
            renderInstanceSegmentation=self.config.render_instance_segmentation,
            agentCount=self.config.agent_count,
            width=self.config.width,
            height=self.config.height,
            fieldOfView=self.config.field_of_view,
        )
        return c

    def initialize(self) -> Any:
        """Initialize the scene and return the first event."""
        self._last_event = self.controller.step(action="Done")

        # Add top-down third-party camera
        event = self.controller.step(action="GetMapViewCameraProperties")
        self.controller.step(action="AddThirdPartyCamera", **event.metadata["actionReturn"])

        # Get reachable positions for navigation
        self._reachable_positions = self._get_reachable_positions()

        # Randomize agent starting positions
        self._randomize_agent_positions()

        logger.info(
            "AI2-THOR controller initialized",
            extra={
                "scene": self.config.scene,
                "agent_count": self.config.agent_count,
                "reachable_positions": len(self._reachable_positions),
            },
        )
        return self._last_event

    def _get_reachable_positions(self) -> List[Tuple[float, float, float]]:
        """Query and cache all reachable positions in the scene."""
        event = self.controller.step(action="GetReachablePositions")
        positions = event.metadata["actionReturn"]
        self._reachable_positions = [
            (p["x"], p["y"], p["z"]) for p in positions
        ]
        return self._reachable_positions

    def _randomize_agent_positions(self) -> None:
        """Randomly teleport each agent to a reachable position."""
        for agent_id in range(self.config.agent_count):
            init_pos = random.choice(self._reachable_positions)
            self.controller.step(
                dict(action="Teleport", position=init_pos, agentId=agent_id)
            )

    def step(self, action: str, agentId: int = 0, forceAction: bool = False, **kwargs) -> Any:
        """Execute an action and return the event.

        Args:
            action: The AI2-THOR action name (str), or a dict containing
                    action and other parameters (e.g. {"action": "Teleport", ...}).
            agentId: The agent ID for multi-agent scenarios.
            forceAction: Force the action to succeed if possible.
            **kwargs: Additional action parameters.
        """
        # Support dict-based action (needed by _randomize_agent_positions for Teleport)
        if isinstance(action, dict):
            merged = dict(action)
            if forceAction:
                merged["forceAction"] = forceAction
            self._last_event = self.controller.step(merged)
        else:
            self._last_event = self.controller.step(
                action=action, agentId=agentId, forceAction=forceAction, **kwargs
            )
        return self._last_event

    @property
    def reachable_positions(self) -> List[Tuple[float, float, float]]:
        """Return cached reachable positions."""
        if self._reachable_positions is None:
            self._get_reachable_positions()
        return self._reachable_positions

    def reset(self, scene: Optional[str] = None) -> None:
        """Reset the controller with an optional new scene."""
        if scene:
            self.config.scene = scene
        self.controller.reset(self.config.scene)
        self._last_event = None
        self._reachable_positions = None
        self.initialize()

    def close(self) -> None:
        """Stop the controller."""
        if self._controller:
            self._controller.stop()
            self._controller = None
            self._reachable_positions = None
            self._last_event = None

    def __enter__(self) -> "AI2ThorController":
        self.initialize()
        return self

    def __exit__(self, *args) -> None:
        self.close()
