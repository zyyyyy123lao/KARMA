"""Action execution engine for KARMA.

Manages the action queue and executes AI2-THOR actions in a background thread.
Consolidates the exec_actions() function from multiple source files.
"""

import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2

from karma.utils.path import PathResolver

logger = logging.getLogger("karma.agents.action_executor")


class ActionExecutor:
    """Background thread action executor with queue management.

    Manages the action queue and executes AI2-THOR actions asynchronously,
    while optionally saving agent views and top-down camera frames.
    """

    def __init__(
        self,
        controller,
        agent_count: int = 1,
        save_frames: bool = True,
        short_term_memory_updater: Optional[Callable[[Any], None]] = None,
    ):
        self.controller = controller
        self.agent_count = agent_count
        self.save_frames = save_frames
        self.short_term_memory_updater = short_term_memory_updater
        self.paths = PathResolver()

        self._queue: List[Dict[str, Any]] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._img_counter = 0
        self._short_term_img_counter = 0
        self._last_event = None

    def start(self) -> None:
        """Start the background action execution thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Action executor already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Action executor started")

    def stop(self) -> None:
        """Stop the background thread and wait for completion."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Action executor stopped")

    def enqueue(self, action: Dict[str, Any]) -> None:
        """Add an action to the execution queue."""
        self._queue.append(action)

    def enqueue_nav(self, position: Dict[str, float], agent_id: int) -> None:
        """Convenience method to enqueue a navigation action."""
        self.enqueue({
            "action": "ObjectNavExpertAction",
            "position": position,
            "agent_id": agent_id,
        })

    def enqueue_rotate(self, degrees: float, agent_id: int, direction: str) -> None:
        """Convenience method to enqueue a rotation action."""
        action_name = "RotateRight" if direction == "right" else "RotateLeft"
        self.enqueue({"action": action_name, "degrees": degrees, "agent_id": agent_id})

    def clear_queue(self) -> None:
        """Clear all pending actions from the queue."""
        self._queue.clear()

    @property
    def queue_size(self) -> int:
        """Current number of actions in the queue."""
        return len(self._queue)

    def wait_for_queue(self, timeout: Optional[float] = None) -> bool:
        """Wait until the action queue is empty."""
        start = time.time()
        while self._queue:
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(0.1)
        return True

    def _setup_output_dirs(self) -> None:
        """Create output directories for agent frames and top-view."""
        # Clear existing
        for pattern in [str(self.paths.base / "*")]:
            import glob
            for d in glob.glob(pattern):
                if Path(d).is_dir() and d not in [".", ".."]:
                    try:
                        shutil.rmtree(d)
                    except OSError:
                        pass

        # Create per-agent folders
        for i in range(self.agent_count):
            self.paths.agent_folder(agent_id=i + 1)

        # Create top-view folder
        self.paths.top_view.mkdir(exist_ok=True)

    def _save_frames(self) -> None:
        """Save frames from all agent cameras and top-view camera."""
        events = self._last_event.events

        # Save each agent's first-person view
        for i, event in enumerate(events):
            # Display window
            try:
                cv2.imshow(f"agent{i}", event.cv2img)
            except Exception:
                pass

            # Save frame
            if self.save_frames:
                f_name = self.paths.agent_folder(i + 1) / f"img_{str(self._img_counter).zfill(5)}.png"
                cv2.imwrite(str(f_name), event.cv2img)

        # Save top-view
        if self.save_frames and self._last_event.events:
            try:
                tp_frames = self._last_event.events[0].third_party_camera_frames
                if tp_frames:
                    top_rgb = cv2.cvtColor(tp_frames[-1], cv2.COLOR_RGB2BGR)
                    cv2.imshow("Top View", top_rgb)
                    f_name = self.paths.top_view / f"img_{str(self._img_counter).zfill(5)}.png"
                    cv2.imwrite(str(f_name), top_rgb)
            except Exception:
                pass

        # Check for quit key
        if cv2.waitKey(25) & 0xFF == ord("q"):
            self._stop_event.set()

    def _save_short_term_memory_frame(self) -> None:
        """Capture and save a short-term memory observation frame."""
        try:
            self.controller.step(action="LookDown", degrees=20)
            frame = self.controller.last_event.frame
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.paths.short_term_memory.mkdir(exist_ok=True)
            filename = f"short_memory_{self._short_term_img_counter}.png"
            cv2.imwrite(str(self.paths.short_term_memory / filename), frame_bgr)
            self._short_term_img_counter += 1

            if self.short_term_memory_updater:
                self.short_term_memory_updater(self.controller.last_event)
        except Exception as e:
            logger.error("Failed to save short-term memory frame: %s", e)

    def _execute_action(self, act: Dict[str, Any]) -> None:
        """Execute a single action dict against the AI2-THOR controller."""
        action_name = act["action"]
        agent_id = act.get("agent_id", 0)

        if action_name == "ObjectNavExpertAction":
            self._last_event = self.controller.step(
                dict(action=action_name, position=act["position"], agentId=agent_id)
            )
            next_action = self._last_event.metadata.get("actionReturn")
            if next_action is not None:
                self._last_event = self.controller.step(
                    action=next_action, agentId=agent_id, forceAction=True
                )

        elif action_name == "PickupObject":
            self._last_event = self.controller.step(
                action="PickupObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "PutObject":
            self._last_event = self.controller.step(
                action="PutObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )
            if self.short_term_memory_updater:
                self._save_short_term_memory_frame()

        elif action_name == "ToggleObjectOn":
            self._last_event = self.controller.step(
                action="ToggleObjectOn",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "ToggleObjectOff":
            self._last_event = self.controller.step(
                action="ToggleObjectOff",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "SliceObject":
            self._last_event = self.controller.step(
                action="SliceObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "OpenObject":
            self._last_event = self.controller.step(
                action="OpenObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "CloseObject":
            self._last_event = self.controller.step(
                action="CloseObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "BreakObject":
            self._last_event = self.controller.step(
                action="BreakObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "CleanObject":
            self._last_event = self.controller.step(
                action="CleanObject",
                objectId=act["objectId"],
                agentId=agent_id,
                forceAction=True,
            )

        elif action_name == "ThrowObject":
            self._last_event = self.controller.step(
                action="ThrowObject",
                moveMagnitude=7,
                agentId=agent_id,
                forceAction=True,
            )
            time.sleep(1.0)

        elif action_name == "RotateLeft":
            self._last_event = self.controller.step(
                action="RotateLeft",
                degrees=act.get("degrees", 20),
                agentId=agent_id,
            )

        elif action_name == "RotateRight":
            self._last_event = self.controller.step(
                action="RotateRight",
                degrees=act.get("degrees", 20),
                agentId=agent_id,
            )

        elif action_name == "MoveAhead":
            self._last_event = self.controller.step(
                action="MoveAhead", agentId=agent_id
            )

        elif action_name == "MoveBack":
            self._last_event = self.controller.step(
                action="MoveBack", agentId=agent_id
            )

        elif action_name == "PlaceObjectAtPoint":
            self._last_event = self.controller.step(
                action="PlaceObjectAtPoint",
                objectId=act.get(
                    "objectId", "Apple|-00.47|+01.15|+00.48"
                ),
                position=act.get(
                    "position", {"x": -1.35, "y": 1.0, "z": -2.3}
                ),
            )
            if self._last_event.metadata.get("lastActionSuccess"):
                logger.info("PlaceObjectAtPoint succeeded")
            else:
                logger.error("PlaceObjectAtPoint failed")

        elif action_name == "Done":
            self._last_event = self.controller.step(action="Done")

        else:
            logger.warning("Unknown action type: %s", action_name)

    def _run(self) -> None:
        """Background thread main loop."""
        if self.save_frames:
            self._setup_output_dirs()

        while not self._stop_event.is_set():
            if self._queue:
                act = self._queue.pop(0)
                try:
                    self._execute_action(act)
                    self._save_frames()
                    self._img_counter += 1
                except Exception as e:
                    logger.error("Action execution error: %s", e)
            else:
                time.sleep(0.05)

        logger.info("Action executor thread finished")
