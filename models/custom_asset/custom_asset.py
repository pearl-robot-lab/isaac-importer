from __future__ import annotations
from typing import TYPE_CHECKING

from isaaclab.sim.utils import clone
from pxr import Usd, UsdGeom, Sdf  # type: ignore
import carb  # type: ignore

from models.custom_asset.usd_utils import XformUtils
from models.custom_asset.usd_geom_utils import MeshUtils, SubsetUtils
from models.custom_asset.usd_shade_utils import ShadeUtils
from utils.usd_tree import PrimNode

if TYPE_CHECKING:
    from custom_asset_spawner_cfg import CustomAssetSpawnerCfg


@clone
def spawn_asset(
    prim_path: str,
    cfg: CustomAssetSpawnerCfg,
    # TODO: Why are we not considering translation and orientation?
    translation: tuple[float, float, float] | None = None,
    orientation: tuple[float, float, float, float] | None = None,
) -> Usd.Prim:

    # * Check if Prim is still loaded in temporary stage
    source_prim: Usd.Prim = cfg.source_node.prim
    if not source_prim.IsValid():
        raise RuntimeError(
            "Source Prim could not be found. Maybe you imported more than one environment? "
            "In this case, the stage get's unloaded and filled with different assets, "
            "leading to the prim not existing!"
        )
    target_prim_path = Sdf.Path(prim_path)

    # * Create materials for this asset
    materials: list[PrimNode] = cfg.materials
    for material in materials:
        # TODO: Chagen material path to be inside the asset xform?
        # TODO: Couple material path to target prim
        ShadeUtils.create_material(
            source_material=material.prim, target_prim_path=target_prim_path
        )

    # * Spawn Xform to hold the asset
    new_xform = XformUtils.spawn_xform(
        source_prim=source_prim, target_prim_path=target_prim_path, cfg=cfg
    )

    # * Traverse Tree
    spawn_prims_recursive(
        target_prim_path=target_prim_path, prim_nodes=cfg.source_node.children, cfg=cfg
    )

    return new_xform.GetPrim()


def spawn_prims_recursive(
    target_prim_path: Sdf.Path,
    prim_nodes: list[PrimNode],
    cfg: CustomAssetSpawnerCfg,
) -> None:
    """Recursively traverse prim tree and spawn children

    Args:
        target_prim_path (Sdf.Path): _description_
        prim_nodes (list[PrimNode]): _description_
        cfg (BlenderAssetCfg): _description_
    """
    for prim_node in prim_nodes:
        source_prim: Usd.Prim = prim_node.prim

        # * Go over the implemented types of assets and spawn the corresponding one
        if source_prim.IsA(UsdGeom.Xform):
            # Spawn Xform
            _target_prim_path = target_prim_path.AppendChild(
                source_prim.GetName(),
            )
            XformUtils.spawn_xform(
                source_prim=source_prim,
                target_prim_path=_target_prim_path,
                cfg=None,  # cfg is None for nested Xforms
            )
        elif source_prim.IsA(UsdGeom.Mesh):
            # Spawn Mesh
            _target_prim_path = target_prim_path.AppendChild(
                f"MSH_{source_prim.GetName()}",
            )
            MeshUtils.spawn_mesh(
                source_prim=source_prim,
                target_prim_path=_target_prim_path,
                cfg=cfg,
            )
        elif source_prim.IsA(UsdGeom.Subset):
            # Spawn GeomSubset
            _target_prim_path = target_prim_path.AppendChild(
                f"GS_{source_prim.GetName()}",
            )
            SubsetUtils.spawn_geom_subset(
                source_prim=source_prim,
                target_prim_path=_target_prim_path,
            )
        else:
            # raise ValueError(f"'{source_prim.GetTypeName()}' not supported")
            carb.log_warn(f"'{source_prim.GetTypeName()}' not supported")
            continue

        # * Traverse tree
        spawn_prims_recursive(
            target_prim_path=_target_prim_path,
            prim_nodes=prim_node.children,
            cfg=cfg,
        )
