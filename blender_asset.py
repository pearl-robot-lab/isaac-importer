"""
The `BlenderAsset` class holds functions to copy an asset from a reference prim to a newly created prim in the final scene. It copies information such as translation, orientation and scale, copies the mesh from the source to a newly created mesh and copies GeomSubsets.
"""

from __future__ import annotations
from abc import ABC
from typing import Any, TYPE_CHECKING
from isaacsim.core.utils.stage import get_current_stage
import isaacsim.core.utils.prims as prim_utils

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

from isaaclab.sim import schemas

from isaaclab.sim.utils import clone

if TYPE_CHECKING:
    from blender_asset_cfg import BlenderAssetCfg


@clone
def spawn_asset(
    prim_path: str,
    cfg: BlenderAssetCfg,
    translation: tuple[float, float, float] | None = None,
    orientation: tuple[float, float, float, float] | None = None,
) -> Usd.Prim:
    """_summary_

    Args:
        prim_path (str): Path at which we want to spawn the asset in the scene.
        cfg (BlenderAssetCfg): Configuration for the given asset we want to spawn.
        translation (tuple[float, float, float] | None, optional): Unused. Defaults to None.
        orientation (tuple[float, float, float, float] | None, optional): Unused. Defaults to None.

    Returns:
        Usd.Prim: _description_
    """
    if not prim_utils.is_prim_path_valid(prim_path):
        prim = prim_utils.create_prim(
            prim_path,
            prim_type="Xform",
            translation=None,
            orientation=None,
            scale=None,
        )
        xform = UsdGeom.Xform(prim)
        scale_op = list(
            filter(
                lambda x: x.GetOpType() == UsdGeom.XformOp.TypeScale,
                xform.GetOrderedXformOps(),
            )
        )[0]

        scale_op.Set(Gf.Vec3d(*cfg.scale))
    # else:
    #     raise ValueError(f"A prim already exists at path: '{prim_path}'.")

    BlenderAsset.copy_blender_asset(target_prim_path=str(prim_path), cfg=cfg)
    return prim_utils.get_prim_at_path(prim_path)


class BlenderAsset(ABC):

    reference_stage = None
    reference_prim = None

    @classmethod
    def copy_blender_asset(cls, target_prim_path: str, cfg: BlenderAssetCfg) -> None:
        """Accesses the references in the source scene and copies them into the new scene.

        Args:
            target_prim_path (str): Path at which we want to spawn the new asset.
            cfg (BlenderAssetCfg): Configuration for the asset we want to spawn.

        Raises:
            RuntimeError: Reference stage cannot be None.
            RuntimeError: When more than one environment gets loaded, the prim references and the reference stage will no longer match, causing invalid null prims.
        """
        # * Get prims from reference stage.
        if BlenderAsset.reference_stage is None or BlenderAsset.reference_prim is None:
            raise RuntimeError("References cannot be None!")
        xform_source: Usd.Prim = BlenderAsset.reference_stage.GetPrimAtPath(
            cfg.xform_source
        )
        mesh_source: Usd.Prim = BlenderAsset.reference_stage.GetPrimAtPath(
            cfg.mesh_source
        )
        if not xform_source.IsValid() or not xform_source.IsValid():
            raise RuntimeError(
                "Source Prims could not be found. Maybe you imported more than one environment? In this case, the stge get's unloaded and filled with different assets, leading to the prim not existing!"
            )

        # * Copy the asset
        new_xform, new_mesh = BlenderAsset.copy_asset(
            xform_source=xform_source,
            mesh_source=mesh_source,
            target_prim_path=target_prim_path,
            cfg=cfg,
        )

        # * Apply materials to the asset.
        applied_api_schemas = mesh_source.GetPrimTypeInfo().GetAppliedAPISchemas()
        if "MaterialBindingAPI" in applied_api_schemas:
            orig_material_binding_api = UsdShade.MaterialBindingAPI(mesh_source)
            mat, rel = orig_material_binding_api.ComputeBoundMaterial()  # type: ignore
            target: Sdf.Path = rel.GetTargets()[0]

            materials = (
                get_current_stage().GetPrimAtPath("/World/materials").GetAllChildren()
            )

            new_material_binding_api = UsdShade.MaterialBindingAPI.Apply(
                new_mesh.GetPrim()
            )
            material = list(
                filter(
                    lambda mat: mat.GetPath().elementString == target.elementString,
                    materials,
                )
            )[0]
            new_material_binding_api.Bind(UsdShade.Material(material))

        new_mesh.GetPrim().SetMetadata("instanceable", False)
        Usd.ModelAPI(new_xform).SetKind("component")

        # UsdPhysics.DriveAPI.Apply(new_xform.GetPrim())

    @classmethod
    def copy_asset(
        cls,
        xform_source: Usd.Prim,
        mesh_source: Usd.Prim,
        target_prim_path: str,
        cfg: BlenderAssetCfg,
    ) -> tuple[UsdGeom.Xform, UsdGeom.Mesh]:
        """Creates a new Xform and a new Mesh based on the source prim. Applies all relevant APIs and attributes.

        Args:
            xform_source (Usd.Prim): Source Prim from the input scene.
            mesh_source (Usd.Prim): Source Mesh from the input scene.
            target_prim_path (str): Target path to spawn Prim in
            cfg (BlenderAssetCfg): Configuration for the new asset

        Raises:
            ValueError: Raised when the Mesh has other children than a GeomSubset. Those types are not supported yet.

        Returns:
            tuple[UsdGeom.Xform, UsdGeom.Mesh]: The newly created Prim and the corresponding Mesh.
        """
        orig_mesh_prim: Usd.Prim = mesh_source
        # * Define new asset with the same name as source_prim
        new_prim_path = f"{target_prim_path}/{xform_source.GetName()}"
        new_xform = UsdGeom.Xform.Define(get_current_stage(), new_prim_path)

        # * Apply Transformations to new prim and define order
        new_xform.AddTranslateOp().Set(xform_source.GetAttribute("xformOp:translate").Get())  # type: ignore
        new_xform.AddRotateXYZOp().Set(xform_source.GetAttribute("xformOp:rotateXYZ").Get())  # type: ignore
        new_xform.AddScaleOp().Set(xform_source.GetAttribute("xformOp:scale").Get())  # type: ignore

        # * Then, read the meshes attributes (see code below) and create a new mesh
        mesh_prim_path = Sdf.Path(
            f"{new_prim_path}/{new_xform.GetPrim().GetName()}_{orig_mesh_prim.GetName()}"
        )
        new_mesh: UsdGeom.Mesh = UsdGeom.Mesh.Define(
            get_current_stage(), mesh_prim_path
        )

        BlenderAsset.copy_mesh_attributes(mesh_source=mesh_source, new_mesh=new_mesh)

        # * Copy GeomSubsets
        children = mesh_source.GetAllChildren()
        for child in children:
            if child.IsA(UsdGeom.Subset):
                name = child.GetName()
                geomsubset_path = mesh_prim_path.AppendChild(f"GS{name}")
                new_subset = UsdGeom.Subset.Define(get_current_stage(), geomsubset_path)
                BlenderAsset.copy_geomsubset_attributes(
                    subset_source_prim=child, subset_target=new_subset
                )
            else:
                raise ValueError(f"Type not supported")

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
        elif cfg.collision_props is not None:
            # ! SOURCE: exts/isaacsim.core.prims/isaacsim/core/prims/impl/geometry_prim.py
            # *apply collision approximation to mesh
            # * - ``"boundingCube"``
            #   - Bounding Cube
            #   - An optimally fitting box collider is computed around the mesh
            if cfg.collision_approximation == "bounding_cube":
                collision_approximation = "boundingCube"

            # * - ``"boundingSphere"``
            #   - Bounding Sphere
            #   - A bounding sphere is computed around the mesh and used as a collider
            elif cfg.collision_approximation == "bounding_sphere":
                collision_approximation = "boundingSphere"

            # * - ``"convexDecomposition"``
            #   - Convex Decomposition
            #   - A convex mesh decomposition is performed. This results in a set of convex mesh colliders
            elif cfg.collision_approximation == "convex_decomposition":
                collision_approximation = "convexDecomposition"

            # * - ``"convexHull"``
            #   - Convex Hull
            #   - A convex hull of the mesh is generated and used as the collider
            elif cfg.collision_approximation == "convex_hull":
                collision_approximation = "convexHull"

            # * - ``"meshSimplification"``
            #   - Mesh Simplification
            #   - A mesh simplification step is performed, resulting in a simplified triangle mesh collider
            elif cfg.collision_approximation == "mesh_simplification":
                collision_approximation = "meshSimplification"

            # * - ``"sdf"``
            #   - SDF Mesh
            #   - SDF (Signed-Distance-Field) use high-detail triangle meshes as collision shape
            elif cfg.collision_approximation == "sdf":
                collision_approximation = "sdf"

            # * - ``"sphereFill"``
            #   - Sphere Approximation
            #   - A sphere mesh decomposition is performed. This results in a set of sphere colliders
            elif cfg.collision_approximation == "sphere_approximation":
                collision_approximation = "sphereFill"

            # * - ``"none"``
            #   - Triangle Mesh
            #   - The mesh geometry is used directly as a collider without any approximation
            else:
                collision_approximation = "none"

            mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(new_mesh.GetPrim())  # type: ignore
            mesh_collision_api.GetApproximationAttr().Set(collision_approximation)

            # apply collision properties
            schemas.define_collision_properties(mesh_prim_path, cfg.collision_props)

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

        # * return the asset and the mesh
        return new_xform, new_mesh

    @classmethod
    def copy_mesh_attributes(
        cls, mesh_source: Usd.Prim, new_mesh: UsdGeom.Mesh
    ) -> None:
        """Copies the attributes from the source mesh to the new mesh.

        Args:
            mesh_source (Usd.Prim): Source holding the original mesh
            new_mesh (UsdGeom.Mesh): Newly created mesh we want to copy our information into.
        """
        orig_mesh: UsdGeom.Mesh = UsdGeom.Mesh(mesh_source)

        if (attr := orig_mesh.GetDoubleSidedAttr().Get()) is not None:
            new_mesh.CreateDoubleSidedAttr().Set(attr)  # type: ignore
        if (attr := orig_mesh.GetExtentAttr().Get()) is not None:
            new_mesh.CreateExtentAttr().Set(attr)  # type: ignore
        if (attr := orig_mesh.GetFaceVertexCountsAttr().Get()) is not None:
            new_mesh.CreateFaceVertexCountsAttr().Set(attr)  # type: ignore
        if (attr := orig_mesh.GetFaceVertexIndicesAttr().Get()) is not None:
            new_mesh.CreateFaceVertexIndicesAttr().Set(attr)  # type: ignore
        if (attr := orig_mesh.GetNormalsAttr().Get()) is not None:
            new_mesh.GetNormalsAttr().Set(attr)
        if (attr := orig_mesh.GetPointsAttr().Get()) is not None:
            new_mesh.GetPointsAttr().Set(attr)
        if (attr := orig_mesh.GetSubdivisionSchemeAttr().Get()) is not None:
            new_mesh.GetSubdivisionSchemeAttr().Set(attr)

        # * Apply Primvars api so that we can copy primvars attributes
        orig_primvars_api = UsdGeom.PrimvarsAPI(mesh_source)
        orig_primvars = orig_primvars_api.GetPrimvars()
        # print([pv.GetName() for pv in orig_primvars])
        mesh_primvars_api = UsdGeom.PrimvarsAPI(new_mesh)
        for orig_primvar in orig_primvars:
            name = orig_primvar.GetName()
            typeName = orig_primvar.GetTypeName()
            interpolation = orig_primvar.GetInterpolation()
            elementSize = orig_primvar.GetElementSize()
            new_primvar = mesh_primvars_api.CreatePrimvar(
                name, typeName, interpolation, elementSize
            )
            orig_value = orig_primvar.Get()  # type: ignore
            if orig_value:
                new_primvar.Set(orig_value)  # type: ignore

        # # * Copy normals
        orig_geom_points_based = UsdGeom.PointBased(orig_mesh)
        orig_normals_interpolation = orig_geom_points_based.GetNormalsInterpolation()
        new_point_based_api = UsdGeom.PointBased(new_mesh)
        new_point_based_api.SetNormalsInterpolation(orig_normals_interpolation)

    @classmethod
    def copy_geomsubset_attributes(
        cls, subset_source_prim: Usd.Prim, subset_target: UsdGeom.Subset
    ) -> None:
        """Copies the attributes from the source GeomSubset to the newly created GeomSubset.

        Args:
            subset_source_prim (Usd.Prim): Source holding the original subset
            subset_target (UsdGeom.Subset): Newly created geomsubset we want to copy our information into
        """
        subset_source = UsdGeom.Subset(subset_source_prim)
        # Apply MaterialBindingAPI
        applied_api_schemas = (
            subset_source_prim.GetPrimTypeInfo().GetAppliedAPISchemas()
        )
        if "MaterialBindingAPI" in applied_api_schemas:
            orig_material_binding_api = UsdShade.MaterialBindingAPI(subset_source)
            mat, rel = orig_material_binding_api.ComputeBoundMaterial()  # type: ignore
            target: Sdf.Path = rel.GetTargets()[0]
            # material_target_path = Sdf.Path(f"{material_path}/{target.elementString}")

            materials = (
                get_current_stage().GetPrimAtPath("/World/materials").GetAllChildren()
            )

            new_material_binding_api = UsdShade.MaterialBindingAPI.Apply(
                subset_target.GetPrim()
            )
            material = list(
                filter(
                    lambda mat: mat.GetPath().elementString == target.elementString,
                    materials,
                )
            )[0]
            new_material_binding_api.Bind(UsdShade.Material(material))

        if (element_type := subset_source.GetElementTypeAttr().Get()) is not None:
            subset_target.CreateElementTypeAttr(element_type)  # type: ignore
        if (family_name := subset_source.GetFamilyNameAttr().Get()) is not None:
            subset_target.CreateFamilyNameAttr(family_name)  # type: ignore
        if (indices := subset_source.GetIndicesAttr().Get()) is not None:
            subset_target.CreateIndicesAttr(indices)  # type: ignore

    @classmethod
    def copy_materials(
        cls, source_prim: dict[Usd.Prim, Any], target_prim_path: Sdf.Path
    ) -> list[UsdShade.Material]:
        """Copies the materials from the source to the newly created scene at the provided target prim path.

        Args:
            source_prim (dict[Usd.Prim, Any]): Source holding all of our materials.
            target_prim_path (Sdf.Path): Target path we want to copy the materials into.

        Raises:
            ValueError: Raised when the structure of the source does not match the expected structure.

        Returns:
            list[UsdShade.Material]: List holding the newly created materials.
        """
        # * In the beginning, source_prim is the root folder '_materials'
        if source_prim.GetName() != "_materials":
            raise ValueError(
                f"copy_materials expects source prim to be root material folder called '_materials', instead got {source_prim}."
            )

        # * Create scope for materials:
        material_root_path = Sdf.Path(f"{target_prim_path}/materials")
        materials_root = UsdGeom.Scope.Define(get_current_stage(), material_root_path)

        new_materials = []

        materials: list = source_prim.GetAllChildren()
        for material in materials:
            mtl_path = Sdf.Path(f"{material_root_path}/{material.GetName()}")
            mtl = UsdShade.Material.Define(get_current_stage(), mtl_path)
            new_materials.append(mtl)

            shaders: list[UsdShade.Shader] = material.GetAllChildren()

            input_queue = {}

            new_shaders = []

            for _shader in shaders:
                shader = UsdShade.Shader(_shader)
                if shader.GetIdAttr().Get() == "UsdPreviewSurface":
                    new_shader, inputs = BlenderAsset.create_bsdf_shader(
                        mtl_path, shader
                    )
                    mtl.CreateSurfaceOutput().ConnectToSource(
                        new_shader.ConnectableAPI(), "surface"
                    )
                if shader.GetIdAttr().Get() == "UsdUVTexture":
                    new_shader, inputs = BlenderAsset.create_image_texture_shader(
                        mtl_path, shader
                    )
                if shader.GetIdAttr().Get() == "UsdPrimvarReader_float2":
                    new_shader, inputs = BlenderAsset.create_uvmap_shader(
                        mtl_path, shader
                    )
                new_shaders.append(new_shader)
                for key, value in inputs.items():
                    input_queue[key] = value

            for inpt, source_info in input_queue.items():
                source_path = mtl_path.AppendPath(
                    source_info.source.GetPath().elementString
                )
                source_name = source_info.sourceName
                prm: Usd.Prim = inpt.GetPrim()
                valid = prm.IsValid()
                shader_prim = prim_utils.get_prim_at_path(source_path)
                if shader_prim.IsValid():
                    inpt.ConnectToSource(
                        UsdShade.Shader(shader_prim).ConnectableAPI(), source_name
                    )

        return new_materials

    @classmethod
    def create_bsdf_shader(
        cls, mtl_path: Sdf.Path, orig_bsdf_shader: UsdShade.Shader
    ) -> tuple[UsdShade.Shader, dict]:
        bsdf_shader: UsdShade.Shader = UsdShade.Shader.Define(
            get_current_stage(), mtl_path.AppendPath("Principled_BSDF")
        )
        bsdf_shader.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)  # type: ignore
        bsdf_shader.CreateIdAttr("UsdPreviewSurface")  # type: ignore
        bsdf_shader.GetPrim().GetAttribute("info:implementationSource").Clear()

        input_queue = {}

        for inpt in orig_bsdf_shader.GetInputs(onlyAuthored=False):
            new_input = bsdf_shader.CreateInput(inpt.GetBaseName(), inpt.GetTypeName())
            if inpt.HasConnectedSource():
                source_info = inpt.GetConnectedSources()[0][0]  # type: ignore
                input_queue[new_input] = source_info
            else:
                new_input.Set(orig_bsdf_shader.GetInput(inpt.GetBaseName()).Get())  # type: ignore

        return bsdf_shader, input_queue

    @classmethod
    def create_image_texture_shader(
        cls, mtl_path: Sdf.Path, orig_image_texture_shader: UsdShade.Shader
    ) -> tuple[UsdShade.Shader, dict]:
        texture_shader: UsdShade.Shader = UsdShade.Shader.Define(
            get_current_stage(), mtl_path.AppendPath("Image_Texture")
        )
        texture_shader.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)  # type: ignore
        texture_shader.CreateIdAttr("UsdUVTexture")  # type: ignore
        texture_shader.GetPrim().GetAttribute("info:implementationSource").Clear()

        input_queue = {}

        for inpt in orig_image_texture_shader.GetInputs(onlyAuthored=False):
            new_input = texture_shader.CreateInput(
                inpt.GetBaseName(), inpt.GetTypeName()
            )
            if inpt.HasConnectedSource():
                source_info = inpt.GetConnectedSources()[0][0]  # type: ignore
                input_queue[new_input] = source_info
            else:
                tmp = orig_image_texture_shader.GetInput(inpt.GetBaseName()).Get()  # type: ignore
                if type(tmp) == Sdf.AssetPath:
                    new_input.Set(tmp.resolvedPath)  # type: ignore
                else:
                    new_input.Set(tmp)  # type: ignore

        return texture_shader, input_queue

    @classmethod
    def create_uvmap_shader(
        cls, mtl_path: Sdf.Path, orig_uvmap_shader: UsdShade.Shader
    ) -> tuple[UsdShade.Shader, dict]:
        uvmap_shader: UsdShade.Shader = UsdShade.Shader.Define(
            get_current_stage(), mtl_path.AppendPath("uvmap")
        )
        uvmap_shader.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)  # type: ignore
        uvmap_shader.CreateIdAttr("UsdPrimvarReader_float2")  # type: ignore
        uvmap_shader.GetPrim().GetAttribute("info:implementationSource").Clear()

        input_queue = {}

        for inpt in orig_uvmap_shader.GetInputs(onlyAuthored=False):
            new_input = uvmap_shader.CreateInput(inpt.GetBaseName(), inpt.GetTypeName())
            if inpt.HasConnectedSource():
                source_info = inpt.GetConnectedSources()[0][0]  # type: ignore
                input_queue[new_input] = source_info
            else:
                new_input.Set(orig_uvmap_shader.GetInput(inpt.GetBaseName()).Get())  # type: ignore

        return uvmap_shader, input_queue
