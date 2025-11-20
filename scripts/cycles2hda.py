import shutil
import sys
import os
import re
import sys
from pathlib import Path
import fnmatch

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


_SHADERS_SKIP = [
    "output",
]

_SHADER_LABELS_MAP = {
    "scatter_volume": "Volume Scatter",
    "absorption_volume": "Volume Absorption",
    "coefficients_volume": "Volume Coefficients",
}

_SHADER_LABELS_CAPITAL_WORDS = [
    "rgb",
    "bw",
    "bsdf",
    "uv",
    "xyz",
    "hsv",
]

_PARM_CLASS_MAP = {
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
}

_VOP_TYPE_MAP = {
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

_SUBMENUS_MAP = {
    "shader": [
        "*bsdf*",
        "emission",
        "scatter_volume",
        "absorption_volume",
        "coefficients_volume",
        "holdout",
        "add_shader",
        "mix_shader",
    ],
    "input": [
        "*info*",
        "*attribute*",
        "ambient_occlusion",
        "bevel",
        "fresnel",
        "geometry",
        "layer_weight",
        "light_path",
        "tangent",
        "texture_coordinate",
        "uvmap",
        "value",
        "wireframe",
    ],
    "texture": [
        "*texture*",
    ],
    "converter": [
        "*combine*",
        "*separate*",
        "*convert*",
        "blackbody",
        "clamp",
        "color_ramp",
        "float_curve",
        "map_range",
        "math",
        "mix",
        "rgb_to_bw",
        "vector_math",
        "wavelength",
    ],
}

# TODO: Gather these UI-level defaults, organization and min/max values
# from the Blender implementation of Cycles if possible.

_ORDERED_PARM_MAP = {
    "principled_bsdf": [
        {
            "group": "Base",
            "params": [
                "base_color",
                "metallic",
                "roughness",
                "ior",
                "alpha",
                "normal",
            ],
        },
        {
            "group": "Diffuse",
            "params": [
                "diffuse_roughness",
            ],
        },
        {
            "group": "Subsurface",
            "params": [
                "*subsurface*",
            ],
        },
        {
            "group": "Specular",
            "params": [
                "*specular*",
                "*anisotropic*",
            ],
        },
        {
            "group": "Coat",
            "params": [
                "*coat*",
            ],
        },
        {
            "group": "Transmission",
            "params": [
                "*transmission*",
            ],
        },
        {
            "group": "Sheen",
            "params": [
                "*sheen*",
            ],
        },
        {
            "group": "Emission",
            "params": [
                "*emission*",
            ],
        },
        {
            "group": "Thin Film",
            "params": [
                "*thin_film*",
            ],
        },
        {
            "group": "Advanced",
            "params": ["*"],  # Catch-all for any remaining params
        },
    ]
}

# TODO: Use these defaults when creating the parm templates, but in order
# to do that we first need to make sure shadertranslator is promoting ALL
# values from vops to the USD level, otherwise values that are left in
# this new default state will not be applied at all.

_SOCKET_DEFAULTS_OVERRIDES = {
    "principled_bsdf": {
        "ior": 1.45,
        "specular_ior_level": 0.5,
        "subsurface_radius": [1.0, 0.2, 0.1],
        "subsurface_scale": 0.05,
    }
}


def _shaderLabelFromName(name):
    label = _SHADER_LABELS_MAP.get(name)
    if label:
        return label

    label = name.title().replace("_", " ")
    for token in _SHADER_LABELS_CAPITAL_WORDS:
        pattern = re.compile(r"\b" + re.escape(token) + r"\b", re.IGNORECASE)
        label = pattern.sub(token.upper(), label)

    # Not sure if this is a correct assumption yet, but for now:
    label = label.replace("Closure", "Shader")

    return label


def _configureSimpleParm(parmTemplate, socketData):
    socketType = socketData["type"]

    if socketType == "color":
        parmTemplate.setLook(hou.parmLook.ColorSquare)
        parmTemplate.setNamingScheme(hou.parmNamingScheme.RGBA)

    # defaultvalue = socketData.get("default_value")

    defaultValue = socketData.get("default_value")
    if defaultValue is not None:
        if isinstance(parmTemplate, hou.ToggleParmTemplate):
            defaultValue = bool(defaultValue)
        elif not isinstance(defaultValue, list):
            defaultValue = [defaultValue]
        parmTemplate.setDefaultValue(defaultValue)

    if socketData.get("internal"):
        parmTemplate.hide(True)

    return parmTemplate


def _parmTemplateFromSocketData(socketData):
    name = socketData["name"]
    label = socketData["ui_name"]

    (parmClass, size) = _PARM_CLASS_MAP.get(socketData["type"], (None, None))
    if parmClass:
        if size is None:
            parmTemplate = parmClass(name, label)
        else:
            parmTemplate = parmClass(name, label, size)
        return _configureSimpleParm(parmTemplate, socketData)

    # TODO: Handle more complex types like enums, arrays, etc.

    return None


def _sortSockets(sockets, shaderName):
    orderedParms = _ORDERED_PARM_MAP.get(shaderName) or []
    sortedSockets = []
    for group in orderedParms:
        for pattern in group["params"]:
            for socketData in sockets:
                if fnmatch.fnmatch(socketData["name"], pattern):
                    if socketData not in sortedSockets:
                        sortedSockets.append(socketData)

    for socketData in sorted(sockets, key=lambda s: s["name"]):
        if socketData not in sortedSockets:
            sortedSockets.append(socketData)

    return sortedSockets


def _folderPathFromSocketData(socketData, shaderName):
    orderedParms = _ORDERED_PARM_MAP.get(shaderName) or []
    for group in orderedParms:
        for pattern in group["params"]:
            if fnmatch.fnmatch(socketData["name"], pattern):
                return group["group"]
    return None


def _vopTypeFromSocketData(socketData):
    socketType = socketData["type"]
    socketName = socketData["name"]

    vopType = _VOP_TYPE_MAP.get(socketType)
    if isinstance(vopType, dict):
        vopType = vopType.get(socketName)

    if not vopType:
        print(
            f"WARNING: Unhandled socket type '{socketType}' for socket '{socketName}'"
        )
        vopType = "bsdf"

    if vopType == "bsdf":
        # Assume surface for now
        vopType = "surface"

    return vopType


def _shaderParametersFromSocketDataList(sockets, shaderName, isInput):
    result = []

    for socketData in _sortSockets(sockets, shaderName):
        vopType = _vopTypeFromSocketData(socketData)
        if not vopType:
            continue

        folderPath = _folderPathFromSocketData(socketData, shaderName)
        if folderPath:
            # Remove folder path from ui_name, to avoid "Subsurface / Subsurface Color" kind of names
            socketData["ui_name"] = (
                socketData["ui_name"].replace(folderPath, "").strip()
            )

        result.append(
            shaderhda.ShaderParameter(
                name=socketData["name"],
                vop_type=vopType,
                ui_parm=(
                    _parmTemplateFromSocketData(socketData)
                    if isInput
                    else None
                ),
                ui_folder_path=folderPath,
                is_connectable=socketData["linkable"] and not socketData["internal"],
                extra_infos=None,
            )
        )
    return result


def _submenuFromName(name):
    for groupName, patterns in _SUBMENUS_MAP.items():
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern):
                return f"Cycles ({groupName.title()})"
    return "Cycles (Other)"


def main(saveExpanded=False):
    try:
        import yaml
    except ImportError:
        print("pyyaml is required to run this script. Please install it via pip.")
        return 1

    with open(CYCLES_NODES_YAML, "r") as f:
        nodes_data = yaml.safe_load(f)

    shadersData = [node for node in nodes_data if node["type"] == "shader"]

    if HDA_PATH.is_dir():
        shutil.rmtree(HDA_PATH)
    elif HDA_PATH.exists():
        HDA_PATH.unlink()
    if not HDA_PATH.parent.exists():
        HDA_PATH.parent.mkdir(parents=True, exist_ok=True)

    totalShaders = len(shadersData)
    for i, data in enumerate(shadersData):

        if data["name"] in _SHADERS_SKIP:
            continue

        hdaName = "cycles_" + data["name"]
        hdaLabel = "Cycles " + _shaderLabelFromName(data["name"])
        shaderName = f"cycles:" + data["name"]
        signatureName = hdaName.title().replace("_", "")

        print(f"[{i+1}/{totalShaders}] {hdaLabel} ({hdaName})")

        shader = shaderhda.Shader(hdaName)
        shader.setHdaLabel(hdaLabel)
        shader.setHdaIcon("BUTTONS_theme_light")
        shader.setShaderName(shaderName)
        shader.setShaderType("generic")
        shader.setRenderMask("cycles")
        shader.setVopnetMask("cycles")
        shader.setTabSubMenus([_submenuFromName(hdaName)])
        shader.setToolKeywords(["cycles", "shader"] + hdaName.lower().split())

        signature = shaderhda.ShaderSignature(
            name=signatureName,
            label=hdaLabel,
            shader_name=shaderName,
            inputs=_shaderParametersFromSocketDataList(
                data.get("inputs", []), shaderName=data["name"], isInput=True
            ),
            outputs=_shaderParametersFromSocketDataList(
                data.get("outputs", []), shaderName=data["name"], isInput=False
            ),
        )
        ok, err = shader.signatureSet().addSignature(signature)
        assert ok, f'Problem while adding a signature for shader "{hdaName}":\n{err}\n'
        assert all(
            parm is not None for parm in signature._parameterTypeList()
        ), f"Shader '{hdaName}' has parameters with undefined VOP types."

        shader.signatureSet().sortSignatures()
        shader.signatureSet().setBestDefaultSignature()

        if saveExpanded:
            shader.addHDAToExpandedDir(str(HDA_PATH), True)
        else:
            shader.addHDAToFile(str(HDA_PATH), True)


if __name__ == "__main__":
    sys.exit(main(True))
