import argparse
import logging
import os
import pickle
import sys
import time

import constants
from config import Config
from controller import Controller
from exceptions import *
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

logging.basicConfig(level=logging.DEBUG if args.debug_log else logging.INFO, format='%(asctime)s %(message)s')

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
    max_iterations_on_player=5
)

# Make sure provided paths are valid
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
gim = GameInstanceManager(config.get_game_path(), config.get_player_name(), config.get_player_pass(), histograms)
gameInstanceState = gim.get_state()
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
    gotInstance = gim.launch_instance(config.get_resolution())
else:
    logging.info('"Attaching" to existing game instance')
    gotInstance = gim.find_instance(config.get_resolution())

# Schedule restart if no instance was started/found
if not gotInstance:
    gameInstanceState.set_error_restart_required(True)

# Start with max to switch away from dead spectator right away
iterationsOnPlayer = config.get_max_iterations_on_player()
while True:
    bf2Window = gim.get_game_window()
    # Try to bring BF2 window to foreground
    if not gameInstanceState.error_restart_required():
        try:
            gim.bring_to_foreground()
        except Exception as e:
            logging.error('BF2 window is gone, restart required')
            logging.error(str(e))
            gameInstanceState.set_error_restart_required(True)

    # Check if game froze
    if not gameInstanceState.error_restart_required() and not is_responding_pid(int(bf2Window.pid)):
        logging.info('Game froze, checking unresponsive count')
        # Game will temporarily freeze when map load finishes or when joining server, so don't restart right away
        if gameInstanceState.get_error_unresponsive_count() < 3:
            logging.info('Unresponsive count below limit, giving time to recover')
            # Increase unresponsive count
            gameInstanceState.increase_error_unresponsive_count()
            # Check again in 2 seconds
            time.sleep(2)
            continue
        else:
            logging.error('Unresponsive count exceeded limit, scheduling restart')
            gameInstanceState.set_error_restart_required(True)
    elif not gameInstanceState.error_restart_required() and gameInstanceState.get_error_unresponsive_count() > 0:
        logging.info('Game recovered from temp freeze, resetting unresponsive count')
        # Game got it together, reset unresponsive count
        gameInstanceState.reset_error_unresponsive_count()

    # Check for (debug assertion and Visual C++ Runtime) error window
    if not gameInstanceState.error_restart_required() and \
            (find_window_by_title('BF2 Error') is not None or
             find_window_by_title('Microsoft Visual C++ Runtime Library') is not None):
        logging.error('BF2 Error window present, scheduling restart')
        gameInstanceState.set_error_restart_required(True)

    # Check if a game restart command was issued to the controller
    if config.use_controller():
        commands = controller.get_commands()
        if commands.get('game_restart') is True:
            logging.info('Game restart requested via controller, unsetting command flag and queueing game restart')
            # Reset command to false
            commandReset = controller.post_commands({'game_restart': False})
            if commandReset:
                # Set restart required flag
                gameInstanceState.set_error_restart_required(True)

    # Start a new game instance if required
    if gameInstanceState.rtl_restart_required() or gameInstanceState.error_restart_required():
        if bf2Window is not None and gameInstanceState.rtl_restart_required():
            # Quit out of current instnace
            logging.info('Quitting existing game instance')
            quitSuccessful = gim.quit_game_instance()
            logging.debug(f'Quit successful: {quitSuccessful}')
            gameInstanceState.set_rtl_restart_required(False)
            # If quit was not successful, switch to error restart
            if not quitSuccessful:
                logging.error('Quitting existing game instance failed, switching to error restart')
                gameInstanceState.set_error_restart_required(True)
        # Don't use elif here so error restart can be executed right after a failed quit attempt
        if bf2Window is not None and gameInstanceState.error_restart_required():
            # Kill any remaining instance by pid
            logging.info('Killing existing game instance')
            killed = taskkill_pid(int(bf2Window.pid))
            logging.debug(f'Instance killed: {killed}')
            # Give Windows time to actually close the window
            time.sleep(3)

        # Init game new game instance
        gim.launch_instance(config.get_resolution())
        # Update window dict
        bf2Window = gim.get_game_window()

        # Bring window to foreground
        try:
            gim.bring_to_foreground()
        except Exception as e:
            logging.error('BF2 window is gone, restart required')
            logging.error(str(e))
            continue

        # Connect to server
        logging.info('Connecting to server')
        serverIp, serverPort, serverPass = config.get_server()
        connected = gim.connect_to_server(serverIp, serverPort, serverPass)
        # Reset state
        gameInstanceState.restart_reset()
        gameInstanceState.set_spectator_on_server(connected)
        gameInstanceState.set_map_loading(connected)
        if connected:
            gameInstanceState.set_server(serverIp, serverPort, serverPass)

        continue

    # Make sure we are still in the game
    gameMessagePresent = gim.check_for_game_message()
    if gameMessagePresent:
        logging.info('Game message present, ocr-ing message')
        gameMessage = gim.ocr_game_message()

        # Close game message to enable actions
        gim.close_game_message()

        if 'full' in gameMessage:
            logging.info('Server full, trying to rejoin in 30 seconds')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
            # Connect to server waits 10, wait another 20 = 30
            time.sleep(20)
        elif 'kicked' in gameMessage:
            logging.info('Got kicked, trying to rejoin')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
        elif 'banned' in gameMessage:
            sys.exit('Got banned, contact server admin')
        elif 'connection' in gameMessage and 'lost' in gameMessage or \
                'failed to connect' in gameMessage:
            logging.info('Connection lost, trying to reconnect')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
        elif 'modified content' in gameMessage:
            logging.info('Got kicked for modified content, trying to rejoin')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
        elif 'invalid ip address' in gameMessage:
            logging.info('Join by ip dialogue bugged, restart required')
            # Set restart flag
            gameInstanceState.set_error_restart_required(True)
        else:
            sys.exit(gameMessage)

        continue

    # If we are using a controller, check if server switch is required and possible
    # (spectator not on server or fully in game)
    if config.use_controller() and (not gameInstanceState.spectator_on_server() or
                                    (not gameInstanceState.map_loading() and
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
        elif gameInstanceState.spectator_on_server():
            controller.post_current_server(
                gameInstanceState.get_server_ip(),
                gameInstanceState.get_server_port(),
                gameInstanceState.get_server_password()
            )

    # Queue server switch if spectator is supposed to be on a different server (or the password changed)
    if gameInstanceState.spectator_on_server() and \
            (config.get_server_ip() != gameInstanceState.get_server_ip() or
             config.get_server_port() != gameInstanceState.get_server_port() or
             config.get_server_pass() != gameInstanceState.get_server_password()):
        logging.info('Queued server switch, disconnecting from current server')
        gameInstanceState.set_spectator_on_server(False)
        gim.disconnect_from_server()

    # Player is not on server, check if rejoining is possible and makes sense
    if not gameInstanceState.spectator_on_server():
        # Check number of free slots
        # TODO
        # (Re-)connect to server
        logging.info('(Re-)Connecting to server')
        serverIp, serverPort, serverPass = config.get_server()
        connected = gim.connect_to_server(serverIp, serverPort, serverPass)
        # Treat re-connecting as map rotation (state wise)
        gameInstanceState.map_rotation_reset()
        # Update state
        gameInstanceState.set_spectator_on_server(connected)
        gameInstanceState.set_map_loading(connected)
        if connected:
            gameInstanceState.set_server(serverIp, serverPort, serverPass)
        # Update controller
        if connected and config.use_controller():
            controller.post_current_server(serverIp, serverPort, serverPass)
        continue

    onRoundFinishScreen = gim.check_if_round_ended()
    mapIsLoading = gim.check_if_map_is_loading()
    mapBriefingPresent = gim.check_for_map_briefing()

    # Update instance state if any map load/eor screen is present
    # (only _set_ map loading state here, since it should only be _unset_ when attempting to spawn
    if (onRoundFinishScreen or mapIsLoading or mapBriefingPresent) and not gameInstanceState.map_loading():
        gameInstanceState.set_map_loading(True)

    if config.limit_rtl() and onRoundFinishScreen and gameInstanceState.get_round_num() >= config.get_instance_trl():
        logging.info('Game instance has reached rtl limit, restart required')
        gameInstanceState.set_rtl_restart_required(True)
    elif mapIsLoading:
        logging.info('Map is loading')
        # Reset state once if it still reflected to be on the (same) map
        if gameInstanceState.rotation_on_map():
            logging.info('Performing map rotation reset')
            gameInstanceState.map_rotation_reset()
        iterationsOnPlayer = config.get_max_iterations_on_player()
        time.sleep(3)
    elif mapBriefingPresent:
        logging.info('Map briefing present, checking map')
        currentMapName = gim.get_map_name()
        currentMapSize = gim.get_map_size()

        # Update map state if relevant and required
        if currentMapName is not None and currentMapSize != -1 and \
                (currentMapName != gameInstanceState.get_rotation_map_name() or
                 currentMapSize != gameInstanceState.get_rotation_map_size()):
            logging.debug(f'Updating map state: {currentMapName}; {currentMapSize}')
            gameInstanceState.set_rotation_map_name(currentMapName)
            gameInstanceState.set_rotation_map_size(currentMapSize)

            # Give go-ahead for active joining
            logging.info('Enabling active joining')
            gameInstanceState.set_active_join_possible(True)

        if gameInstanceState.active_join_possible():
            # Check if join game button is present
            logging.info('Could actively join, checking for button')
            joinGameButtonPresent = gim.check_for_join_game_button()

            if joinGameButtonPresent:
                # TODO
                pass

        time.sleep(3)
    elif onRoundFinishScreen:
        logging.info('Game is on round finish screen')
        # Reset state
        gameInstanceState.round_end_reset()
        # Set counter to max again to skip spectator
        iterationsOnPlayer = config.get_max_iterations_on_player()
        time.sleep(3)
    elif not onRoundFinishScreen and not gameInstanceState.round_spawned():
        # Loaded into map, now trying to start spectating
        gameInstanceState.set_map_loading(False)
        # Re-enable hud if required
        if gameInstanceState.hud_hidden():
            # Give game time to swap teams
            time.sleep(3)
            # Re-enable hud
            logging.info('Enabling hud')
            gim.toggle_hud(1)
            # Update state
            gameInstanceState.set_hud_hidden(False)
            time.sleep(1)

        spawnMenuVisible = gim.check_if_spawn_menu_visible()
        if not spawnMenuVisible:
            logging.info('Spawn menu not visible, opening with enter')
            gim.open_spawn_menu()
            # Force another attempt re-enable hud
            gameInstanceState.set_hud_hidden(True)
            continue

        logging.info('Determining team')
        currentTeam = gim.get_player_team()
        if currentTeam is not None and \
                gameInstanceState.get_rotation_map_name() is not None and \
                gameInstanceState.get_rotation_map_size() != -1:
            gameInstanceState.set_round_team(currentTeam)
            logging.debug(f'Current team: {"USMC" if gameInstanceState.get_round_team() == 0 else "MEC/CHINA"}')
            logging.info('Spawning once')
            try:
                spawnSucceeded = gim.spawn_suicide()
                logging.info('Spawn succeeded' if spawnSucceeded else 'Spawn failed, retrying')
                gameInstanceState.set_round_spawned(spawnSucceeded)
            except UnsupportedMapException as e:
                logging.error('Spawning not supported on current map/size')
                # Wait map out by "faking" spawn
                gameInstanceState.set_round_spawned(True)
        elif gameInstanceState.get_rotation_map_name() is not None and \
                gameInstanceState.get_rotation_map_size() != -1:
            logging.error('Failed to determine current team, retrying')
            # Force another attempt re-enable hud
            gameInstanceState.set_hud_hidden(True)
            time.sleep(2)
            continue
        else:
            # Map detection failed, force reconnect
            logging.error('Map detection failed, disconnecting')
            gim.disconnect_from_server()
            # Update state
            gameInstanceState.set_spectator_on_server(False)
            continue
    elif not onRoundFinishScreen and not gameInstanceState.hud_hidden():
        logging.info('Hiding hud')
        gim.toggle_hud(0)
        gameInstanceState.set_hud_hidden(True)
        # Increase round number/counter
        gameInstanceState.increase_round_num()
        logging.debug(f'Entering round #{gameInstanceState.get_round_num()} using this instance')
        # Spectator has "entered" map, update state accordingly
        gameInstanceState.set_rotation_on_map(True)
    elif not onRoundFinishScreen and iterationsOnPlayer < config.get_max_iterations_on_player():
        # Check if player is afk
        if not gim.is_sufficient_action_on_screen():
            logging.info('Insufficient action on screen')
            iterationsOnPlayer = config.get_max_iterations_on_player()
        else:
            logging.info('Nothing to do, stay on player')
            iterationsOnPlayer += 1
            time.sleep(2)
    elif not onRoundFinishScreen:
        logging.info('Rotating to next player')
        gim.rotate_to_next_player()
        iterationsOnPlayer = 0
