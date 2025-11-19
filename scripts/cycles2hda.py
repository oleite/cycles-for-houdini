import sys
import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve().parent
HDA_PATH = ROOT_DIR / "houdini" / "otls" / "cycles.hda"
CYCLES_NODES_YAML = ROOT_DIR / "scripts" / "cycles_nodes.yaml"


def enableHouModule():
    """
    Set up the environment so that "import hou" works.
    Modified from: https://www.sidefx.com/docs/houdini/hom/commandline.html
    """
    binDir = f"{os.environ['HFS']}/bin"
    os.chdir(binDir)

    if hasattr(sys, "setdlopenflags"):
        old_dlopen_flags = sys.getdlopenflags()
        sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(binDir)
    try:
        import hou
    except ImportError:
        sys.path.append(os.environ["HHP"])
        import hou
    finally:
        if hasattr(sys, "setdlopenflags"):
            sys.setdlopenflags(old_dlopen_flags)


enableHouModule()
import hou
import shaderhda


def _configureSimpleParm(parmTemplate, socketData):
    socketType = socketData["type"]

    if socketType == "color":
        parmTemplate.setLook(hou.parmLook.ColorSquare)
        parmTemplate.setNamingScheme(hou.parmNamingScheme.RGBA)

    defaultvalue = socketData.get("default_value")
    if defaultvalue is not None:
        if isinstance(parmTemplate, hou.ToggleParmTemplate):
            defaultvalue = bool(defaultvalue)
        elif not isinstance(defaultvalue, list):
            defaultvalue = [defaultvalue]
        parmTemplate.setDefaultValue(defaultvalue)

    return parmTemplate


def _parmTemplateFromSocketData(socketData):
    parmClassMap = {
        "int": (hou.IntParmTemplate, 1),
        "uint": (hou.IntParmTemplate, 1),
        "boolean": (hou.ToggleParmTemplate, None),
        "float": (hou.FloatParmTemplate, 1),
        "string": (hou.StringParmTemplate, 1),
        # Vector types
        "vector": (hou.FloatParmTemplate, 3),
        "point": (hou.FloatParmTemplate, 3),
        "color": (hou.FloatParmTemplate, 3),
        "normal": (hou.FloatParmTemplate, 3),
        # Not in the standard library
        "BSDF": (hou.StringParmTemplate, 1),
        "closure": (hou.StringParmTemplate, 1),
    }

    name = socketData["name"]
    label = socketData["ui_name"]

    (parmClass, size) = parmClassMap.get(socketData["type"], (None, None))
    if parmClass:
        if size is None:
            parmTemplate = parmClass(name, label)
        else:
            parmTemplate = parmClass(name, label, size)
        return _configureSimpleParm(parmTemplate, socketData)

    # TODO: Handle more complex types like enums, arrays, etc.

    return None


def _vopTypeFromSocketData(socketData):
    vopTypeMap = {
        "int": "int",
        "uint": "uint",
        "boolean": "int",
        "float": "Float",
        "string": "String",
        "vector": "vector",
        "point": "vector",
        "color": "color",
        "normal": "vector",
        "BSDF": "bsdf",
        "enum": "int",
        "transform": "matrix",
        "closure": {
            "material": "material",
            "surface": "surface",
            "volume": "atmosphere",
            "displacement": "displacement",
            "BSDF": "bsdf",
        },
    }
    socketType = socketData["type"]
    socketName = socketData["name"]

    vopType = vopTypeMap.get(socketType)
    if isinstance(vopType, dict):
        vopType = vopType.get(socketName)

    if not vopType:
        print(
            f"WARNING: Unhandled socket type '{socketType}' for socket '{socketName}'"
        )
        vopType = "string"  # Fallback to string for unknown types

    # TODO: Remove this workaround when we have proper closure support
    if vopType == "bsdf":
        vopType = "surface"

    return vopType


def _shaderParametersFromSocketDataList(sockets, isInput=True):
    result = []
    for socketData in sockets:
        vopType = _vopTypeFromSocketData(socketData)
        if not vopType:
            continue

        result.append(
            shaderhda.ShaderParameter(
                name=socketData["name"],
                vop_type=vopType,
                ui_parm=_parmTemplateFromSocketData(socketData) if isInput else None,
                ui_folder_path="Inputs",
                is_connectable=True,
                extra_infos=None,
            )
        )
    return result


def _submenuFromName(name):
    submenu = "Cycles "
    if "convert" in name:
        submenu += "(Converters)"
    elif "combine" in name or "separate" in name:
        submenu += "(Utilities)"
    elif "bsdf" in name:
        submenu += "(BSDFs)"
    elif "texture" in name or "image" in name:
        submenu += "(Textures)"
    else:
        submenu += "(Others)"
    return submenu


def main(saveExpanded=False):
    try:
        import yaml
    except ImportError:
        print("pyyaml is required to run this script. Please install it via pip.")
        return 1

    with open(CYCLES_NODES_YAML, "r") as f:
        nodes_data = yaml.safe_load(f)

    shadersData = [node for node in nodes_data if node["type"] == "shader"]

    if HDA_PATH.exists():
        HDA_PATH.unlink()
    if not HDA_PATH.parent.exists():
        HDA_PATH.parent.mkdir(parents=True, exist_ok=True)

    totalShaders = len(shadersData)
    for i, data in enumerate(shadersData):

        if data["name"] == "output":
            data["outputs"] = [
                {
                    "name": "material",
                    "ui_name": "Material Output",
                    "type": "closure",
                }
            ]

        name = "cycles_" + data["name"]
        label = name.title().replace("_", " ")
        shaderName = f"cycles:" + data["name"]

        print(f"[{i+1}/{totalShaders}] Creating shader HDA: {name}")

        shader = shaderhda.Shader(name)
        shader.setHdaLabel(label)
        shader.setHdaIcon("BUTTONS_theme_light")
        shader.setShaderName(shaderName)
        shader.setShaderType("generic")
        shader.setRenderMask("cycles")
        shader.setVopnetMask("cycles")
        shader.setTabSubMenus([_submenuFromName(name)])
        shader.setToolKeywords(["cycles", "shader"] + name.lower().split())

        signature = shaderhda.ShaderSignature(
            name=label.replace(
                " ", "_"
            ),  # Can't have spaces nor underscores in signature names
            label=label,
            shader_name=shaderName,
            inputs=_shaderParametersFromSocketDataList(
                data.get("inputs", []), isInput=True
            ),
            outputs=_shaderParametersFromSocketDataList(
                data.get("outputs", []), isInput=False
            ),
        )
        ok, err = shader.signatureSet().addSignature(signature)
        assert ok, (
            'Problem while adding a signature for shader "' + name + '":\n' + err + "\n"
        )
        assert all(
            parm is not None for parm in signature._parameterTypeList()
        ), f"Shader '{name}' has parameters with undefined VOP types."

        shader.signatureSet().sortSignatures()
        shader.signatureSet().setBestDefaultSignature()

        if saveExpanded:
            shader.addHDAToExpandedDir(str(HDA_PATH), True)
        else:
            shader.addHDAToFile(str(HDA_PATH), True)

if __name__ == "__main__":
    sys.exit(main(True))
