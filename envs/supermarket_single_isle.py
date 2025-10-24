import os


from isaaclab.assets import RigidObjectCollectionCfg

from blender_asset_cfg import define_asset_configs
from models.custom_asset.utils import rigid_object_collection_from_usd

# MANIBOT_ISLE = RigidObjectCollectionCfg(
#     rigid_objects=define_asset_configs(  # type: ignore
#         reference_stage_path=os.path.join(
#             os.path.dirname(__file__),
#             os.path.pardir,
#             "assets",
#             "usd",
#             "convenience_store",
#             "single_isle.usda",
#         ),
#         default_rigid_body_behavior="static",
#         default_collision_approximation_method="convex_decomposition",
#         asset_collision_approximation_method={
#             "Cube_045": "mesh_simplification",  # Outside Walls
#             "Bodyframe": "sdf",  # Shelves
#             "crispix.*": "sdf",  # Test
#         },
#         dynamic_assets=["crispix.*"],
#         static_assets=[
#             # Shelves
#             "Bodyframe",
#         ],
#     ),
# )


MANIBOT_ISLE = RigidObjectCollectionCfg(
    rigid_objects=rigid_object_collection_from_usd(
        file_path=os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            "assets",
            "usd",
            "convenience_store",
            "single_isle.usda",
        ),
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
    )
)
