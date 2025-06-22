import os

import blender_asset_cfg

from isaaclab.assets import RigidObjectCollectionCfg

MANIBOT_AIRPORT = RigidObjectCollectionCfg(
    rigid_objects=blender_asset_cfg.define_asset_configs(
        reference_stage_path=os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            "assets",
            "usd",
            "airport",
            "airport_environment.usda",
        ),
        default_rigid_body_behavior="static",
        default_collision_approximation_method="convex_decomposition",
        asset_collision_approximation_method={
            "Suitcase_.*": "sdf",  # Suitcases
        },
        dynamic_assets=["Suitcase_.*"],
        static_assets=[],
    ),
)
