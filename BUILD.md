# Bulding the executable
In order to provide a simple way of running the spectator without having to install Python, releases as standalone executables can be found under [releases](https://github.com/cetteup/bf2-auto-spectator/releases).

## Prerequisites
Make you sure you have all dependencies (see `requirements.txt`) as well as [pyinstaller](https://www.pyinstaller.org/) and [pyinstaller-versionfile](https://pypi.org/project/pyinstaller-versionfile/) installed, before you run the build command.

## Build command
First, generate a version file.

```commandline
create-version-file.exe versionfile.yaml --outfile versionfile
```

Then, run the following command to build the executable.

```commandline
pyinstaller.exe .\src\main.py --onefile --clean --name="bf2-auto-spectator" --add-data="pickle/*.pickle;pickle/" --version-file="versionfile"
```

This will create a `bf2-auto-spectator.exe` in `.\dist`.