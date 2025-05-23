"""
In order to create the neccesary configs, the importer first loads all assets into a separate scene. Then, this scene gets queried and all relevant assets, APIs, materials and attributes get extracted. The materials get created directly, as they are independent of the number of environments created. For the assets, we copy a reference to the Xform and the Mesh from the separate scene and pass it to the cfg. The `BlenderAsset` then queries the xform and the mesh and copies the APIs and attributes to a newly created prim in the final scene. Besides the xform and mesh, `BlenderAssetCfg` holds references to the function called by the sim during scene creation, `RigidBodyPropertiesCfg` for define the rigid body behavior, `CollisionPropertiesCfg` to define the collision behavior in tandem with the `collision_approximation` parameter. Finally, `MassPropertiesCfg` defines the mass properties for an asset.
"""

from collections.abc import Callable
from typing import Any, Literal, Optional
import isaaclab.sim as sim_utils
from isaaclab.utils import configclass
from isaaclab.assets import RigidObjectCfg
from blender_asset import BlenderAsset
from dataclasses import MISSING
import carb
import fnmatch

import blender_asset

from blender_asset import spawn_asset

from blender_asset import BlenderAsset

from pxr import Usd, UsdGeom, UsdShade, Sdf


@configclass
class BlenderAssetCfg(sim_utils.MeshCfg):
    """Config for spawning blender asset from a reference stage."""

    func: Callable = spawn_asset

    xform_source: str = MISSING

    mesh_source: str = MISSING

    scale: list[float] = MISSING

    collision_approximation: Literal[
        "triangle_mesh",
        "convex_decomposition",
        "convex_hull",
        "bounding_sphere",
        "bounding_cube",
        "mesh_simplification",
        "sdf",
        "sphere_approximation",
    ] = "convex_hull"


def define_asset_configs(
    reference_stage_path: str,
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
    asset_root: str = "/World",
) -> dict[str, BlenderAssetCfg]:
    """Opens the usd to be imported in a new stage and extracts all relevant assets and materials. Returns BlenderAssetCfgs for each asset to be spawned in the scene.

    Args:
        reference_stage_path (str): Path to the `.usd` to be imported.
        default_rigid_body_behavior (Literal["static", "dynamic"], optional): Defines how assets should behave by deafult, whether they should e.g. react to gravity or not. Defaults to "static".
        static_assets (Optional[list[str]], optional): List with expressions of asset names that should stay static in the scene. i.e. not be movable by forces. Defaults to None.
        dynamic_assets (Optional[list[str]], optional): List with expressions of asset names that should be dynamic in the scene. i.e. react to forces. Defaults to None.
        default_collision_approximation_method (Literal[ triangle_mesh, convex_decomposition, convex_hull, bounding_sphere, bounding_cube, mesh_simplification, sdf, sphere_approximation, ], optional): Which collision approximation method should be applied to the assets by default. Defaults to "convex_hull".
        asset_collision_approximation_method (Optional[ dict[ str, Literal[ triangle_mesh, convex_decomposition, convex_hull, bounding_sphere, bounding_cube, mesh_simplification, sdf, sphere_approximation, ], ] ], optional): Dictionary with asset names and the chosen collision approximation method to overwrite the default. Defaults to None.
        asset_root (str, optional): Define the root of the source usd tree. Defaults to "/World".

    Returns:
        dict[str, BlenderAssetCfg]: Dictionary holding the asset names as keys and their corresponding configuraion as value.
    """
    # * Open the source `.usd` in a separate stage
    BlenderAsset.reference_stage: Usd.Stage = Usd.Stage.Open(filePath=reference_stage_path)  # type: ignore
    BlenderAsset.reference_prim = BlenderAsset.reference_stage.GetPrimAtPath(asset_root)  # type: ignore

    # * Go over the source and extract all relevant assets and materials
    assets, materials = _parse_reference_prim(BlenderAsset.reference_prim)  # type: ignore

    # * Create copies of the extracted materials in the new scene
    _create_materials(materials)

    # * Go over the assets and define their rigid body behavior and their collision approximation method
    asset_cfgs = _parse_asset_config(
        assets,
        default_rigid_body_behavior,
        static_assets,
        dynamic_assets,
        default_collision_approximation_method,
        asset_collision_approximation_method,
    )

    # * Create RigidObjectCfgs for wach asset, in alignment with the asset_cfgs from above
    asset_definitions = {}
    for asset, asset_cfg in asset_cfgs.items():
        xform_source: str = str(asset.GetPrimPath())
        children = asset.GetAllChildren()
        if len(children) == 0:
            continue
        mesh_source: str = str(asset.GetAllChildren()[0].GetPrimPath())

        cfg = RigidObjectCfg(
            # prim_path=f"/World/envs/env_.*/Convenience_Store/{asset.GetName()}",
            # TODO: Create a Scope to hold all the assets from this env or create an xform
            prim_path=f"/World/envs/env_.*/{asset.GetName()}",
            spawn=BlenderAssetCfg(
                func=spawn_asset,
                xform_source=xform_source,
                mesh_source=mesh_source,
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

        asset_definitions[str(asset.GetName())] = cfg

    # BlenderAsset.reference_stage.Unload(asset_root)  # type: ignore

    return asset_definitions


def _parse_reference_prim(
    reference_prim: Usd.Prim,
) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Go over the source and extract all assets, meshes and materials. Ignore all lights.

    Args:
        reference_prim (Usd.Prim): Pointer showing to the root of the source scene.

    Returns:
        tuple[list[Usd.Prim], list[Usd.Prim]]: Returns a list of asset pointers and a list of materials.
    """
    # * Get all assets by recursively getting all children
    assets: list = reference_prim.GetAllChildren()
    for asset in assets:
        assets.extend(asset.GetAllChildren())

    # * Remove all Meshes
    assets: list[Usd.Prim] = [asset for asset in assets if not asset.IsA(UsdGeom.Mesh)]

    # * remove lights
    # env_light
    env_lights = list(filter(lambda x: x.GetName() == "env_light", assets))
    for light in env_lights:
        assets.remove(light)
    # TODO: Find way to include lights
    # normal lights
    light_types = [
        "CylinderLight",
        "DiskLight",
        "DistantLight",
        "DomeLight",
        "RectLight",
        "SphereLight",
    ]
    lights = list(
        filter(
            lambda prim: prim.GetTypeName() in light_types
            or any(
                map(
                    lambda child: child.GetTypeName() in light_types,
                    prim.GetAllChildren(),
                )
            ),
            assets,
        )
    )
    for light in lights:
        assets.remove(light)

    # * Filter out materials from assets, keep them separate
    materials = list(
        filter(
            lambda asset: asset.IsA(UsdShade.Material)
            or asset.IsA(UsdGeom.Subset)
            or "_materials" in asset.GetPath().pathString,
            assets,
        )
    )
    for material in materials:
        assets.remove(material)

    for material in materials.copy():
        # ? Currently everything is built around "_materials" and us iterating over all its children later.This could be restricting later, when we don't have a _materials folder, but this might be default for blender
        if material.GetName() != "_materials":
            materials.remove(material)

    # # * "Area" Assets are currently bugged
    # For manibot, these usually refer to lights
    for asset in assets.copy():
        if "Area" in asset.GetPath().elementString:
            assets.remove(asset)

    return assets, materials


def _create_materials(materials: list[Usd.Prim]) -> None:
    """Creates materials in the new scene from the given list.

    Args:
        materials (list[Usd.Prim]): List with references to materials from the source scene to be created in the new scene.
    """
    for material in materials:
        BlenderAsset.copy_materials(
            source_prim=material, target_prim_path=Sdf.Path("/World")
        )


def _parse_asset_config(
    assets: list[Usd.Prim],
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
    Usd.Prim,
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
        Usd.Prim,
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
                if fnmatch.fnmatch(asset.GetName(), pattern.replace(".", "*") + "*"):
                    asset_cfg[asset]["rigid_body_behavior"] = "static"
        if dynamic_assets is not None:
            for pattern in dynamic_assets:
                if fnmatch.fnmatch(asset.GetName(), pattern.replace(".", "*") + "*"):
                    asset_cfg[asset]["rigid_body_behavior"] = "dynamic"

        # parse collisions
        if asset_collision_approximation_method is not None:
            for pattern, method in asset_collision_approximation_method.items():
                if fnmatch.fnmatch(asset.GetName(), pattern.replace(".", "*") + "*"):
                    asset_cfg[asset]["collision_approximation_method"] = method

    return asset_cfg
