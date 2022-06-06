import argparse
import logging
import os
import pickle
import sys
import time
from datetime import datetime

import constants
from config import Config
from controller import Controller
from exceptions import UnsupportedMapException
from gameinstancemanager import GameInstanceManager
from helpers import is_responding_pid, find_window_by_title, taskkill_pid, init_pytesseract

parser = argparse.ArgumentParser(description='Launch and control a Battlefield 2 spectator instance')
parser.add_argument('--version', action='version', version=f'{constants.APP_NAME} v{constants.APP_VERSION}')
parser.add_argument('--player-name', help='Account name of spectating player', type=str, required=True)
parser.add_argument('--player-pass', help='Account password of spectating player', type=str, required=True)
parser.add_argument('--server-ip', help='IP of sever to join for spectating', type=str, required=True)
parser.add_argument('--server-port', help='Port of sever to join for spectating', type=str, default='16567')
parser.add_argument('--server-pass', help='Password of sever to join for spectating', type=str)
parser.add_argument('--game-path', help='Path to BF2 install folder',
                    type=str, default='C:\\Program Files (x86)\\EA Games\\Battlefield 2\\')
parser.add_argument('--game-res', help='Resolution to use for BF2 window', choices=['720p', '900p'], type=str, default='720p')
parser.add_argument('--tesseract-path', help='Path to Tesseract install folder',
                    type=str, default='C:\\Program Files\\Tesseract-OCR\\')
parser.add_argument('--instance-rtl', help='How many rounds to use a game instance for (rounds to live)', type=int, default=6)
parser.add_argument('--use-controller', dest='use_controller', action='store_true')
parser.add_argument('--controller-base-uri', help='Base uri of web controller', type=str)
parser.add_argument('--controller-app-key', help='App key for web controller', type=str)
parser.add_argument('--controller-timeout', help='Timeout to use for requests to controller (in seconds)', type=int,
                    default=2)
parser.add_argument('--no-start', dest='start_game', action='store_false')
parser.add_argument('--no-rtl-limit', dest='limit_rtl', action='store_false')
parser.add_argument('--debug-log', dest='debug_log', action='store_true')
parser.add_argument('--debug-screenshot', dest='debug_screenshot', action='store_true')
parser.set_defaults(start_game=True, limit_rtl=True, debug_log=False, debug_screenshot=False, use_controller=False)
args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG if args.debug_log else logging.INFO, stream=sys.stdout,
                    format='%(asctime)s %(levelname)-8s %(message)s')

# Transfer argument values to config
config = Config()
config.set_options(
    player_name=args.player_name,
    player_pass=args.player_pass,
    server_ip=args.server_ip,
    server_port=args.server_port,
    server_pass=args.server_pass,
    game_path=args.game_path,
    tesseract_path=args.tesseract_path,
    limit_rtl=args.limit_rtl,
    instance_rtl=args.instance_rtl,
    use_controller=args.use_controller,
    controller_base_uri=args.controller_base_uri,
    controller_app_key=args.controller_app_key,
    controller_timeout=args.controller_timeout,
    resolution=args.game_res,
    debug_screenshot=args.debug_screenshot,
    max_iterations_on_player=5,
    max_iterations_on_default_camera_view=6
)

# Make sure provided paths.py are valid
if not os.path.isfile(os.path.join(config.get_tesseract_path(), constants.TESSERACT_EXE)):
    sys.exit(f'Could not find {constants.TESSERACT_EXE} in given install folder: {args.tesseract_path}')
elif not os.path.isfile(os.path.join(config.get_game_path(), constants.BF2_EXE)):
    sys.exit(f'Could not find {constants.BF2_EXE} in given game install folder: {config.get_game_path()}')

# Init pytesseract
init_pytesseract(config.get_tesseract_path())

# Load pickles
logging.info('Loading pickles')
with open(os.path.join(config.ROOT_DIR, 'pickle', 'histograms.pickle'), 'rb') as histogramFile:
    histograms = pickle.load(histogramFile)

# Init debug directory if debugging is enabled
if config.debug_screenshot():
    # Create debug output dir if needed
    if not os.path.isdir(config.DEBUG_DIR):
        os.mkdir(Config.DEBUG_DIR)

# Init game instance state store
gim = GameInstanceManager(
    config.get_game_path(),
    config.get_player_name(),
    config.get_player_pass(),
    config.get_resolution(),
    histograms
)
gis = gim.get_state()
controller = Controller(
    config.get_controller_base_uri(),
    config.get_controller_app_key(),
    config.get_controller_timeout()
)

# Check whether the controller has a server join
if config.use_controller():
    logging.info('Checking for join server on controller')
    joinServer = controller.get_join_server()
    if joinServer is not None and \
            (joinServer['ip'] != config.get_server_ip() or
             str(joinServer['gamePort']) != config.get_server_port()):
        # Spectator is supposed to be on different server
        logging.info('Controller has a server to join, updating config')
        config.set_server(joinServer['ip'], str(joinServer['gamePort']), joinServer['password'])

# Init game instance if requested
gotInstance = False
if args.start_game:
    logging.info('Initializing spectator game instance')
    gotInstance = gim.launch_instance()
else:
    logging.info('"Attaching" to existing game instance')
    gotInstance = gim.find_instance()

# Schedule restart if no instance was started/found
if not gotInstance:
    gis.set_error_restart_required(True)

# Start with max to switch away from dead spectator right away
iterationsOnPlayer = config.get_max_iterations_on_player()
iterationsOnDefaultCameraView = 0
while True:
    bf2Window = gim.get_game_window()
    # Try to bring BF2 window to foreground
    if not gis.error_restart_required():
        try:
            gim.bring_to_foreground()
        except Exception as e:
            logging.error('BF2 window is gone, restart required')
            logging.error(str(e))
            gis.set_error_restart_required(True)

    # Check if game froze
    if not gis.error_restart_required() and not is_responding_pid(bf2Window.pid):
        logging.info('Game froze, checking unresponsive count')
        # Game will temporarily freeze when map load finishes or when joining server, so don't restart right away
        if gis.get_error_unresponsive_count() < 3:
            logging.info('Unresponsive count below limit, giving time to recover')
            # Increase unresponsive count
            gis.increase_error_unresponsive_count()
            # Check again in 2 seconds
            time.sleep(2)
            continue
        else:
            logging.error('Unresponsive count exceeded limit, scheduling restart')
            gis.set_error_restart_required(True)
    elif not gis.error_restart_required() and gis.get_error_unresponsive_count() > 0:
        logging.info('Game recovered from temp freeze, resetting unresponsive count')
        # Game got it together, reset unresponsive count
        gis.reset_error_unresponsive_count()

    # Check for (debug assertion and Visual C++ Runtime) error window
    if not gis.error_restart_required() and \
            (find_window_by_title('BF2 Error') is not None or
             find_window_by_title('Microsoft Visual C++ Runtime Library') is not None):
        logging.error('BF2 Error window present, scheduling restart')
        gis.set_error_restart_required(True)

    # Check if a game restart command was issued to the controller
    forceNextPlayer = False
    if config.use_controller():
        commands = controller.get_commands()
        if commands.get('game_restart') is True:
            logging.info('Game restart requested via controller, queueing game restart')
            # Reset command to false
            commandReset = controller.post_commands({'game_restart': False})
            if commandReset:
                # Set restart required flag
                gis.set_error_restart_required(True)

        if commands.get('rotation_pause') is True:
            logging.info('Player rotation pause requested via controller, pausing rotation')
            # Reset command to false
            commandReset = controller.post_commands({'rotation_pause': False})
            if commandReset:
                # Set pause via config
                config.pause_player_rotation(constants.PLAYER_ROTATION_PAUSE_DURATION)

        if commands.get('rotation_resume') is True:
            logging.info('Player rotation resume requested via controller, resuming rotation')
            # Reset command flag
            commandReset = controller.post_commands({'rotation_resume': False})
            if commandReset:
                # Unpause via config
                config.unpause_player_rotation()

        if commands.get('next_player') is True:
            logging.info('Manual switch to next player requested via controller, queueing switch')
            # Reset command to false
            commandReset = controller.post_commands({'next_player': False})
            if commandReset:
                forceNextPlayer = True

        if commands.get('respawn') is True:
            logging.info('Respawn requested via controller, queueing respawn')
            # Reset command
            commandReset = controller.post_commands({'respawn': False})
            if commandReset:
                gis.set_round_spawned(False)

    # Start a new game instance if required
    if gis.rtl_restart_required() or gis.error_restart_required():
        if bf2Window is not None and gis.rtl_restart_required():
            # Quit out of current instnace
            logging.info('Quitting existing game instance')
            quitSuccessful = gim.quit_instance()
            logging.debug(f'Quit successful: {quitSuccessful}')
            gis.set_rtl_restart_required(False)
            # If quit was not successful, switch to error restart
            if not quitSuccessful:
                logging.error('Quitting existing game instance failed, switching to error restart')
                gis.set_error_restart_required(True)
        # Don't use elif here so error restart can be executed right after a failed quit attempt
        if bf2Window is not None and gis.error_restart_required():
            # Kill any remaining instance by pid
            logging.info('Killing existing game instance')
            killed = taskkill_pid(bf2Window.pid)
            logging.debug(f'Instance killed: {killed}')
            # Give Windows time to actually close the window
            time.sleep(3)

        # Init game new game instance
        gim.launch_instance()

        # Bring window to foreground
        try:
            gim.bring_to_foreground()
        except Exception as e:
            logging.error('BF2 window is gone, restart required')
            logging.error(str(e))
            continue

        # Ensure game menu is open, try to open it if not
        if not gim.is_in_menu() and not gim.open_menu():
            logging.error('Game menu is not visible and could not be opened, restart required')
            gis.set_error_restart_required(True)
            continue

        # Connect to server
        logging.info('Connecting to server')
        serverIp, serverPort, serverPass = config.get_server()
        connected = gim.connect_to_server(serverIp, serverPort, serverPass)
        # Reset state
        gis.restart_reset()
        gis.set_spectator_on_server(connected)
        gis.set_map_loading(connected)
        if connected:
            gis.set_server(serverIp, serverPort, serverPass)

        continue

    # Make sure we are still in the game
    gameMessagePresent = gim.is_game_message_visible()
    if gameMessagePresent:
        logging.info('Game message present, ocr-ing message')
        gameMessage = gim.ocr_game_message()

        # Close game message to enable actions
        gim.close_game_message()

        if 'full' in gameMessage:
            logging.info('Server full, trying to rejoin in 30 seconds')
            # Update state
            gis.set_spectator_on_server(False)
            # Connect to server waits 10, wait another 20 = 30
            time.sleep(20)
        elif 'kicked' in gameMessage:
            logging.info('Got kicked, trying to rejoin')
            # Update state
            gis.set_spectator_on_server(False)
        elif 'banned' in gameMessage:
            sys.exit('Got banned, contact server admin')
        elif 'connection' in gameMessage and 'lost' in gameMessage or \
                'failed to connect' in gameMessage:
            logging.info('Connection lost, trying to reconnect')
            # Update state
            gis.set_spectator_on_server(False)
        elif 'modified content' in gameMessage:
            logging.info('Got kicked for modified content, trying to rejoin')
            # Update state
            gis.set_spectator_on_server(False)
        elif 'invalid ip address' in gameMessage:
            logging.info('Join by ip dialogue bugged, restart required')
            # Set restart flag
            gis.set_error_restart_required(True)
        else:
            sys.exit(gameMessage)

        continue

    # If we are using a controller, check if server switch is required and possible
    # (spectator not on server or fully in game)
    if config.use_controller() and (not gis.spectator_on_server() or
                                    (not gis.map_loading() and
                                     iterationsOnPlayer == config.get_max_iterations_on_player())):
        logging.info('Checking for join server on controller')
        joinServer = controller.get_join_server()
        # Update server and switch if spectator is supposed to be on a different server of password was updated
        if joinServer is not None and \
                (joinServer['ip'] != config.get_server_ip() or
                 str(joinServer['gamePort']) != config.get_server_port() or
                 joinServer['password'] != config.get_server_pass()):
            # Spectator is supposed to be on different server
            logging.info('Controller has a server to join, updating config')
            config.set_server_ip(joinServer['ip'])
            config.set_server_port(str(joinServer['gamePort']))
            config.set_server_pass(joinServer['password'])
        elif gis.spectator_on_server():
            controller.post_current_server(
                gis.get_server_ip(),
                gis.get_server_port(),
                gis.get_server_password()
            )

    # Queue server switch if spectator is supposed to be on a different server (or the password changed)
    if gis.spectator_on_server() and \
            (config.get_server_ip() != gis.get_server_ip() or
             config.get_server_port() != gis.get_server_port() or
             config.get_server_pass() != gis.get_server_password()):
        logging.info('Queued server switch, disconnecting from current server')
        if (gim.is_in_menu() or gim.open_menu()) and gim.disconnect_from_server():
            gis.set_spectator_on_server(False)

            # If game instance is about to be replaced, add one more round on the new server
            if gis.get_round_num() + 1 >= config.get_instance_trl():
                logging.info('Extending instance lifetime by one round on the new server')
                gis.decrease_round_num()
        else:
            logging.error('Failed to disconnect from server')
            continue

    # Player is not on server, check if rejoining is possible and makes sense
    if not gis.spectator_on_server():
        # Check number of free slots
        # TODO

        # Ensure game menu is open, try to open it if not
        if not gim.is_in_menu() and not gim.open_menu():
            logging.error('Game menu is not visible and could not be opened, restart required')
            gis.set_error_restart_required(True)
            continue

        # Disconnect from server if still connected according to menu
        if gim.is_disconnect_button_visible():
            logging.warning('Game is still connected to a server, disconnecting')
            disconnected = gim.disconnect_from_server()
            if not disconnected:
                logging.error('Failed to disconnect from server, skipping joining server for now')
                continue

        # (Re-)connect to server
        logging.info('(Re-)Connecting to server')
        serverIp, serverPort, serverPass = config.get_server()
        connected = gim.connect_to_server(serverIp, serverPort, serverPass)
        # Treat re-connecting as map rotation (state wise)
        gis.map_rotation_reset()
        # Update state
        gis.set_spectator_on_server(connected)
        gis.set_map_loading(connected)
        if connected:
            gis.set_server(serverIp, serverPort, serverPass)
        # Update controller
        if connected and config.use_controller():
            controller.post_current_server(serverIp, serverPort, serverPass)
        continue

    onRoundFinishScreen = gim.is_round_end_screen_visible()
    mapIsLoading = gim.is_map_loading()
    mapBriefingPresent = gim.is_map_briefing_visible()
    defaultCameraViewVisible = gim.is_default_camera_view_visible()

    # Update instance state if any map load/eor screen is present
    # (only _set_ map loading state here, since it should only be _unset_ when attempting to spawn
    if (onRoundFinishScreen or mapIsLoading or mapBriefingPresent) and not gis.map_loading():
        gis.set_map_loading(True)

    if config.limit_rtl() and onRoundFinishScreen and gis.get_round_num() >= config.get_instance_trl():
        logging.info('Game instance has reached rtl limit, restart required')
        gis.set_rtl_restart_required(True)
    elif mapIsLoading:
        logging.info('Map is loading')
        # Reset state once if it still reflected to be on the (same) map
        if gis.rotation_on_map():
            logging.info('Performing map rotation reset')
            gis.map_rotation_reset()
        iterationsOnPlayer = config.get_max_iterations_on_player()
        time.sleep(3)
    elif mapBriefingPresent:
        logging.info('Map briefing present, checking map')
        currentMapName = gim.get_map_name()
        currentMapSize = gim.get_map_size()

        # Update map state if relevant and required
        if currentMapName is not None and currentMapSize != -1 and \
                (currentMapName != gis.get_rotation_map_name() or
                 currentMapSize != gis.get_rotation_map_size()):
            logging.debug(f'Updating map state: {currentMapName}; {currentMapSize}')
            gis.set_rotation_map_name(currentMapName)
            gis.set_rotation_map_size(currentMapSize)

            # Give go-ahead for active joining
            logging.info('Enabling active joining')
            gis.set_active_join_possible(True)

        if gis.active_join_possible():
            # Check if join game button is present
            logging.info('Could actively join, checking for button')
            joinGameButtonPresent = gim.is_join_game_button_visible()

            if joinGameButtonPresent:
                # TODO
                pass

        time.sleep(3)
    elif onRoundFinishScreen:
        logging.info('Game is on round finish screen')
        # Reset state
        gis.round_end_reset()
        # Set counter to max again to skip spectator
        iterationsOnPlayer = config.get_max_iterations_on_player()
        time.sleep(3)
    elif defaultCameraViewVisible and gis.round_spawned() and \
            iterationsOnDefaultCameraView < config.get_max_iterations_on_default_camera_view():
        # Default camera view is visible after spawning once, either after a round restart or after the round ended
        logging.info('Game is on default camera view, waiting to see if round ended')
        iterationsOnDefaultCameraView += 1
        time.sleep(3)
    elif defaultCameraViewVisible and gis.round_spawned() and \
            iterationsOnDefaultCameraView == config.get_max_iterations_on_default_camera_view():
        # Default camera view has been visible for a while, most likely due to a round restart
        # => try to restart spectating by pressing space (only works on freecam-enabled servers)
        logging.info('Game is still on default camera view, trying to (re-)start spectating via freecam toggle')
        gim.start_spectating_via_freecam_toggle()
        iterationsOnDefaultCameraView += 1
        time.sleep(3)
    elif defaultCameraViewVisible and gis.round_spawned() and \
            iterationsOnDefaultCameraView > config.get_max_iterations_on_default_camera_view():
        # Default camera view has been visible for a while, failde to restart spectating by pressing space
        # => spawn-suicide again to restart spectating
        logging.info('Game is still on default camera view, queueing another spawn-suicide to restart spectating')
        gis.set_round_spawned(False)
        iterationsOnDefaultCameraView = 0
    elif not defaultCameraViewVisible and iterationsOnDefaultCameraView > 0:
        logging.info('Game is no longer on default camera view, resetting counter')
        iterationsOnDefaultCameraView = 0
    elif defaultCameraViewVisible and not gis.round_spawned() and not gis.round_freecam_toggle_spawn_attempted():
        # Try to restart spectating without suiciding on consecutive rounds (only works on freecam-enabled servers)
        logging.info('Game is on default camera view, trying to (re-)start spectating via freecam toggle')
        gis.set_map_loading(False)
        gim.start_spectating_via_freecam_toggle()
        gis.set_round_freecam_toggle_spawn_attempted(True)
        time.sleep(.5)
        # Set round spawned to true of default camera view is no longer visible, else enable hud for spawn-suicide
        if not gim.is_default_camera_view_visible():
            logging.info('Started spectating via freecam toggle, skipping spawn-suicide')
            gis.set_round_spawned(True)
            # Increase round number/counter
            gis.increase_round_num()
            logging.debug(f'Entering round #{gis.get_round_num()} using this instance')
            # Spectator has "entered" map, update state accordingly
            gis.set_rotation_on_map(True)
        else:
            # Don't log this as an error since it's totally normal
            logging.info('Failed to start spectating via freecam toggle, continuing to spawn-suicide')
    elif not onRoundFinishScreen and not gis.round_spawned():
        # Loaded into map, now trying to start spectating
        gis.set_map_loading(False)
        # Re-enable hud if required
        if gis.hud_hidden():
            # Give game time to swap teams
            time.sleep(3)
            # Re-enable hud
            logging.info('Enabling hud')
            gim.toggle_hud(1)
            # Update state
            gis.set_hud_hidden(False)
            time.sleep(1)

        spawnMenuVisible = gim.is_spawn_menu_visible()
        if not spawnMenuVisible:
            logging.info('Spawn menu not visible, opening with enter')
            gim.open_spawn_menu()
            # Force another attempt re-enable hud
            gis.set_hud_hidden(True)
            continue

        logging.info('Determining team')
        currentTeam = gim.get_player_team()
        if currentTeam is not None and \
                gis.get_rotation_map_name() is not None and \
                gis.get_rotation_map_size() != -1:
            gis.set_round_team(currentTeam)
            logging.debug(f'Current team: {"USMC" if gis.get_round_team() == 0 else "MEC/CHINA"}')
            logging.info('Spawning once')
            try:
                spawnSucceeded = gim.spawn_suicide()
                logging.info('Spawn succeeded' if spawnSucceeded else 'Spawn failed, retrying')
                gis.set_round_spawned(spawnSucceeded)
            except UnsupportedMapException as e:
                logging.error('Spawning not supported on current map/size')
                # Wait map out by "faking" spawn
                gis.set_round_spawned(True)
        elif gis.get_rotation_map_name() is not None and \
                gis.get_rotation_map_size() != -1:
            logging.error('Failed to determine current team, retrying')
            # Force another attempt re-enable hud
            gis.set_hud_hidden(True)
            time.sleep(2)
            continue
        else:
            # Map detection failed, force reconnect
            logging.error('Map detection failed, disconnecting')
            if (gim.is_in_menu() or gim.open_menu()) and gim.disconnect_from_server():
                # Update state
                gis.set_spectator_on_server(False)
            else:
                logging.error('Failed to disconnect from server')
            continue
    elif not onRoundFinishScreen and not gis.hud_hidden():
        logging.info('Hiding hud')
        gim.toggle_hud(0)
        gis.set_hud_hidden(True)
        # Increase round number/counter
        gis.increase_round_num()
        logging.debug(f'Entering round #{gis.get_round_num()} using this instance')
        # Spectator has "entered" map, update state accordingly
        gis.set_rotation_on_map(True)
    elif not onRoundFinishScreen and iterationsOnPlayer < config.get_max_iterations_on_player() and \
            not config.player_rotation_paused() and not forceNextPlayer:
        # Check if player is afk
        if not gim.is_sufficient_action_on_screen():
            logging.info('Insufficient action on screen')
            iterationsOnPlayer = config.get_max_iterations_on_player()
        else:
            logging.info('Nothing to do, stay on player')
            iterationsOnPlayer += 1
            time.sleep(2)
    elif not onRoundFinishScreen and config.player_rotation_paused() and not forceNextPlayer:
        logging.info(f'Player rotation is paused until {config.get_player_rotation_paused_until().isoformat()}')
        # If rotation pause flag is still set even though the pause expired, remove the flag
        if config.get_player_rotation_paused_until() < datetime.now():
            logging.info('Player rotation pause expired, re-enabling rotation')
            config.unpause_player_rotation()
        else:
            time.sleep(2)
    elif not onRoundFinishScreen:
        logging.info('Rotating to next player')
        gim.rotate_to_next_player()
        iterationsOnPlayer = 0
