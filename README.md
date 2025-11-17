# Cycles for Houdini

Simple scripts for integrating the Cycles Hydra Delegate into Houdini.


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

## Notes

- Only tested on Windows with Visual Studio 2022 and Houdini 21.0.512;
- Houdini 21 now targets VFX Platform CY2025, so usage of legacy libraries is disabled;
- OSL and Alembic support is disabled because of dependency issues;
- Debugging with RelWithDebInfo works fine, but Debug builds are not supported due to missing debug versions of some dependencies.
