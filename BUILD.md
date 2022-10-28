# Bulding the executable
In order to provide a simple way of running the spectator without having to install Python, releases as standalone executables can be found under [releases](https://github.com/cetteup/BF2AutoSpectator/releases).

## Prerequisites
Make you sure you have all dependencies (see `requirements.txt`) as well as [pyinstaller](https://www.pyinstaller.org/) and [pyinstaller-versionfile](https://pypi.org/project/pyinstaller-versionfile/) installed, before you run the build command.

## Build command
First, generate a version file.

```commandline
create-version-file.exe versionfile.yaml --outfile versionfile
```

Then, run the following command to build the executable.

```commandline
pyinstaller.exe .\BF2AutoSpectator\spectate.py --onefile --clean --name="BF2AutoSpectator" --add-data="pickle/*.pickle;pickle/" --add-data="redist/*.exe;redist/" --version-file="versionfile"
```

This will create a `BF2AutoSpectator.exe` in `.\dist`.