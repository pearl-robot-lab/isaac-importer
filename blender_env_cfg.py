"""Launch Isaac Sim Simulator first."""

import argparse

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

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""


import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sim import SimulationContext
from isaaclab.utils.timer import Timer
from isaaclab.utils import configclass

from isaaclab.assets import (
    AssetBaseCfg,
    RigidObjectCollection,
)

# from envs.supermarket import MANIBOT_SUPERMARKET

# from envs.supermarket import MANIBOT_ISLE

from envs.airport import MANIBOT_AIRPORT


@configclass
class BlenderSceneCfg(InteractiveSceneCfg):
    # ground plane
    ground = AssetBaseCfg(
        prim_path="/World/defaultGroundPlane", spawn=sim_utils.GroundPlaneCfg()
    )

    # lights
    dome_light = AssetBaseCfg(
        prim_path="/World/Light",
        spawn=sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75)),
    )

    assets = MANIBOT_AIRPORT

    # assets = MANIBOT_ISLE

    # assets = MANIBOT_SUPERMARKET


##
# Simulation Loop
##
def run_simulator(sim: SimulationContext, scene: InteractiveScene):
    """Runs the simulation loop."""
    # Extract scene entities
    assets: RigidObjectCollection = scene["assets"]
    # robot: Articulation = scene["robot"]

    # Define simulation stepping
    sim_dt = sim.get_physics_dt()
    count = 0

    scene.reset()
    print("[INFO]: Resetting scene state...")

    # Simulation loop
    while simulation_app.is_running():

        # DO STUFF

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
