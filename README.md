# bf2-auto-spectator
An automated spectator for Battlefield 2 written in Python 🐍

Battefield 2 might be an old game that is known for sometimes having more dust than hit registration. But it's still around after 15 years and people still play it. So, why not support this game and community with an automated spectator that makes it easy to, for example, stream this game around the clock so people can (re-)discover it via a [live stream](https://twitch.tv/allidoisspectate).

## Project state
The goal is to provide a fully automated, fire-and-forget spectator for the game. However, this project is currently in an alpha-like state. *Thus, some monitoring of the spectator and any live stream is strongly recommended.*

## Features
- automatic start of a BF2 game instance (can be disabled to attach to an existing instance)
- automatic account login
- automatic server join (only by server ip; custom ports and server passwords are supported)
- automatic spawning in game to enable "spectator mode" (see supported maps/sizes below)
- automatic rotation between players of spectator's team
- in game error detection and handling
- game freeze detection and handling

## Command line arguments
Argument|Description|Default|Required
--------|-----------|-------|--------
`--version`|Output version information
`--player-name`|Name of bf2hub account|None|Yes
`--player-password`|Passwort for bf2hub account|None|Yes
`--server-ip`|IP of server to join|None|Yes
`--server-port`|Port of server to join|16567|No
`--server-pass`|Passwort for server to join|None|No
`--game-path`|Path to BF2 install folder|C:\Program Files (x86)\EA Games\Battlefield 2\ |No
`--tesseract-path`|Path to Tesseract install folder|C:\Program Files\Tesseract-OCR\ |No
`--no-start`|Do not start a new game instance (use existing)
`--debug-log`|Add debugging information to log output
`--debug-screenshot`|Write any screenshots to disk for debugging

You can always get these details locally by providing the `--help` argument.

## Supported maps for auto-spawning
Map name|16 size|32 size|64 size
--------|-------|-------|-------
Dalian Plant|No|No|Yes
Daqing Oilfields|No|No|Yes
Dragon Valley|No|No|Yes
FuShe Pass|No|No|Yes
Great Wall|No|Yes|n/a
Gulf of Oman|Yes|No|Yes
Highway Tampa|No|No|Yes
Kubra Dam|No|No|Yes
Mashtuur City|Yes|No|Yes
Midnight Sun|No|No|Yes
Operation Blue Pearl|No|No|Yes
Operation Clean Sweep|No|No|Yes
Operation Harvest|No|No|Yes
Operation Road Rage|No|No|Yes
Operation Smoke Screen|No|No|Yes
Road to Jalalabad|Yes|No|Yes
Sharqi Peninsula|Yes|No|Yes
Songhua Stalemate|No|No|Yes
Strike at Karkand|Yes|No|Yes
Taraba Quarry|No|Yes|n/a
Wake Island 2007|No|No|Yes
Zatar Wetlands|No|No|Yes

## Setup
### Download and install software
1. Download and install Tesseract v4.1.0.20190314 from the [Uni Mannheim server](https://digi.bib.uni-mannheim.de/tesseract/) (be sure to use the 64 bit version, [direct link](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v4.1.0.20190314.exe))
2. Download and extract the [latest release](https://github.com/cetteup/bf2-auto-spectator/releases/latest)

### In-game setup
Setting up an extra bf2hub account for the spectator is strongly recommended in order to not mess with your existing account's settings/stats.

Any settings not explicitly mentioned here can be changed however you like.
1. Under "game options"
    1. Enable "auto ready"
    2. Enable "opt out of voting" (optional)
    3. Set all transparency values to 100 (optional)
2. Under "controls"
    1. Remove crouch binding and airplane/helicopter free look binding (and/or any other `left ctrl` bindings)
    2. Bind `left ctrl` to console
  
## How to run
1. Open CMD or Powershell (recommended)
2. Enter the path to the controller.exe (can be done by dragging & dropping the .exe onto the CMD/Powershell window)
3. Enter required command line arguments (see above)
4. Enter any additional command lind arguments (optional)
5. Hit enter to run the command

If you want to stop the spectator, hit CTRL + C in the CMD/Powershell window at any time.

**Please note: You cannot (really) use the computer while the spectator is running. It relies on having control over mouse and keyboard and needs the game window to be focused and in the foreground.** You do, however, have small time windows between the spectator's actions in which you can start/stop the stream, stop the spectator etc.

## Known limitations
- bf2-auto-spectator currently only supports running the game in 720p windowed mode
- Windows display scaling must be set to 100%
- auto-spawning will currently fail if the default spawn has been captured by the other team
- game locale/language must be set to English
- some elements of your English locale must be somewhat standard (team names, kick messages, menu items etc)
- the camera and it's movement around the player are controlled by the game
- the spectator is taking up a slot on the server, since it is technically a regular player
