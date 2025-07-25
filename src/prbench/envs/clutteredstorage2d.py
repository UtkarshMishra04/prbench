"""Cluttered environment where blocks must be stored on a shelf."""

from dataclasses import dataclass
from typing import Any

import gymnasium
import numpy as np
from geom2drobotenvs.concepts import is_inside
from geom2drobotenvs.envs.base_env import Geom2DRobotEnv, Geom2DRobotEnvSpec
from geom2drobotenvs.object_types import (
    CRVRobotType,
    Geom2DRobotEnvTypeFeatures,
    RectangleType,
)
from geom2drobotenvs.structs import ZOrder
from geom2drobotenvs.utils import (
    BLACK,
    PURPLE,
    CRVRobotActionSpace,
    SE2Pose,
    create_walls_from_world_boundaries,
    sample_se2_pose,
    state_has_collision,
)
from numpy.typing import NDArray
from relational_structs import Object, ObjectCentricState, ObjectCentricStateSpace, Type
from relational_structs.spaces import ObjectCentricBoxSpace
from relational_structs.utils import create_state_from_dict
from tomsgeoms2d.structs import Rectangle

from prbench.utils import get_geom2d_crv_robot_action_from_gui_input

# NOTE: unlike some other environments, there are multiple target blocks here.
TargetBlockType = Type("target_block", parent=RectangleType)
Geom2DRobotEnvTypeFeatures[TargetBlockType] = list(
    Geom2DRobotEnvTypeFeatures[RectangleType]
)
# There is only one target region (the shelf) and it is bookended by obstacles.
ShelfType = Type("shelf", parent=RectangleType)
Geom2DRobotEnvTypeFeatures[ShelfType] = list(Geom2DRobotEnvTypeFeatures[RectangleType])


@dataclass(frozen=True)
class ClutteredStorage2DEnvSpec(Geom2DRobotEnvSpec):
    """Scene specification for ClutteredStorage2DEnv()."""

    # World boundaries. Standard coordinate frame with (0, 0) in bottom left.
    world_min_x: float = 0.0
    world_max_x: float = 5.0
    world_min_y: float = 0.0
    world_max_y: float = 3.0

    # Action space parameters.
    min_dx: float = -5e-2
    max_dx: float = 5e-2
    min_dy: float = -5e-2
    max_dy: float = 5e-2
    min_dtheta: float = -np.pi / 16
    max_dtheta: float = np.pi / 16
    min_darm: float = -1e-1
    max_darm: float = 1e-1
    min_vac: float = 0.0
    max_vac: float = 1.0

    # Shelf hyperparameters:
    shelf_rgb: tuple[float, float, float] = PURPLE
    shelf_height: float = (world_max_y - world_min_y) / 8
    shelf_width_pad: float = shelf_height / 10
    shelf_y: float = world_max_y - shelf_height

    # Robot hyperparameters.
    robot_base_radius: float = 0.2
    # NOTE: extra long robot arm to make it easier to reach into shelf.
    robot_arm_length: float = 4 * robot_base_radius
    robot_gripper_height: float = 0.14
    robot_gripper_width: float = 0.02
    # NOTE: robot init y pose bounded above by shelf_y.
    robot_init_pose_bounds: tuple[SE2Pose, SE2Pose] = (
        SE2Pose(
            world_min_x + 4 * robot_base_radius,
            world_min_y + 4 * robot_base_radius,
            -np.pi,
        ),
        SE2Pose(
            world_max_x - 4 * robot_base_radius,
            shelf_y - 4 * robot_base_radius,
            np.pi,
        ),
    )

    # Target block hyperparameters.
    target_block_rgb: tuple[float, float, float] = (0.0, 0.3, 1.0)
    # N blocks are initialized in the shelf and N + 1 are initialized outside.
    target_block_in_shelf_rotation_bounds: tuple[float, float] = (
        -np.pi / 16,
        np.pi / 16,
    )
    target_block_out_of_shelf_pose_bounds: tuple[SE2Pose, SE2Pose] = (
        robot_init_pose_bounds
    )
    target_block_shape: tuple[float, float] = (
        2 * robot_gripper_height,
        2 * robot_gripper_width,
    )

    # For initial state sampling.
    max_init_sampling_attempts: int = 10_000

    # For rendering.
    render_dpi: int = 300
    render_fps: int = 20

    def get_shelf_width(self, num_init_shelf_blocks: int) -> float:
        """Calculate the shelf width as a function of number of blocks."""
        if num_init_shelf_blocks == 0:
            shelf_width = max(self.target_block_shape) + self.shelf_width_pad
        else:
            shelf_width = (
                max(self.target_block_shape) + self.shelf_width_pad
            ) * num_init_shelf_blocks
        assert shelf_width <= self.world_max_x - self.world_min_x
        # Make sure that vertical stacking is possible.
        assert shelf_width > (num_init_shelf_blocks + 1) * self.target_block_shape[1]
        return shelf_width

    def get_shelf_init_pose_bounds(
        self, num_init_shelf_blocks: int
    ) -> tuple[SE2Pose, SE2Pose]:
        """Calculate the init pose bounds for the shelf based on block
        number."""
        shelf_width = self.get_shelf_width(num_init_shelf_blocks)
        return (
            SE2Pose(self.world_min_x, self.shelf_y, 0),
            SE2Pose(self.world_max_x - shelf_width, self.shelf_y, 0),
        )

    def get_target_block_in_shelf_center_positions(
        self, num_init_shelf_blocks: int, shelf_pose: SE2Pose
    ) -> list[tuple[float, float]]:
        """Get the init center positions for the target blocks in the shelf."""
        shelf_width = self.get_shelf_width(num_init_shelf_blocks)
        assert np.isclose(shelf_pose.theta, 0.0)
        total_half_pad = (self.shelf_width_pad + self.target_block_shape[0]) / 2
        min_x = shelf_pose.x + total_half_pad
        max_x = shelf_pose.x + shelf_width - total_half_pad
        xs = np.linspace(min_x, max_x, num=num_init_shelf_blocks, endpoint=True)
        # NOTE: there is an implicit assumption here that the shelf is not too
        # deep for the robot to reach in and grab the objects.
        y = shelf_pose.y + 2 * self.target_block_shape[1]
        return [(x, y) for x in xs]


class ObjectCentricClutteredStorage2DEnv(Geom2DRobotEnv):
    """Cluttered environment where blocks must be stored on a shelf.

    This is an object-centric environment. The vectorized version with
    Box spaces is defined below.
    """

    def __init__(
        self,
        num_blocks: int = 3,
        spec: ClutteredStorage2DEnvSpec = ClutteredStorage2DEnvSpec(),
        **kwargs,
    ) -> None:
        super().__init__(spec, **kwargs)
        assert num_blocks % 2 == 1, "Number of blocks must be odd"
        self._num_init_shelf_blocks = num_blocks // 2
        self._num_init_outside_blocks = num_blocks - self._num_init_shelf_blocks
        self._spec: ClutteredStorage2DEnvSpec = spec  # for type checking
        self.metadata = {
            "render_modes": ["rgb_array"],
            "render_fps": self._spec.render_fps,
        }

    def _sample_initial_state(self) -> ObjectCentricState:
        initial_state_dict = self._create_constant_initial_state_dict()
        static_objects = set(initial_state_dict)
        # Sample robot pose.
        robot_pose = sample_se2_pose(self._spec.robot_init_pose_bounds, self.np_random)
        # Sample shelf pose.
        shelf_init_pose_bounds = self._spec.get_shelf_init_pose_bounds(
            self._num_init_shelf_blocks
        )
        shelf_pose = sample_se2_pose(shelf_init_pose_bounds, self.np_random)
        # Sample the target block rotations for those in the shelf.
        shelf_target_block_rotations = self.np_random.uniform(
            *self._spec.target_block_in_shelf_rotation_bounds,
            size=self._num_init_shelf_blocks,
        ).tolist()
        state = self._create_initial_state(
            initial_state_dict, robot_pose, shelf_pose, shelf_target_block_rotations
        )
        robot = state.get_objects(CRVRobotType)[0]
        assert not state_has_collision(state, {robot}, static_objects, {})
        # Sample target block poses for those outside the shelf.
        target_block_outside_poses: list[SE2Pose] = []
        for _ in range(self._num_init_outside_blocks):
            for _ in range(self._spec.max_init_sampling_attempts):
                pose = sample_se2_pose(
                    self._spec.target_block_out_of_shelf_pose_bounds, self.np_random
                )
                # Make sure in bounds.
                if not (
                    self._spec.world_min_x < pose.x < self._spec.world_max_x
                    and self._spec.world_min_y < pose.y < self._spec.world_max_y
                ):
                    continue
                # Check for collisions.
                state = self._create_initial_state(
                    initial_state_dict,
                    robot_pose,
                    shelf_pose,
                    shelf_target_block_rotations,
                    target_block_outside_poses=target_block_outside_poses + [pose],
                )
                obj_name_to_obj = {o.name: o for o in state}
                num_blocks = sum(b.startswith("block") for b in obj_name_to_obj)
                new_block = obj_name_to_obj[f"block{num_blocks-1}"]
                if not state_has_collision(state, {new_block}, set(state), {}):
                    break
            else:
                raise RuntimeError("Failed to sample obstruction pose.")
            # Update target blocks.
            target_block_outside_poses.append(pose)
        # The state should already be finalized.
        return state

    def _create_constant_initial_state_dict(self) -> dict[Object, dict[str, float]]:
        init_state_dict: dict[Object, dict[str, float]] = {}

        # Create room walls.
        assert isinstance(self.action_space, CRVRobotActionSpace)
        min_dx, min_dy = self.action_space.low[:2]
        max_dx, max_dy = self.action_space.high[:2]
        wall_state_dict = create_walls_from_world_boundaries(
            self._spec.world_min_x,
            self._spec.world_max_x,
            self._spec.world_min_y,
            self._spec.world_max_y,
            min_dx,
            max_dx,
            min_dy,
            max_dy,
        )
        init_state_dict.update(wall_state_dict)

        return init_state_dict

    def _create_initial_state(
        self,
        constant_initial_state_dict: dict[Object, dict[str, float]],
        robot_pose: SE2Pose,
        shelf_pose: SE2Pose,
        shelf_target_block_rotations: list[float],
        target_block_outside_poses: list[SE2Pose] | None = None,
    ) -> ObjectCentricState:

        # Shallow copy should be okay because the constant objects should not
        # ever change in this method.
        init_state_dict = constant_initial_state_dict.copy()

        # Create the robot.
        robot = Object("robot", CRVRobotType)
        init_state_dict[robot] = {
            "x": robot_pose.x,
            "y": robot_pose.y,
            "theta": robot_pose.theta,
            "base_radius": self._spec.robot_base_radius,
            "arm_joint": self._spec.robot_base_radius,  # arm is fully retracted
            "arm_length": self._spec.robot_arm_length,
            "vacuum": 0.0,  # vacuum is off
            "gripper_height": self._spec.robot_gripper_height,
            "gripper_width": self._spec.robot_gripper_width,
        }

        # Create the shelf.
        shelf = Object("shelf", ShelfType)
        shelf_width = self._spec.get_shelf_width(self._num_init_shelf_blocks)
        init_state_dict[shelf] = {
            "x": shelf_pose.x,
            "y": shelf_pose.y,
            "theta": shelf_pose.theta,
            "width": shelf_width,
            "height": self._spec.shelf_height,
            "static": True,
            "color_r": self._spec.shelf_rgb[0],
            "color_g": self._spec.shelf_rgb[1],
            "color_b": self._spec.shelf_rgb[2],
            "z_order": ZOrder.FLOOR.value,
        }

        # Create the left shelf bookend.
        shelf_left_bookend = Object("shelf_left_bookend", RectangleType)
        init_state_dict[shelf_left_bookend] = {
            "x": self._spec.world_min_x,
            "y": shelf_pose.y,
            "theta": shelf_pose.theta,
            "width": shelf_pose.x - self._spec.world_min_x,
            "height": self._spec.shelf_height,
            "static": True,
            "color_r": BLACK[0],
            "color_g": BLACK[1],
            "color_b": BLACK[2],
            "z_order": ZOrder.ALL.value,
        }

        # Create the right shelf bookend.
        shelf_right_bookend = Object("shelf_right_bookend", RectangleType)
        init_state_dict[shelf_right_bookend] = {
            "x": shelf_pose.x + shelf_width,
            "y": shelf_pose.y,
            "theta": shelf_pose.theta,
            "width": self._spec.world_max_x - (shelf_pose.x + shelf_width),
            "height": self._spec.shelf_height,
            "static": True,
            "color_r": BLACK[0],
            "color_g": BLACK[1],
            "color_b": BLACK[2],
            "z_order": ZOrder.ALL.value,
        }

        # Create the target blocks that are initially in the shelf. Evenly space
        # them horizontally and apply rotations.
        block_num = 0
        target_block_in_shelf_center_positions = (
            self._spec.get_target_block_in_shelf_center_positions(
                self._num_init_shelf_blocks, shelf_pose
            )
        )
        for (center_x, center_y), rot in zip(
            target_block_in_shelf_center_positions,
            shelf_target_block_rotations,
            strict=True,
        ):
            block = Object(f"block{block_num}", TargetBlockType)
            block_num += 1
            rect = Rectangle.from_center(
                center_x,
                center_y,
                self._spec.target_block_shape[0],
                self._spec.target_block_shape[1],
                rot,
            )
            init_state_dict[block] = {
                "x": rect.x,
                "y": rect.y,
                "theta": rect.theta,
                "width": rect.width,
                "height": rect.height,
                "static": False,
                "color_r": self._spec.target_block_rgb[0],
                "color_g": self._spec.target_block_rgb[1],
                "color_b": self._spec.target_block_rgb[2],
                "z_order": ZOrder.SURFACE.value,
            }

        # Create the target blocks that are initially outside the shelf.
        if target_block_outside_poses is not None:
            for pose in target_block_outside_poses:
                block = Object(f"block{block_num}", TargetBlockType)
                block_num += 1
                init_state_dict[block] = {
                    "x": pose.x,
                    "y": pose.y,
                    "theta": pose.theta,
                    "width": self._spec.target_block_shape[0],
                    "height": self._spec.target_block_shape[1],
                    "static": False,
                    "color_r": self._spec.target_block_rgb[0],
                    "color_g": self._spec.target_block_rgb[1],
                    "color_b": self._spec.target_block_rgb[2],
                    "z_order": ZOrder.SURFACE.value,
                }

        # Finalize state.
        return create_state_from_dict(init_state_dict, Geom2DRobotEnvTypeFeatures)

    def _get_reward_and_done(self) -> tuple[float, bool]:
        assert self._current_state is not None
        shelf = self._current_state.get_objects(ShelfType)[0]
        blocks = self._current_state.get_objects(TargetBlockType)
        terminated = all(
            is_inside(self._current_state, block, shelf, self._static_object_body_cache)
            for block in blocks
        )
        return -1.0, terminated


class ClutteredStorage2DEnv(gymnasium.Env[NDArray[np.float32], NDArray[np.float32]]):
    """Cluttered sotrage 2D env."""

    def __init__(
        self,
        num_blocks: int = 3,
        spec: ClutteredStorage2DEnvSpec = ClutteredStorage2DEnvSpec(),
        **kwargs,
    ) -> None:
        super().__init__()
        # At the moment, all the real logic for this environment is defined
        # externally. We create that environment and then add some additional
        # code to vectorize observations, making it easier for RL approaches.
        self._geom2d_env = ObjectCentricClutteredStorage2DEnv(
            num_blocks=num_blocks, spec=spec, **kwargs
        )
        # Create a Box version of the observation space by assuming a constant
        # number of obstructions (and thus a constant number of objects).
        assert isinstance(self._geom2d_env.observation_space, ObjectCentricStateSpace)
        # Make observation vectors start with the robot, then the shelf,
        # then target blocks. Don't include the walls or because those are
        # universally constant.
        exemplar_object_centric_state, _ = self._geom2d_env.reset()
        obj_name_to_obj = {o.name: o for o in exemplar_object_centric_state}
        self._constant_objects = [
            obj_name_to_obj["robot"],
            obj_name_to_obj["shelf"],
        ]
        block_names = {o for o in obj_name_to_obj if o.startswith("block")}
        assert len(block_names) == num_blocks
        for block_name in sorted(block_names):
            self._constant_objects.append(obj_name_to_obj[block_name])
        self.observation_space = self._geom2d_env.observation_space.to_box(
            self._constant_objects, Geom2DRobotEnvTypeFeatures
        )
        self.action_space = self._geom2d_env.action_space
        assert isinstance(self.observation_space, ObjectCentricBoxSpace)
        assert isinstance(self.action_space, CRVRobotActionSpace)
        # Add descriptions to metadata for doc generation.
        env_md = create_env_description(num_blocks)
        obs_md = self.observation_space.create_markdown_description()
        act_md = self.action_space.create_markdown_description()
        reward_md = "A penalty of -1.0 is given at every time step until termination, which occurs when all blocks are inside the shelf.\n"  # pylint: disable=line-too-long
        references_md = "Similar environments have been considered by many others, especially in the task and motion planning literature.\n"  # pylint: disable=line-too-long
        self.metadata = {
            "description": env_md,
            "observation_space_description": obs_md,
            "action_space_description": act_md,
            "reward_description": reward_md,
            "references": references_md,
            "render_modes": self._geom2d_env.metadata["render_modes"],
            "render_fps": self._geom2d_env.metadata["render_fps"],
        }

    def reset(self, *args, **kwargs) -> tuple[NDArray[np.float32], dict]:
        super().reset(*args, **kwargs)  # necessary to reset RNG if seed is given
        obs, info = self._geom2d_env.reset(*args, **kwargs)
        assert isinstance(self.observation_space, ObjectCentricBoxSpace)
        vec_obs = self.observation_space.vectorize(obs)
        return vec_obs, info

    def step(
        self, *args, **kwargs
    ) -> tuple[NDArray[np.float32], float, bool, bool, dict]:
        obs, reward, terminated, truncated, done = self._geom2d_env.step(
            *args, **kwargs
        )
        assert isinstance(self.observation_space, ObjectCentricBoxSpace)
        vec_obs = self.observation_space.vectorize(obs)
        return vec_obs, reward, terminated, truncated, done

    def render(self):
        return self._geom2d_env.render()

    def get_action_from_gui_input(
        self, gui_input: dict[str, Any]
    ) -> NDArray[np.float32]:
        """Get the mapping from human inputs to actions."""
        assert isinstance(self.action_space, CRVRobotActionSpace)
        return get_geom2d_crv_robot_action_from_gui_input(self.action_space, gui_input)


def create_env_description(num_blocks: int = 3) -> str:
    """Create a human-readable environment description."""
    # pylint: disable=line-too-long
    return f"""A 2D environment where the goal is to put all blocks inside a shelf.

There are always {num_blocks} blocks in this environment.

The robot has a movable circular base and a retractable arm with a rectangular vacuum end effector. Objects can be grasped and ungrasped when the end effector makes contact.
"""
