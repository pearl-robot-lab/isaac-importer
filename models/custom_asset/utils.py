from typing import Literal, Optional

import carb  # type: ignore
import fnmatch
import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObjectCfg
from pxr import Usd  # type: ignore

from utils import usd_tree
from models.custom_asset.custom_asset import spawn_asset
from models.custom_asset.custom_asset_spawner_cfg import CustomAssetSpawnerCfg


def custom_asset_from_usd(
    file_path: str,
    rigid_props: sim_utils.RigidBodyPropertiesCfg,
    mass_props: sim_utils.MassPropertiesCfg,
    collision_props: sim_utils.CollisionPropertiesCfg,
    collision_approximation: Literal[
        "triangle_mesh",
        "convex_decomposition",
        "convex_hull",
        "bounding_sphere",
        "bounding_cube",
        "mesh_simplification",
        "sdf",
        "sphere_approximation",
    ] = "convex_hull",
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> CustomAssetSpawnerCfg:
    stage: Usd.Stage = Usd.Stage.Open(filePath=file_path)  # type: ignore

    # * Go over the source and extract all relevant assets and materials
    # root = parse_usd(BlenderAsset.reference_stage)
    root = usd_tree.parse_usd(stage)
    materials: list[usd_tree.PrimNode] = []
    for node in root.children.copy():
        if node.prim.GetName() == "_materials":
            materials.extend([child for child in node.children])
            root.children.remove(node)

    # TODO: here goes the logic that ensures that we pull a single rigid object out of the usd

    # ! This still needs to be here, because the single asset might still have children underneath it. we need to parse those accordingly
    # * Go over the assets and define their rigid body behavior and their collision approximation method

    # ? I guess from here it would all be the same?

    # asset_cfgs = _parse_asset_config(
    #     root.children,
    #     default_rigid_body_behavior,
    #     static_assets,
    #     dynamic_assets,
    #     default_collision_approximation_method,
    #     asset_collision_approximation_method,
    # )

    # # * Create RigidObjectCfgs for each asset, in alignment with the asset_cfgs from above
    # asset_definitions = {
    #     # Add AssetBaseCfg as grouping element for our assets
    #     # "Assets": AssetBaseCfg(
    #     #     prim_path=f"/World/envs/env_.*/Assets", class_type=None, spawn=None
    #     # )
    # }

    # stage.Unload(asset_root)  # type: ignore

    return CustomAssetSpawnerCfg(
        func=spawn_asset,
        source_node=root,
        materials=materials,
        scale=scale,
        rigid_props=rigid_props,
        mass_props=mass_props,
        collision_props=collision_props,
        collision_approximation=collision_approximation,
    )

    for prim_node, asset_cfg in asset_cfgs.items():
        cfg = RigidObjectCfg(
            prim_path=f"/World/envs/env_.*/{prim_node.prim.GetName()}",
            spawn=BlenderAssetCfg(
                func=spawn_asset,
                source_node=prim_node,
                scale=[0.5, 0.5, 0.5],
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=asset_cfg["rigid_body_behavior"] == "static",
                    solver_position_iteration_count=4,
                    # max_depenetration_velocity=1.0,
                ),
                collision_props=sim_utils.CollisionPropertiesCfg(
                    collision_enabled=True,
                    # contact_offset=0.05,
                    # rest_offset=0.05,
                ),
                collision_approximation=asset_cfg["collision_approximation_method"],
                # TODO: What about mass? How are we going to pipe mass info through here? Should we leave it out and let IsaacSim calculate it?
                mass_props=sim_utils.MassPropertiesCfg(mass=100.0),
            ),
        )

        asset_definitions[str(prim_node.prim.GetName())] = cfg

    return asset_definitions


def rigid_object_collection_from_usd(
    file_path: str,
    default_rigid_body_behavior: Literal["static", "dynamic"] = "static",
    static_assets: Optional[list[str]] = None,
    dynamic_assets: Optional[list[str]] = None,
    default_collision_approximation_method: Literal[
        "triangle_mesh",
        "convex_decomposition",
        "convex_hull",
        "bounding_sphere",
        "bounding_cube",
        "mesh_simplification",
        "sdf",
        "sphere_approximation",
    ] = "convex_hull",
    asset_collision_approximation_method: Optional[
        dict[
            str,
            Literal[
                "triangle_mesh",
                "convex_decomposition",
                "convex_hull",
                "bounding_sphere",
                "bounding_cube",
                "mesh_simplification",
                "sdf",
                "sphere_approximation",
            ],
        ]
    ] = None,
) -> dict[str, RigidObjectCfg]:
    stage: Usd.Stage = Usd.Stage.Open(filePath=file_path)  # type: ignore

    # * Go over the source and extract all relevant assets and materials
    # root = parse_usd(BlenderAsset.reference_stage)
    root = usd_tree.parse_usd(stage)
    materials: list[usd_tree.PrimNode] = []
    for node in root.children.copy():
        if node.prim.GetName() == "_materials":
            materials.extend([child for child in node.children])
            root.children.remove(node)

    # TODO: here is the logic that ensures that we pull a single rigid object out of the usd
    # material = list(
    #             filter(
    #                 lambda mat: mat.GetPath().elementString == target.elementString,
    #                 materials,
    #             )
    #         )[0]

    # ! This still needs to be here, because the single asset might still have children underneath it. we need to parse those accordingly
    # * Go over the assets and define their rigid body behavior and their collision approximation method

    # ? I guess from here it would all be the same?

    asset_cfgs = _parse_asset_config(
        root.children,
        default_rigid_body_behavior,
        static_assets,
        dynamic_assets,
        default_collision_approximation_method,
        asset_collision_approximation_method,
    )

    # # * Create RigidObjectCfgs for each asset, in alignment with the asset_cfgs from above
    asset_definitions = {
        # Add AssetBaseCfg as grouping element for our assets
        # "Assets": AssetBaseCfg(
        #     prim_path=f"/World/envs/env_.*/Assets", class_type=None, spawn=None
        # )
    }

    # return CustomAssetSpawnerCfg(
    #     func=spawn_asset,
    #     source_node=root,
    #     materials=materials,
    #     scale=scale,
    #     rigid_props=rigid_props,
    #     mass_props=mass_props,
    #     collision_props=collision_props,
    #     collision_approximation=collision_approximation,
    # )

    for prim_node, asset_cfg in asset_cfgs.items():
        cfg = RigidObjectCfg(
            prim_path=f"/World/envs/env_.*/{prim_node.prim.GetName()}",
            spawn=CustomAssetSpawnerCfg(
                func=spawn_asset,
                source_node=prim_node,
                materials=materials,  # TODO: Create Materials according to whether this is a single asset or a collection of assets
                scale=(0.4, 0.4, 0.4),
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=asset_cfg["rigid_body_behavior"] == "static",
                    solver_position_iteration_count=4,
                    # max_depenetration_velocity=1.0,
                ),
                collision_props=sim_utils.CollisionPropertiesCfg(
                    collision_enabled=True,
                    # contact_offset=0.05,
                    # rest_offset=0.05,
                ),
                collision_approximation=asset_cfg["collision_approximation_method"],  # type: ignore
                # TODO: What about mass? How are we going to pipe mass info through here? Should we leave it out and let IsaacSim calculate it?
                mass_props=sim_utils.MassPropertiesCfg(mass=100.0),
            ),
        )

        asset_definitions[str(prim_node.prim.GetName())] = cfg

    # stage.Unload(asset_root)  # type: ignore

    return asset_definitions


def _parse_asset_config(
    assets: list[usd_tree.PrimNode],
    default_rigid_body_behavior: Literal["static", "dynamic"] = "static",
    static_assets: Optional[list[str]] = None,
    dynamic_assets: Optional[list[str]] = None,
    default_collision_approximation_method: Literal[
        "triangle_mesh",
        "convex_decomposition",
        "convex_hull",
        "bounding_sphere",
        "bounding_cube",
        "mesh_simplification",
        "sdf",
        "sphere_approximation",
    ] = "convex_hull",
    asset_collision_approximation_method: Optional[
        dict[
            str,
            Literal[
                "triangle_mesh",
                "convex_decomposition",
                "convex_hull",
                "bounding_sphere",
                "bounding_cube",
                "mesh_simplification",
                "sdf",
                "sphere_approximation",
            ],
        ]
    ] = None,
) -> dict[
    usd_tree.PrimNode,
    dict[
        Literal[
            "rigid_body_behavior",
            "collision_approximation_method",
        ],
        str,
    ],
]:
    """Validates if config is valid and creates config dict regarding rigid body behavior and collision approximation method for the assets, based on the provided asset name regex and the static/dynamic_assets and asset_collision_approximation_method parameters.

    Returns:
        dict[Usd.Prim, dict[Literal["rigid_body_behavior", "collision_approximation_method"]]]: Dictionary with the reference as key and the config dict as value.
    """
    # * Validate if parameter combinations are valid
    # Can only have one of, either static or dynamic assets
    if static_assets is not None and dynamic_assets is not None:
        carb.log_error(
            "Provided both a list with static assets and a list with dynamics assets at the same time. Unexpected behavior might arise! Proceed with caution!"
        )
    # If default method is static and list of static assets has been provided, log a warning to the console to inform the user
    if default_rigid_body_behavior == "static" and static_assets is not None:
        carb.log_warn(
            f"Default Rigid Body Behavior is 'static', but provided a list with static assets. Provided list will have no additional effect. Did you perhaps try to set a list of dynamic items?"
        )
    if default_rigid_body_behavior == "dynamic" and dynamic_assets is not None:
        carb.log_warn(
            f"Default Rigid Body Behavior is 'dynamic', but provided a list with dynamic assets. Provided list will have no additional effect. Did you perhaps try to set a list of static items?"
        )

    # * Get all assets and define their rigid body behavior and their collision behavior
    asset_cfg: dict[
        usd_tree.PrimNode,
        dict[
            Literal[
                "rigid_body_behavior",
                "collision_approximation_method",
            ],
            str,
        ],
    ] = {}
    for asset in assets:
        # Set default values
        asset_cfg[asset] = {
            "rigid_body_behavior": default_rigid_body_behavior,
            "collision_approximation_method": default_collision_approximation_method,
        }
        # parse rigid bdy behavior
        if static_assets is not None:
            for pattern in static_assets:
                if fnmatch.fnmatch(
                    asset.prim.GetName(), pattern.replace(".", "*") + "*"
                ):
                    asset_cfg[asset]["rigid_body_behavior"] = "static"
        if dynamic_assets is not None:
            for pattern in dynamic_assets:
                if fnmatch.fnmatch(
                    asset.prim.GetName(), pattern.replace(".", "*") + "*"
                ):
                    asset_cfg[asset]["rigid_body_behavior"] = "dynamic"

        # parse collisions
        if asset_collision_approximation_method is not None:
            for pattern, method in asset_collision_approximation_method.items():
                if fnmatch.fnmatch(
                    asset.prim.GetName(), pattern.replace(".", "*") + "*"
                ):
                    asset_cfg[asset]["collision_approximation_method"] = method

    return asset_cfg
