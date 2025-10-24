from isaacsim.core.utils.stage import get_current_stage  # type: ignore
import isaacsim.core.utils.prims as prim_utils  # type: ignore
from pxr import Usd, UsdGeom, UsdShade, Sdf  # type: ignore


class ShadeUtils:
    @classmethod
    def create_material(
        cls, source_material: Usd.Prim, target_prim_path: Sdf.Path
    ) -> UsdShade.Material:
        """Copies the material from the source to the newly created scene at the provided target prim path.

        Args:
            source_prim_path (Sdf.Path): Source Path holding the material.
            target_prim_path (Sdf.Path): Target path we want to copy the materials into.

        Raises:
            ValueError: Raised when the structure of the source does not match the expected structure.

        Returns:
            UsdShade.Material: Newly created materials.
        """
        # # * In the beginning, source_prim is the root folder '_materials'
        # if source_prim.GetName() != "_materials":
        #     raise ValueError(
        #         f"copy_materials expects source prim to be root material folder called '_materials', instead got {source_prim}."
        #     )

        # * Create scope for materials:
        material_root_path = Sdf.Path(f"{target_prim_path}/materials")
        materials_root = UsdGeom.Scope.Define(get_current_stage(), material_root_path)

        material = source_material
        mtl_path = Sdf.Path(f"{material_root_path}/{material.GetName()}")
        mtl = UsdShade.Material.Define(get_current_stage(), mtl_path)

        shaders: list[UsdShade.Shader] = material.GetAllChildren()

        input_queue = {}

        new_shaders = []

        for _shader in shaders:
            shader = UsdShade.Shader(_shader)
            if shader.GetIdAttr().Get() == "UsdPreviewSurface":
                new_shader, inputs = ShadeUtils.create_bsdf_shader(mtl_path, shader)
                mtl.CreateSurfaceOutput().ConnectToSource(
                    new_shader.ConnectableAPI(), "surface"
                )
            elif shader.GetIdAttr().Get() == "UsdUVTexture":
                new_shader, inputs = ShadeUtils.create_image_texture_shader(
                    mtl_path, shader
                )
            elif shader.GetIdAttr().Get() == "UsdPrimvarReader_float2":
                new_shader, inputs = ShadeUtils.create_uvmap_shader(mtl_path, shader)
            else:
                raise ValueError(
                    f"Shader type '{shader.GetIdAttr().Get()}' is unknown."
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

        return mtl

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
