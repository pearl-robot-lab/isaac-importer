from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from isaacsim.core.utils.stage import get_current_stage  # type: ignore
from isaaclab.sim import schemas
from pxr import Usd, Sdf, UsdGeom, Gf  # type: ignore
import carb  # type: ignore


if TYPE_CHECKING:
    from models.custom_asset.custom_asset_spawner_cfg import CustomAssetSpawnerCfg


class XformUtils:
    @classmethod
    def spawn_xform(
        cls,
        source_prim: Usd.Prim,
        target_prim_path: Sdf.Path,
        cfg: Optional[CustomAssetSpawnerCfg],
    ) -> UsdGeom.Xform:
        # * Define new xform with the same name as source_prim
        new_xform = UsdGeom.Xform.Define(get_current_stage(), target_prim_path)

        if cfg is None:
            XformUtils.copy_xform_attributes(
                xform_source_prim=source_prim,
                xform_target=new_xform,
            )
        else:
            XformUtils.copy_xform_attributes(
                xform_source_prim=source_prim,
                xform_target=new_xform,
                external_scale=cfg.scale,
            )

        # ? Copy all atributes or just the transforms?

        if cfg is None:
            # Cfg will be None for nested Xforms
            return new_xform

        # * Apply Physics and what not
        # note: in case of deformable objects, we need to apply the deformable properties to the mesh prim.
        #   this is different from rigid objects where we apply the properties to the parent prim.
        if cfg.deformable_props is not None:
            # apply mass properties
            if cfg.mass_props is not None:
                schemas.define_mass_properties(
                    new_xform.GetPrim().GetPrimPath(), cfg.mass_props
                )
            # apply deformable body properties
            schemas.define_deformable_body_properties(
                new_xform.GetPrim().GetPrimPath(), cfg.deformable_props
            )

        # # apply visual material
        # if cfg.visual_material is not None:
        #     if not cfg.visual_material_path.startswith("/"):
        #         material_path = f"{geom_prim_path}/{cfg.visual_material_path}"
        #     else:
        #         material_path = cfg.visual_material_path
        #     # create material
        #     cfg.visual_material.func(material_path, cfg.visual_material)
        #     # apply material
        #     bind_visual_material(mesh_prim_path, material_path)

        # TODO:
        # # apply physics material
        # if cfg.physics_material is not None:
        #     if not cfg.physics_material_path.startswith("/"):
        #         material_path = f"{geom_prim_path}/{cfg.physics_material_path}"
        #     else:
        #         material_path = cfg.physics_material_path
        #     # create material
        #     cfg.physics_material.func(material_path, cfg.physics_material)
        #     # apply material
        #     bind_physics_material(mesh_prim_path, material_path)

        # note: we apply the rigid properties to the parent prim in case of rigid objects.
        # if cfg.rigid_props is not None:
        #     # apply mass properties
        #     if cfg.mass_props is not None:
        #         schemas.define_mass_properties(new_prim_path, cfg.mass_props)
        #     # apply rigid properties
        #     schemas.define_rigid_body_properties(new_prim_path, cfg.rigid_props)

        if cfg.rigid_props is not None:
            # apply mass properties
            if cfg.mass_props is not None:
                schemas.define_mass_properties(
                    new_xform.GetPrim().GetPrimPath(), cfg.mass_props
                )
            # apply rigid properties
            schemas.define_rigid_body_properties(
                new_xform.GetPrim().GetPrimPath(), cfg.rigid_props
            )

        Usd.ModelAPI(new_xform).SetKind("component")
        return new_xform

    @classmethod
    def copy_xform_attributes(
        cls,
        xform_source_prim: Usd.Prim,
        xform_target: UsdGeom.Xform,
        external_scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        # xform_source = UsdGeom.Xform(xform_source_prim)
        applied_api_schemas = xform_source_prim.GetPrimTypeInfo().GetAppliedAPISchemas()
        if len(applied_api_schemas) > 0:
            carb.log_warn(
                f"The following APIs will not be applied to asset '{xform_source_prim.GetName()}':\n{applied_api_schemas}"
            )
        if (
            translate := xform_source_prim.GetAttribute("xformOp:translate").Get()  # type: ignore
        ) is not None:
            translate = Gf.Vec3f(
                translate[0] * external_scale[0],
                translate[1] * external_scale[1],
                translate[2] * external_scale[2],
            )
            xform_target.AddTranslateOp().Set(translate)  # type: ignore
        if (
            rotate := xform_source_prim.GetAttribute("xformOp:rotateXYZ").Get()  # type: ignore
        ) is not None:
            xform_target.AddRotateXYZOp().Set(rotate)  # type: ignore
        if (
            scale := xform_source_prim.GetAttribute("xformOp:scale").Get()  # type: ignore
        ) is not None:
            scale = Gf.Vec3f(
                scale[0] * external_scale[0],
                scale[1] * external_scale[1],
                scale[2] * external_scale[2],
            )
            xform_target.AddScaleOp().Set(scale)  # type: ignore
        # TODO: What about order?
