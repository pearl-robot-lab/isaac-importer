"""Launch Isaac Sim Simulator first."""

import argparse
import os
import torch
import yaml

from isaaclab.app import AppLauncher


# add argparse arguments
parser = argparse.ArgumentParser(
    description="Demo on spawning different objects in multiple environments.",
)
parser.add_argument(
    "--num_envs",
    type=int,
    default=1,
    help="Number of environments to spawn.",
)
parser.add_argument(
    "--env_spacing",
    type=float,
    default=40.0,
    help="Space between individual environments.",
)


# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
# parse the arguments
args_cli = parser.parse_args()
args_cli.headless = False

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""


import isaaclab.sim as sim_utils
from isaaclab.assets import (
    AssetBaseCfg,
    Articulation,
    RigidObjectCfg,
    RigidObject,
    RigidObjectCollectionCfg,
)
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sim import SimulationContext
from isaaclab.utils.timer import Timer
from isaaclab.utils import configclass
from isaaclab.assets import AssetBaseCfg, RigidObjectCollection

# from envs.airport import MANIBOT_AIRPORT

# from envs.supermarket_full import MANIBOT_SUPERMARKET

from envs.supermarket_single_isle import MANIBOT_ISLE

from pearl_robots.isaaclab.tiago.utils.common import goal_reached

from pearl_robots.isaaclab.tiago.tiago_dual_cfg import TIAGO_DUAL
from pearl_robots.isaaclab.tiago.tiago_tsid_formulation_wrapper import (
    TiagoTsidFormulationWrapper,
)

# from models.custom_asset_cfg import CustomAssetCfg, define_asset_configs


# from assets.pearl_robots.assets.robot.tiago.tiago_dual_cfg import TIAGO_DUAL
# from assets.pearl_robots.tiago_tsid_formulation_wrapper import (
#     TiagoTsidFormulationWrapper,
# )

# TODO: Something not 100% right, when importing multiple environments.
# In Supermarket, lamps are pink

# VRAM usage the same, but RAM usage is increase around 3-4GB
# Every env seems to be stored in RAM. Can do better by unloading

GOAL_LEFT = (2.3, 0.10, 0.8)
GOAL_RIGHT = (2.3, -0.30, 0.8)


@configclass
class BlenderSceneCfg(InteractiveSceneCfg):
    # # Create scopes to hold assets in to keep the tree in the GUI clean.
    # # Have to create asset folder manually, as IsaacLab won't create it for us.
    # [
    #     UsdGeom.Scope.Define(
    #         get_current_stage(), Sdf.Path(f"/World/envs/env_{i}/Assets")
    #     )
    #     for i in range(args_cli.num_envs)
    # ]
    # ground plane
    ground = AssetBaseCfg(
        prim_path="/World/defaultGroundPlane", spawn=sim_utils.GroundPlaneCfg()
    )

    # lights
    dome_light = AssetBaseCfg(
        prim_path="/World/Light",
        spawn=sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75)),
    )

    goal_sphere_left = RigidObjectCfg(
        prim_path=f"/World/envs/env_.*/Goal_left",
        spawn=sim_utils.SphereCfg(
            radius=0.03,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                kinematic_enabled=True,
                disable_gravity=True,
                max_linear_velocity=1000,
                max_angular_velocity=1000,
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=1,
                max_depenetration_velocity=1000.0,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            # collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.0, 0.0, 1.0), metallic=0.2
            ),
        ),  # wait for initialization
        init_state=RigidObjectCfg.InitialStateCfg(
            lin_vel=(0.0, 0.0, 0.0),
            ang_vel=(0.0, 0.0, 0.0),
            pos=GOAL_LEFT,
        ),
    )

    goal_sphere_right = RigidObjectCfg(
        prim_path=f"/World/envs/env_.*/Goal_right",
        spawn=sim_utils.SphereCfg(
            radius=0.03,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                kinematic_enabled=True,
                disable_gravity=True,
                max_linear_velocity=1000,
                max_angular_velocity=1000,
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=1,
                max_depenetration_velocity=1000.0,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            # collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.0, 1.0, 0.0), metallic=0.2
            ),
        ),  # wait for initialization
        init_state=RigidObjectCfg.InitialStateCfg(
            lin_vel=(0.0, 0.0, 0.0),
            ang_vel=(0.0, 0.0, 0.0),
            pos=GOAL_RIGHT,
        ),
    )

    # assets = MANIBOT_AIRPORT

    # target = RigidObjectCfg(
    #     prim_path=f"/World/envs/env_.*/target",
    #     spawn=sim_utils.UsdFileCfg(
    #         usd_path=os.path.join(
    #             os.path.dirname(__file__),
    #             "assets",
    #             "usd",
    #             "convenience_store",
    #             "additional_assets",
    #             "shampoo",
    #             "shampoo.usdc",
    #         ),
    #         mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
    #         rigid_props=sim_utils.RigidBodyPropertiesCfg(rigid_body_enabled=True),
    #     ),
    #     init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, 2.0)),
    # )

    # assets = MANIBOT_SUPERMARKET

    robot = TIAGO_DUAL
    robot.init_state.pos = (1.0, 0.0, 0.0)
    # assets = MANIBOT_AIRPORT

    assets = MANIBOT_ISLE
    # assets = MANIBOT_SUPERMARKET

    # target = RigidObjectCfg(prim_path="/World/envs/env_.*/target", spawn=)

    # define_rigid_object_config(
    #     reference_stage_path=os.path.join(
    #         os.path.dirname(__file__),
    #         "assets",
    #         "usd",
    #         "convenience_store",
    #         "additional_assets",
    #         "shampoo",
    #         "shampoo.usdc",
    #     ),
    #     rigid_body_behavior="dynamic",
    #     collision_approximation_method="convex_hull",
    #     asset_name="shampoo",
    # )


##
# Simulation Loop
##
def run_simulator(sim: SimulationContext, scene: InteractiveScene):
    """Runs the simulation loop."""
    # Extract scene entities
    assets: RigidObjectCollection = scene["assets"]
    robot: Articulation = scene["robot"]

    goal_sphere_left: RigidObject = scene["goal_sphere_left"]
    goal_sphere_right: RigidObject = scene["goal_sphere_right"]

    # Define simulation stepping
    sim_dt = sim.get_physics_dt()
    count = 0

    formulation = TiagoTsidFormulationWrapper(robot, control_dt=sim_dt)

    scene.reset()
    print("[INFO]: Resetting scene state...")

    # formulation.set_left_ee_pose_goal(
    #     torch.tensor([0.3, 0.3, 0.3, 1.0, 0.0, 0.0, 0.0]).unsqueeze(0)
    # )

    # goal_sphere_left.write_root_pose_to_sim(
    #     torch.tensor(
    #         torch.hstack([torch.tensor(GOAL_LEFT), torch.tensor([1.0, 0.0, 0.0, 0.0])])
    #     ).to(device=robot.device)
    # )

    offset = torch.tensor([-0.7, 0.0, 0.0])

    # Simulation loop
    while simulation_app.is_running():

        if count % 1500 == 0:
            # reset counter
            # ! Resetting robot is important for tsid to work!!!!!
            # -> Probably misalignment between tsid (pin) representation and isaaclab representation?
            # => Would be interesting to fetch current joints positions directly from articulation object

            count = 0
            # reset the scene entities
            # object
            # root_state = rigid_object.data.default_root_state.clone()
            # root_state[:, :3] += scene.env_origins
            # rigid_object.write_root_state_to_sim(root_state)
            # object collection
            # TODO: This breaks, when num_envs > 0. Does not break in the multiAssetExample.

            # object_state = rigid_object_collection.data.default_object_state.clone()
            # object_state[..., :3] += scene.env_origins.unsqueeze(1)
            # rigid_object_collection.write_object_state_to_sim(object_state)

            # robot
            # -- root state
            root_state = robot.data.default_root_state.clone()
            root_state[:, :3] += scene.env_origins
            robot.write_root_state_to_sim(root_state)
            # # -- joint state
            joint_pos, joint_vel = (
                robot.data.default_joint_pos.clone(),
                robot.data.default_joint_vel.clone(),
            )
            robot.write_joint_state_to_sim(joint_pos, joint_vel)

            # clear internal buffers
            scene.reset()
            print("[INFO]: Resetting scene state...")

        # * change ball position
        # offset_left = torch.tensor([0.2, 0.1, 0.1])

        # multiplier = 1 / 1.0

        # radius = 0.0
        # offset_left[0] *= torch.sin(torch.tensor(count / (multiplier * 100)))
        # offset_left[1] *= torch.sin(torch.tensor(count / (multiplier * 100))) + 0.2
        # offset_left[2] *= torch.cos(torch.tensor(count / (multiplier * 100)))
        # offset_left[2] += 0.2 * 0

        # offset_right = offset_left.detach().clone()
        # offset_right[1] *= -1

        # offset_left[0] += torch.sin(torch.tensor(count / 1000)) * radius
        # offset_left[1] += torch.cos(torch.tensor(count / 1000)) * radius
        # offset_right[0] += torch.sin(torch.tensor(count / 1000)) * radius
        # offset_right[1] += torch.cos(torch.tensor(count / 1000)) * radius

        goal_tensor_left = torch.tensor(GOAL_LEFT) + offset
        goal_tensor_right = torch.tensor(GOAL_RIGHT) + offset
        goals = (
            torch.stack([goal_tensor_left, goal_tensor_right], dim=0)
            .unsqueeze(0)  # add batch dimension
            .expand(
                scene.num_envs, -1, -1
            )  # expand batch dimension to shape (num_envs, num_goals, 3)
            .to(device=robot.device)
        )

        # goal_tensor_left_with_offset = torch.tensor(GOAL_LEFT)
        # goal_tensor_right_with_offset = torch.tensor(GOAL_RIGHT)
        # goals_with_offset = (
        #     torch.stack([goal_tensor_left_with_offset, goal_tensor_right_with_offset], dim=0)
        #     .unsqueeze(0)  # add batch dimension
        #     .expand(
        #         scene.num_envs, -1, -1
        #     )  # expand batch dimension to shape (num_envs, num_goals, 3)
        #     .to(device=robot.device)
        # )

        target_links = ["gripper_left_grasping_frame", "gripper_right_grasping_frame"]

        if bool(goal_reached(robot, goals, target_links)):
            offset *= 0
        # if count < 1000:
        #     new_goal_tensor_left = goal_tensor_left + offset
        # else:
        #     new_goal_tensor_left = goal_tensor_left  # + offset_left
        new_goal_tensor_left = goal_tensor_left
        new_goal_pose_left = torch.hstack(
            (new_goal_tensor_left, torch.tensor([1.0, 0.0, 0.0, 0.0]))
        )
        goal_sphere_left.write_root_pose_to_sim(new_goal_pose_left)

        new_goal_tensor_right = goal_tensor_right
        # new_goal_tensor_right = goal_tensor_right  # + offset_right
        new_goal_pose_right = torch.hstack(
            (new_goal_tensor_right, torch.tensor([1.0, 0.0, 0.0, 0.0]))
        )
        goal_sphere_right.write_root_pose_to_sim(new_goal_pose_right)

        goals_left = [new_goal_pose_left] * robot.num_instances
        goals_right = [new_goal_pose_right] * robot.num_instances

        formulation.set_left_ee_pose_goal(torch.vstack(goals_left))
        formulation.set_right_ee_pose_goal(torch.vstack(goals_right))
        formulation.set_head_look_at(goals_left)

        # DO STUFF
        joint_pos, joint_vel, _, _ = formulation.compute_joint_angles()
        robot.set_joint_position_target(joint_pos)
        robot.set_joint_velocity_target(joint_vel)

        # Write data to sim
        scene.write_data_to_sim()
        # Perform step
        sim.step()
        # Increment counter
        count += 1
        # Update buffers
        scene.update(sim_dt)


def main():
    """Main function."""
    # Load kit helper
    sim_cfg = sim_utils.SimulationCfg(dt=1 / 60.0, device=args_cli.device)
    sim_cfg.render.rendering_mode = "balanced"
    sim = sim_utils.SimulationContext(sim_cfg)
    # Set main camera
    sim.set_camera_view([5.5, 8.0, 6.0], [5.5, -5.0, 0.0])  # eye and target positions

    # Design scene
    scene_cfg = BlenderSceneCfg(
        num_envs=args_cli.num_envs,
        env_spacing=args_cli.env_spacing,
        replicate_physics=False,
    )
    with Timer("[INFO] Time to create scene: "):
        scene = InteractiveScene(scene_cfg)

    # Play the simulator
    with Timer("[INFO] Time to reset the sim: "):
        sim.reset()
    # Now we are ready!
    print("[INFO]: Setup complete...")
    # Run the simulator
    run_simulator(sim, scene)


if __name__ == "__main__":
    # run the main execution
    main()
    # close sim app
    simulation_app.close()
