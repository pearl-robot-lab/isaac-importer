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
from isaaclab.assets import AssetBaseCfg, Articulation
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sim import SimulationContext
from isaaclab.utils.timer import Timer
from isaaclab.utils import configclass
from isaaclab.assets import (
    AssetBaseCfg,
    RigidObjectCollection,
)
from isaacsim.core.utils.stage import get_current_stage
from pxr import UsdGeom, Sdf

# from envs.airport import MANIBOT_AIRPORT

from envs.supermarket_full import MANIBOT_SUPERMARKET

# from envs.supermarket_single_isle import MANIBOT_ISLE

import pearl_robots

from pearl_robots.isaaclab.tiago.tiago_dual_cfg import TIAGO_DUAL
from pearl_robots.isaaclab.tiago.tiago_tsid_formulation_wrapper import (
    TiagoTsidFormulationWrapper,
)

# from assets.pearl_robots.assets.robot.tiago.tiago_dual_cfg import TIAGO_DUAL
# from assets.pearl_robots.tiago_tsid_formulation_wrapper import (
#     TiagoTsidFormulationWrapper,
# )

# TODO: Something not 100% right, when importing multiple environments.
# In Supermarket, lamps are pink

# VRAM usage the same, but RAM usage is increase around 3-4GB
# Every env seems to be stored in RAM. Can do better by unloading


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

    # assets = MANIBOT_AIRPORT

    # assets = MANIBOT_ISLE

    assets = MANIBOT_SUPERMARKET

    robot = TIAGO_DUAL
    robot.init_state.pos = (0.3, 0.0, 0.0)


##
# Simulation Loop
##
def run_simulator(sim: SimulationContext, scene: InteractiveScene):
    """Runs the simulation loop."""
    # Extract scene entities
    assets: RigidObjectCollection = scene["assets"]
    robot: Articulation = scene["robot"]

    # robot_cfg_file_path = os.path.join(os.path.dirname(__file__), "tiago_dual.yml")
    # robot_cfg_file = open(robot_cfg_file_path, "r")
    # robot_cfg = yaml.safe_load(robot_cfg_file)["robot_cfg"]  # type: ignore

    # base_motion_cfg_file_path = os.path.join(
    #     os.path.dirname(__file__), "base_tsid_motion_cfg.yml"
    # )
    # base_motion_cfg_file = open(base_motion_cfg_file_path, "r")
    # base_motion_cfg = yaml.safe_load(base_motion_cfg_file)

    # assets_path = os.path.join(os.path.dirname(__file__), "assets")
    # asset_root_path = os.path.join(
    #     assets_path, robot_cfg["kinematics"]["asset_root_path"]
    # )
    # urdf_path = os.path.join(assets_path, robot_cfg["kinematics"]["urdf_path"])

    # # Define simulation stepping
    # sim_dt = sim.get_physics_dt()
    # count = 0
    # t = 0.0

    # Define simulation stepping
    sim_dt = sim.get_physics_dt()
    count = 0

    formulation = TiagoTsidFormulationWrapper(robot, control_dt=sim_dt)

    scene.reset()
    print("[INFO]: Resetting scene state...")

    formulation.set_left_ee_pose_goal(
        torch.tensor([0.3, 0.3, 0.3, 1.0, 0.0, 0.0, 0.0]).unsqueeze(0)
    )

    # Simulation loop
    while simulation_app.is_running():

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
    sim_cfg = sim_utils.SimulationCfg(dt=0.005, device=args_cli.device)
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
