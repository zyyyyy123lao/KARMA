"""Navigation functions for KARMA agents.

Consolidates all navigation logic (GoToObject, ExploreObject, Explore) from
duplicate implementations across the original codebase.
"""

import math
import logging
import re
import time
from typing import Callable, List, Optional, Tuple, Dict, Any

import numpy as np
from scipy.spatial import distance

from karma.constants import (
    GOAL_THRESH,
    DIST_DELTA_THRESH,
    STUCK_COUNT_LIMIT,
    EXPLORE_EXIT_DISTANCE,
    ACTION_STEP_DELAY,
    FAUCET_WASH_DURATION,
)

logger = logging.getLogger("karma.agents.navigation")


def distance_pts(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Compute 2D Euclidean distance between two 3D points (ignoring Y axis)."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[2] - p2[2]) ** 2)


def closest_reachable_node(
    target: Tuple[float, float, float],
    reachable_positions: List[Tuple[float, float, float]],
    num_agents: int,
    closest_indices: List[int],
) -> List[Tuple[float, float, float]]:
    """Find the closest reachable positions for each robot.

    Args:
        target: The target (x, y, z) position.
        reachable_positions: List of all reachable positions.
        num_agents: Number of robots.
        closest_indices: Current closest position index per robot.

    Returns:
        List of (x, y, z) tuples, one per robot.
    """
    target_arr = np.array([target[0], target[2]])
    pos_arr = np.array([[p[0], p[2]] for p in reachable_positions])
    distances = distance.cdist([target_arr], pos_arr)[0]
    dist_indices = np.argsort(distances)

    result = []
    for i in range(num_agents):
        pos_index = dist_indices[(i * 5) + closest_indices[i]]
        result.append(reachable_positions[pos_index])
    return result


def get_robot_pose(event: Any, agent_id: int) -> Dict[str, Any]:
    """Extract robot pose from an AI2-THOR event.

    Returns:
        Dict with x, y, z, rotation, horizon keys.
    """
    metadata = event.events[agent_id].metadata
    return {
        "x": metadata["agent"]["position"]["x"],
        "y": metadata["agent"]["position"]["y"],
        "z": metadata["agent"]["position"]["z"],
        "rotation": metadata["agent"]["rotation"]["y"],
        "horizon": metadata["agent"]["cameraHorizon"],
    }


def compute_rotation_angle(
    robot_rotation: float,
    robot_x: float,
    robot_z: float,
    target_x: float,
    target_z: float,
) -> Tuple[float, str]:
    """Compute rotation needed to face a target point.

    Returns:
        Tuple of (angle in degrees, direction 'left' or 'right')
    """
    robot_target_vec = [target_x - robot_x, target_z - robot_z]
    y_axis = [0, 1]
    unit_y = y_axis / np.linalg.norm(y_axis)
    unit_vector = robot_target_vec / np.linalg.norm(robot_target_vec)

    angle = math.atan2(
        np.linalg.det([unit_vector, unit_y]),
        np.dot(unit_vector, unit_y),
    )
    angle = 360 * angle / (2 * math.pi)
    angle = (angle + 360) % 360
    rot_angle = angle - robot_rotation

    if rot_angle > 0:
        return abs(rot_angle), "right"
    return abs(rot_angle), "left"


def find_object_in_scene(
    event: Any,
    pattern: str,
) -> Optional[Tuple[str, Dict[str, float]]]:
    """Find an object matching a regex pattern in the current scene.

    Returns:
        Tuple of (object_id, axis_aligned_bounding_box_center) or None.
    """
    objs = event.metadata["objects"]
    for obj in objs:
        if re.match(pattern, obj["objectId"]):
            return obj["objectId"], obj["axisAlignedBoundingBox"]["center"]
    return None


def find_object_by_type(
    event: Any,
    pattern: str,
) -> Optional[Tuple[str, Dict[str, float]]]:
    """Find an object by matching its type (not full objectId).

    Uses regex matching against objectId. Returns first match.
    """
    objs = event.metadata["objects"]
    for obj in objs:
        if re.match(pattern, obj["objectId"]):
            return obj["objectId"], obj["axisAlignedBoundingBox"]["center"]
    return None


class NavigationController:
    """Stateful navigation controller that manages action queues."""

    def __init__(
        self,
        controller,
        reachable_positions: List[Tuple[float, float, float]],
        action_queue: List[Dict[str, Any]],
        goal_threshold: float = GOAL_THRESH,
        dist_delta_threshold: float = DIST_DELTA_THRESH,
        stuck_count_limit: int = STUCK_COUNT_LIMIT,
        explore_exit_distance: float = EXPLORE_EXIT_DISTANCE,
    ):
        self.controller = controller
        self.reachable_positions = reachable_positions
        self.action_queue = action_queue
        self.goal_threshold = goal_threshold
        self.dist_delta_threshold = dist_delta_threshold
        self.stuck_count_limit = stuck_count_limit
        self.explore_exit_distance = explore_exit_distance

    def goto_object(
        self,
        robot: Dict[str, Any],
        dest_pattern: str,
        agent_id: Optional[int] = None,
    ) -> bool:
        """Navigate to an object by regex pattern match.

        Uses ObjectNavExpertAction for efficient navigation.
        Aligns the robot's heading toward the object on arrival.

        Returns:
            True when destination is reached.
        """
        if agent_id is None:
            agent_id = int(robot["name"][-1]) - 1

        result = find_object_by_type(self.controller.last_event, dest_pattern)
        if result is None:
            logger.error("Object not found: %s", dest_pattern)
            return False

        dest_obj_id, dest_obj_center = result
        dest_pos = [dest_obj_center["x"], dest_obj_center["y"], dest_obj_center["z"]]

        logger.info("Navigating to %s (id=%s)", dest_pattern, dest_obj_id)

        dist_goals = [self.goal_threshold + 1.0]
        prev_dist_goals = [10.0]
        count_since_update = [0]
        closest_index = [0]

        while dist_goals[0] > self.goal_threshold:
            crp = closest_reachable_node(
                dest_pos,
                self.reachable_positions,
                1,
                closest_index,
            )

            pose = get_robot_pose(self.controller.last_event, agent_id)
            prev_dist_goals[0] = dist_goals[0]
            dist_goals[0] = distance_pts(
                [pose["x"], pose["y"], pose["z"]],
                crp[0],
            )

            dist_del = abs(dist_goals[0] - prev_dist_goals[0])
            if dist_del < self.dist_delta_threshold:
                count_since_update[0] += 1
            else:
                count_since_update[0] = 0

            if count_since_update[0] < self.stuck_count_limit:
                self.action_queue.append({
                    "action": "ObjectNavExpertAction",
                    "position": {"x": crp[0][0], "y": crp[0][1], "z": crp[0][2]},
                    "agent_id": agent_id,
                })
            else:
                closest_index[0] += 1
                count_since_update[0] = 0
                crp = closest_reachable_node(
                    dest_pos, self.reachable_positions, 1, closest_index
                )

            time.sleep(ACTION_STEP_DELAY)

        # Align toward object
        pose = get_robot_pose(self.controller.last_event, agent_id)
        angle, direction = compute_rotation_angle(
            pose["rotation"],
            pose["x"],
            pose["z"],
            dest_pos[0],
            dest_pos[2],
        )
        if direction == "right":
            self.action_queue.append({
                "action": "RotateRight",
                "degrees": angle,
                "agent_id": agent_id,
            })
        else:
            self.action_queue.append({
                "action": "RotateLeft",
                "degrees": angle,
                "agent_id": agent_id,
            })

        logger.info("Reached: %s", dest_pattern)
        return True

    def goto_object_with_memory(
        self,
        robot: Dict[str, Any],
        dest_pattern: str,
        memory_json: Dict[str, Any],
        agent_id: Optional[int] = None,
    ) -> bool:
        """Navigate to an object using position data from memory JSON.

        Args:
            robot: Robot dict with 'name' key.
            dest_pattern: Regex pattern to match objectId.
            memory_json: Dict loaded from memory3.json.
            agent_id: Override agent ID (defaults to robot name).

        Returns:
            True when destination is reached.
        """
        if agent_id is None:
            agent_id = int(robot["name"][-1]) - 1

        objs = {item["objectId"]: item for item in memory_json}

        dest_obj_id, dest_obj_center = None, None
        for obj_id, obj_data in objs.items():
            if re.match(dest_pattern, obj_id):
                dest_obj_id = obj_id
                dest_obj_center = obj_data["position"]
                break

        if dest_obj_center is None:
            logger.error("Object not found in memory: %s", dest_pattern)
            return False

        dest_pos = [dest_obj_center["x"], dest_obj_center["y"], dest_obj_center["z"]]
        logger.info("Navigating to %s from memory", dest_pattern)

        dist_goals = [self.goal_threshold + 1.0]
        prev_dist_goals = [10.0]
        count_since_update = [0]
        closest_index = [0]

        while dist_goals[0] > self.goal_threshold:
            crp = closest_reachable_node(
                dest_pos, self.reachable_positions, 1, closest_index
            )

            pose = get_robot_pose(self.controller.last_event, agent_id)
            prev_dist_goals[0] = dist_goals[0]
            dist_goals[0] = distance_pts([pose["x"], pose["y"], pose["z"]], crp[0])

            dist_del = abs(dist_goals[0] - prev_dist_goals[0])
            if dist_del < self.dist_delta_threshold:
                count_since_update[0] += 1
            else:
                count_since_update[0] = 0

            if count_since_update[0] < self.stuck_count_limit:
                self.action_queue.append({
                    "action": "ObjectNavExpertAction",
                    "position": {"x": crp[0][0], "y": crp[0][1], "z": crp[0][2]},
                    "agent_id": agent_id,
                })
            else:
                closest_index[0] += 1
                count_since_update[0] = 0

            time.sleep(ACTION_STEP_DELAY)

        # Align
        pose = get_robot_pose(self.controller.last_event, agent_id)
        angle, direction = compute_rotation_angle(
            pose["rotation"], pose["x"], pose["z"],
            dest_pos[0], dest_pos[2],
        )
        self.action_queue.append({
            "action": "RotateRight" if direction == "right" else "RotateLeft",
            "degrees": angle,
            "agent_id": agent_id,
        })

        logger.info("Reached: %s", dest_pattern)
        return True

    def explore_object(
        self,
        robot: Dict[str, Any],
        target_position: Tuple[float, float, float],
        target_pattern: str,
        agent_id: Optional[int] = None,
    ) -> bool:
        """Navigate toward a position until the target object becomes visible.

        Unlike goto_object, this explores the environment to find an object
        that may not be in the current field of view.

        Returns:
            True if the target object became visible.
        """
        if agent_id is None:
            agent_id = int(robot["name"][-1]) - 1

        result = find_object_by_type(self.controller.last_event, target_pattern)
        if result is not None:
            logger.info("Object already visible: %s", target_pattern)
            return True

        dest_obj_center = None
        objs = self.controller.last_event.metadata["objects"]
        for obj in objs:
            if re.match(target_pattern, obj["objectId"]):
                dest_obj_center = obj["axisAlignedBoundingBox"]["center"]
                break

        if dest_obj_center is None:
            logger.warning("Object not found in scene for exploration: %s", target_pattern)
            return False

        dest_obj_pos = [
            dest_obj_center["x"],
            dest_obj_center["y"],
            dest_obj_center["z"],
        ]

        nav_pos = [target_position[0], target_position[1], target_position[2]]
        goal_thresh = self.goal_threshold

        dist_goals = [goal_thresh + 1.0]
        prev_dist_goals = [10.0]
        count_since_update = [0]
        closest_index = [0]
        exit_flag = False

        while dist_goals[0] > goal_thresh:
            crp = closest_reachable_node(
                nav_pos, self.reachable_positions, 1, closest_index
            )

            pose = get_robot_pose(self.controller.last_event, agent_id)
            prev_dist_goals[0] = dist_goals[0]
            dist_goals[0] = distance_pts([pose["x"], pose["y"], pose["z"]], crp[0])
            dist_to_target = distance_pts([pose["x"], pose["y"], pose["z"]], dest_obj_pos)

            if dist_to_target < self.explore_exit_distance:
                exit_flag = True
                break

            dist_del = abs(dist_goals[0] - prev_dist_goals[0])
            if dist_del < self.dist_delta_threshold:
                count_since_update[0] += 1
            else:
                count_since_update[0] = 0

            if count_since_update[0] < self.stuck_count_limit:
                self.action_queue.append({
                    "action": "ObjectNavExpertAction",
                    "position": {"x": crp[0][0], "y": crp[0][1], "z": crp[0][2]},
                    "agent_id": agent_id,
                })
            else:
                closest_index[0] += 1
                count_since_update[0] = 0

            time.sleep(ACTION_STEP_DELAY)

        if exit_flag:
            logger.info("Found %s during exploration", target_pattern)
            # Align toward target
            pose = get_robot_pose(self.controller.last_event, agent_id)
            angle, direction = compute_rotation_angle(
                pose["rotation"], pose["x"], pose["z"],
                dest_obj_pos[0], dest_obj_pos[2],
            )
            self.action_queue.append({
                "action": "RotateRight" if direction == "right" else "RotateLeft",
                "degrees": angle,
                "agent_id": agent_id,
            })
            return True

        return False

    def explore(
        self,
        robot: Dict[str, Any],
        target_pattern: str,
        exploration_positions: List[Tuple[float, float, float]],
        agent_id: Optional[int] = None,
    ) -> int:
        """Explore multiple positions to find a target object.

        Args:
            robot: Robot dict.
            target_pattern: Regex pattern for target object.
            exploration_positions: Ordered list of (x, y, z) positions to explore.
            agent_id: Agent ID.

        Returns:
            Number of exploration positions visited.
        """
        if agent_id is None:
            agent_id = int(robot["name"][-1]) - 1

        visited = 0
        for position in exploration_positions:
            found = self.explore_object(robot, position, target_pattern, agent_id)
            visited += 1
            if found:
                self.goto_object(robot, target_pattern, agent_id)
                break

        logger.info("Explored %d positions to find %s", visited, target_pattern)
        return visited
