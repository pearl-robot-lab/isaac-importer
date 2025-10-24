from __future__ import annotations
from typing import TYPE_CHECKING

from isaacsim.core.utils.stage import get_current_stage  # type: ignore
from isaaclab.sim import schemas
from pxr import Usd, UsdGeom, UsdShade, UsdPhysics, Sdf  # type: ignore

if TYPE_CHECKING:
    from models.custom_asset.custom_asset_spawner_cfg import CustomAssetSpawnerCfg


class MeshUtils:
    @classmethod
    def spawn_mesh(
        cls,
        source_prim: Usd.Prim,
        target_prim_path: Sdf.Path,
        cfg: CustomAssetSpawnerCfg,
    ) -> UsdGeom.Mesh:
        # * Then, read the meshes attributes (see code below) and create a new mesh
        # mesh_prim_path = Sdf.Path(
        #     f"{new_prim_path}/{new_xform.GetPrim().GetName()}_{orig_mesh_prim.GetName()}"
        # )

        new_mesh: UsdGeom.Mesh = UsdGeom.Mesh.Define(
            get_current_stage(), target_prim_path
        )

        MeshUtils.copy_mesh_attributes(mesh_source=source_prim, new_mesh=new_mesh)

        # * Apply materials to the asset.
        applied_api_schemas = source_prim.GetPrimTypeInfo().GetAppliedAPISchemas()
        if "MaterialBindingAPI" in applied_api_schemas:
            orig_material_binding_api = UsdShade.MaterialBindingAPI(source_prim)
            mat, rel = orig_material_binding_api.ComputeBoundMaterial()  # type: ignore
            target: Sdf.Path = rel.GetTargets()[0]

            # Extract the first 4 elements of the string ("/World/envs/env_.*/<object>")
            constructed_path = "/" + "/".join(
                target_prim_path.pathString.split("/")[1:5]
            )

            xform_prim_path = Sdf.Path(constructed_path)
            materials = (
                get_current_stage()
                .GetPrimAtPath(xform_prim_path.AppendChild("materials"))
                .GetAllChildren()
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

        if cfg.collision_props is not None:
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
            schemas.define_collision_properties(target_prim_path, cfg.collision_props)
        new_mesh.GetPrim().SetMetadata("instanceable", False)
        return new_mesh

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


class SubsetUtils:
    @classmethod
    def spawn_geom_subset(
        cls, source_prim: Usd.Prim, target_prim_path: Sdf.Path
    ) -> UsdGeom.Subset:
        new_subset = UsdGeom.Subset.Define(get_current_stage(), target_prim_path)
        SubsetUtils.copy_geomsubset_attributes(
            subset_source_prim=source_prim, subset_target=new_subset
        )
        return new_subset

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

            target_prim_path = subset_target.GetPath()

            # Extract the first 4 elements of the string ("/World/envs/env_.*/<object>")
            constructed_path = "/" + "/".join(
                target_prim_path.pathString.split("/")[1:5]
            )

            xform_prim_path = Sdf.Path(constructed_path)
            materials = (
                get_current_stage()
                .GetPrimAtPath(xform_prim_path.AppendChild("materials"))
                .GetAllChildren()
            )

            # materials = (
            #     get_current_stage().GetPrimAtPath("/World/materials").GetAllChildren()
            # )

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
