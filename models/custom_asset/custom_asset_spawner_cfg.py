from typing import Callable, Literal
from dataclasses import MISSING

import isaaclab.sim as sim_utils
from isaaclab.utils import configclass
from pxr import Usd  # type: ignore

from models.custom_asset.custom_asset import spawn_asset
from utils.usd_tree import PrimNode


@configclass
class CustomAssetSpawnerCfg(sim_utils.MeshCfg):

    func: Callable = spawn_asset

    source_node: PrimNode = MISSING  # type: ignore

    materials: list[PrimNode] = MISSING  # type: ignore

    scale: tuple[float, float, float] = MISSING  # type: ignore

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
