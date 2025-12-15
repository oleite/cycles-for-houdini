# Cycles for Houdini

Simple scripts for integrating the Cycles Hydra Delegate into Houdini.
Experimental and work-in-progress.

## Windows Build

1. Install the required tools using [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/):
```sh
winget install -e --id t.VisualStudio.2022.Community --override "add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended"
winget install -e --id Kitware.CMake
winget install -e --id Python.Python.3.11
winget install -e --id Git.Git
```

2. Clone the repository with submodules:
```sh
git clone --recurse-submodules https://github.com/oleite/cycles-for-houdini.git
cd cycles-for-houdini
```

3. Run the build script, specifying the build configuration (Release or RelWithDebInfo) and the Houdini installation path:
```sh
python scripts/build.py Release "C:\Program Files\Side Effects Software\Houdini 21.0.512"
``` 

4. Copy the `cycles.json` file to your `Documents/houdini21.0/packages/` folder.

5. Done! Cycles should now be available within Houdini Solaris.

### GPU Support (CUDA / OptiX)

1. Install the [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit-archive) (tested with 12.9);
2. Set the `CUDA_ROOT` environment variable to point to your CUDA installation (default: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9`);
3. Install the [NVIDIA OptiX SDK](https://developer.nvidia.com/optix/downloads) (tested with 9.0.0);
4. Set the `OPTIX_ROOT` environment variable to point to your OptiX installation (default: `C:\ProgramData\NVIDIA Corporation\OptiX SDK 9.0.0`);
5. Re-run the build script as described above.

## Generating Shader HDAs

1. Generate the shader description file with the `cycles.exe --list-nodes cycles_nodes.yaml` command;

2. Place the generated `cycles_nodes.yaml` file in the `scripts/` folder;

3. set the `HFS` and `HHP` environment variables to point to your Houdini installation and its Python libraries, then run the `cycles2hda.py` script:

```sh
set HFS=C:\Program Files\Side Effects Software\Houdini 21.0.512
set HHP=%HFS%\houdini\python3.11libs
python scripts/cycles2hda.py
```

4. Done. The generated HDAs will be placed in the `houdini/otls` folder.

## Notes

- Only tested on Windows with Visual Studio 2022 and Houdini 21.0.512;
- Houdini 21 now targets VFX Platform CY2025, so usage of legacy libraries is disabled;
- OSL and Alembic support is disabled because of dependency issues;
- Debugging with RelWithDebInfo works fine, but Debug builds are not supported due to missing debug versions of some dependencies.
