import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

# Directory Paths
ROOT_DIR = Path(__file__).parent.resolve().parent
CYCLES_DIR = ROOT_DIR / "cycles"
TARGET_DSO_DIR = ROOT_DIR / "houdini" / "dso"
SOURCE_DSO_DIR = CYCLES_DIR / "install" / "houdini" / "dso"
OPTIX_ROOT_DIR = os.getenv("OPTIX_ROOT", Path("C:/ProgramData/NVIDIA Corporation/OptiX SDK 9.0.0"))
CUDA_ROOT_DIR = os.getenv("CUDA_ROOT", Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.9"))

# Terminal Color Codes
try:
    os.system("")
    HIGHLIGHT = "\033[44m"
    SUCCESS = "\033[32m"
    ALL_DONE = "\033[92m"
    ERROR = "\033[91m"
    RESET = "\033[0m"
except Exception:
    HIGHLIGHT = ""
    SUCCESS = ""
    ALL_DONE = ""
    ERROR = ""
    RESET = ""


def strpath(path):
    return str(path).replace("\\", "/")


def printSuccess(msg="    ...Done."):
    print(f"{SUCCESS}{msg}{RESET}")


def printError(msg):
    print(f"{ERROR}{msg}{RESET}")


def runCommand(cmd, cwd, step_name):
    """
    Helper function to run a subprocess.
    It prints error messages and exits on failure.
    """
    try:
        # Run the command
        # check=True will raise CalledProcessError if the command returns non-zero
        print(f"    Running: {' '.join(map(str, cmd))}")
        subprocess.run(cmd, cwd=cwd, check=True, text=True)

    except subprocess.CalledProcessError as e:
        printError(f"    ERROR: {step_name} failed.")
        # Join command list into a string for readable output
        printError(f"    Command was: {' '.join(map(str, cmd))}")
        if e.stdout:
            printError(f"    STDOUT:\n{e.stdout}")
        if e.stderr:
            printError(f"    STDERR:\n{e.stderr}")
        sys.exit(1)

    except FileNotFoundError:
        printError(f"    ERROR: Command not found: {cmd[0]}\n")
        sys.exit(1)

    printSuccess()


def copyBuildFiles():
    """
    Copy files from cycles/install/houdini/dso to houdini/dso
    """

    try:
        if TARGET_DSO_DIR.exists():
            print(f"    Removing old directory: {TARGET_DSO_DIR}")
            shutil.rmtree(TARGET_DSO_DIR)

        TARGET_DSO_DIR.mkdir(parents=True, exist_ok=True)

        print(f"    Copying files from: {SOURCE_DSO_DIR}")
        shutil.copytree(SOURCE_DSO_DIR, TARGET_DSO_DIR, dirs_exist_ok=True)

    except Exception as e:
        printError("ERROR: Failed to copy build files.")
        printError(f"    {e}")
        sys.exit(1)

    printSuccess()


def runBuildProcess(buildConfig, houdiniRoot):
    stepCnt = 5
    curStep = 0

    def _step(msg):
        nonlocal curStep
        curStep += 1
        print(f"\n{HIGHLIGHT}[{curStep}/{stepCnt}] {msg}{RESET}")

    print(f"{HIGHLIGHT}--- Building Cycles ({buildConfig}) ---{RESET}\n")

    if not os.path.exists(houdiniRoot):
        printError(f"ERROR: Houdini root path does not exist: {houdiniRoot}")
        sys.exit(1)

    _step("Downloading Precompiled Libraries")
    runCommand(
        [sys.executable, "src/cmake/make_update.py"],
        cwd=CYCLES_DIR,
        step_name="Update Cycles source",
    )

    _step("Configuring build with CMake")
    runCommand(
        [
            "cmake",
            "-B",
            "./build",  # Build directory relative to CYCLES_DIR
            f"-DHOUDINI_ROOT={houdiniRoot}",
            f"-DCMAKE_BUILD_TYPE={buildConfig}",
            "-DWITH_CYCLES_OSL=OFF",
            "-DWITH_CYCLES_ALEMBIC=OFF",
            "-DWITH_CYCLES_DEVICE_CUDA=ON",
            "-DWITH_CYCLES_DEVICE_OPTIX=ON",
            "-DWITH_CYCLES_CUDA_BINARIES=ON",
            "-DCYCLES_CUDA_BINARIES_ARCH=sm_75;sm_86;sm_89;sm_120",
            "-DOPTIX_ROOT_DIR=" + strpath(OPTIX_ROOT_DIR),
            "-DCYCLES_RUNTIME_OPTIX_ROOT_DIR=" + strpath(OPTIX_ROOT_DIR),
            "-DCUDA_TOOLKIT_ROOT_DIR=" + strpath(CUDA_ROOT_DIR),
            "-DOPTIX_INCLUDE_DIR=" + strpath(OPTIX_ROOT_DIR / "include"),
        ],
        cwd=CYCLES_DIR,
        step_name="CMake configuration",
    )

    _step("Building Cycles")
    runCommand(
        [
            "cmake",
            "--build",
            "./build",  # Relative to CYCLES_DIR
            "--config",
            buildConfig,
            "--target",
            "install",
        ],
        cwd=CYCLES_DIR,
        step_name="Build",
    )

    _step("Copying built files to Houdini directory")
    copyBuildFiles()

    _step("Creating cycles.json package file")
    with open(ROOT_DIR / "cycles.json", "w") as f:
        json.dump({"hpath": str(ROOT_DIR / "houdini")}, f, indent=4)
    printSuccess()

    print(f"\n{ALL_DONE}--- Build completed successfully! ---{RESET}\n")


def main():
    if len(sys.argv) != 3:
        printError("Usage: build.py <Release|RelWithDebInfo> <HoudiniRootPath>")
        sys.exit(1)
    try:
        runBuildProcess(sys.argv[1], sys.argv[2])
    except Exception as e:
        printError("ERROR: An unexpected error occurred during the build process.")
        printError(f"    {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
