import blender_asset_cfg

from isaaclab.assets import RigidObjectCollectionCfg

MANIBOT_AIRPORT = RigidObjectCollectionCfg(
    rigid_objects=blender_asset_cfg.define_asset_configs(
        reference_stage_path="/isaac-sim/isaac-importer/assets/usd/airport/airport_environment.usda",
        default_rigid_body_behavior="static",
        default_collision_approximation_method="convex_decomposition",
        asset_collision_approximation_method={
            "Cube_045": "mesh_simplification",  # Outside Walls
            "Bodyframe": "sdf",  # Shelves
            "crispix.*": "sdf",  # Test
        },
        dynamic_assets=["crispix.*"],
        static_assets=[
            # Shelves
            "Bodyframe",
        ],
    ),
)