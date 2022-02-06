# Bulding the executable
In order to provide a simple way of running the spectator without having to install Python, releases as standalone executables can be found under [releases](https://github.com/cetteup/bf2-auto-spectator/releases).

## Prerequisites
Make you sure you have all dependencies (see `requirements.txt`) as well as [pyinstaller](https://www.pyinstaller.org/) installed, before you run the build command.

## Build command
Run the following command to build the standalone executable.

```commandline
pyinstaller.exe .\src\main.py --onefile --clean --name="bf2-auto-spectator-standalone" --add-data="pickle/*.pickle;pickle/"
```

This will create a `bf2-auto-spectator-standalone.exe` in `.\dist`.