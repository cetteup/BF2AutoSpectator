import argparse
import logging
import os
import pickle
import sys
import time
from datetime import datetime

from BF2AutoSpectator.common import constants
from BF2AutoSpectator.common.commands import CommandStore
from BF2AutoSpectator.common.config import Config
from BF2AutoSpectator.common.exceptions import SpawnCoordinatesNotAvailableException
from BF2AutoSpectator.common.utility import is_responding_pid, find_window_by_title, taskkill_pid, init_pytesseract
from BF2AutoSpectator.game import GameInstanceManager
from BF2AutoSpectator.remote import ControllerClient


def run():
    parser = argparse.ArgumentParser(
        prog='BF2AutoSpectator',
        description='Launch and control a Battlefield 2 spectator instance'
    )
    parser.add_argument('--version', action='version', version=f'{constants.APP_NAME} v{constants.APP_VERSION}')
    parser.add_argument('--player-name', help='Account name of spectating player', type=str, required=True)
    parser.add_argument('--player-pass', help='Account password of spectating player', type=str, required=True)
    parser.add_argument('--server-ip', help='IP of sever to join for spectating', type=str, required=True)
    parser.add_argument('--server-port', help='Port of sever to join for spectating', type=str, default='16567')
    parser.add_argument('--server-pass', help='Password of sever to join for spectating', type=str)
    parser.add_argument('--server-mod', help='Mod of sever to join for spectating', type=str,
                        choices=['bf2', 'xpack', 'bfp2'], default='bf2')
    parser.add_argument('--game-path', help='Path to BF2 install folder',
                        type=str, default='C:\\Program Files (x86)\\EA Games\\Battlefield 2\\')
    parser.add_argument('--game-res', help='Resolution to use for BF2 window', choices=['720p', '900p'], type=str, default='720p')
    parser.add_argument('--tesseract-path', help='Path to Tesseract install folder',
                        type=str, default='C:\\Program Files\\Tesseract-OCR\\')
    parser.add_argument('--instance-rtl', help='How many rounds to use a game instance for (rounds to live)', type=int, default=6)
    parser.add_argument('--min-iterations-on-player',
                        help='Number of iterations to stay on a player before allowing the next_player command',
                        type=int, default=1)
    parser.add_argument('--use-controller', dest='use_controller', action='store_true')
    parser.add_argument('--controller-base-uri', help='Base uri of web controller', type=str)
    parser.add_argument('--no-rtl-limit', dest='limit_rtl', action='store_false')
    parser.add_argument('--debug-log', dest='debug_log', action='store_true')
    parser.add_argument('--debug-screenshot', dest='debug_screenshot', action='store_true')
    parser.set_defaults(limit_rtl=True, debug_log=False, debug_screenshot=False, use_controller=False)
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
        server_mod=args.server_mod,
        game_path=args.game_path,
        tesseract_path=args.tesseract_path,
        limit_rtl=args.limit_rtl,
        instance_rtl=args.instance_rtl,
        use_controller=args.use_controller,
        controller_base_uri=args.controller_base_uri,
        resolution=args.game_res,
        debug_screenshot=args.debug_screenshot,
        min_iterations_on_player=args.min_iterations_on_player,
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
    logging.debug('Loading pickles')
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
    cc = ControllerClient(
        config.get_controller_base_uri()
    )
    cs = CommandStore()

    if config.use_controller():
        cc.connect()

    # Try to find any existing game instance
    logging.info('Looking for an existing game instance')
    gotInstance, correctParams, *_ = gim.find_instance(config.get_server_mod())

    # Schedule restart if no instance was started/found
    if not gotInstance:
        logging.info('Did not find any existing game instance, will launch a new one')
        gis.set_error_restart_required(True)
    elif not correctParams:
        logging.warning('Found game instance is not running with correct parameters, restart required')
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
            logging.error('BF2 error window present, scheduling restart')
            gis.set_error_restart_required(True)

        # Check if a game restart command was issued to the controller
        forceNextPlayer = False
        if config.use_controller():
            if cs.pop('game_restart'):
                logging.info('Game restart requested via controller, queueing game restart')
                # Set restart required flag
                gis.set_error_restart_required(True)

            if cs.pop('rotation_pause'):
                logging.info('Player rotation pause requested via controller, pausing rotation')
                # Set pause via config
                config.pause_player_rotation(constants.PLAYER_ROTATION_PAUSE_DURATION)

            if cs.pop('rotation_resume'):
                logging.info('Player rotation resume requested via controller, resuming rotation')
                # Unpause via config
                config.unpause_player_rotation()
                # Set counter to max to rotate off current player right away
                iterationsOnPlayer = config.get_max_iterations_on_player()

            if cs.pop('next_player'):
                if iterationsOnPlayer + 1 > config.get_min_iterations_on_player():
                    logging.info('Manual switch to next player requested via controller, queueing switch')
                    forceNextPlayer = True
                else:
                    logging.info('Minimum number of iterations on player is not reached, '
                                 'ignoring controller request to switch to next player')

            if cs.pop('respawn'):
                logging.info('Respawn requested via controller, queueing respawn')
                gis.set_round_spawned(False)

        # Start a new game instance if required
        if gis.rtl_restart_required() or gis.error_restart_required():
            if bf2Window is not None and gis.rtl_restart_required():
                # Quit out of current instance
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
            logging.info('Starting new game instance')
            gotInstance, correctParams, runningMod = gim.launch_instance(config.get_server_mod())

            """
            BF2 will "magically" restart the game in order switch mods if we join a server with a different mod. Meaning
            the window will close when joining the server, which will be detected and trigger an error restart. Since the
            game already started a new instance and "+multi" is off, launch_instance will not be able to start another
            instance and will instead pick up the instance from the restart. However, BF2 does not keep the game window size
            parameters during these restarts. So, after the restart, we have
            a) a resolution mismatch (since the parameters were not used for the restart) and
            b) a mod mismatch (since the game restarted with a different "+modPath" without telling us)
            We will now need to restart again in order to restore the correct resolution, but we need to start with
            "+modPath" set to what the game set during the restart.
            """
            if runningMod is not None and runningMod != config.get_server_mod():
                logging.warning(f'Game restart itself with a different mod, updating config')
                config.set_server_mod(runningMod)

            if not gotInstance:
                logging.error('Game instance was not launched, retrying')
                continue
            elif not correctParams:
                logging.error('Game instance was not launched with correct parameters, restart required')
                continue

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
            serverIp, serverPort, serverPass, *_ = config.get_server()
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
            logging.debug('Game message present, ocr-ing message')
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
                logging.critical('Got banned, contact server admin')
                sys.exit(1)
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
                logging.critical(f'Unhandled game message ({gameMessage}), exiting')
                sys.exit(1)

            continue

        # Regularly update current server in case controller is restarted or loses state another way
        if config.use_controller() and gis.spectator_on_server() and \
                iterationsOnPlayer == config.get_max_iterations_on_player():
            cc.update_current_server(
                gis.get_server_ip(),
                gis.get_server_port(),
                gis.get_server_password()
            )

        if config.use_controller() and gis.spectator_on_server() and not gis.map_loading() and \
                (config.get_server_ip() != gis.get_server_ip() or
                 config.get_server_port() != gis.get_server_port() or
                 config.get_server_pass() != gis.get_server_password()):
            logging.info('Server switch requested via controller, disconnecting from current server')
            """
            Don't spam press ESC before disconnecting. It can lead to the game opening the menu again after the map has 
            loaded when (re-)joining a server. Instead, press ESC once and wait a bit longer. Fail and retry next 
            iteration if menu does not open in time.
            """
            if (gim.is_in_menu() or gim.open_menu(max_attempts=1, sleep=3.0)) and gim.disconnect_from_server():
                gis.set_spectator_on_server(False)

                # If game instance is about to be replaced, add one more round on the new server
                if gis.get_round_num() + 1 >= config.get_instance_trl():
                    logging.debug('Extending instance lifetime by one round on the new server')
                    gis.decrease_round_num()
            else:
                logging.error('Failed to disconnect from server')
                continue

        # Player is not on server, check if rejoining is possible and makes sense
        if not gis.spectator_on_server():
            # Check number of free slots
            # TODO

            # Ensure game menu is open, try to open it if not
            """
            Don't spam press ESC before (re-)joining. It can lead to the game opening the menu again after the map has
            loaded. Instead, press ESC once and wait a bit longer. Fail and restart game if menu does not open in time.
            """
            if not gim.is_in_menu() and not gim.open_menu(max_attempts=1, sleep=3.0):
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
            serverIp, serverPort, serverPass, *_ = config.get_server()
            connected = gim.connect_to_server(serverIp, serverPort, serverPass)
            # Treat re-connecting as map rotation (state wise)
            gis.map_rotation_reset()
            # Update state
            gis.set_spectator_on_server(connected)
            gis.set_map_loading(connected)
            if connected:
                gis.set_server(serverIp, serverPort, serverPass)
            else:
                logging.error('Failed to (re-)connect to server')
            # Update controller
            if connected and config.use_controller():
                cc.update_current_server(serverIp, serverPort, serverPass)
            continue

        onRoundFinishScreen = gim.is_round_end_screen_visible()
        mapIsLoading = gim.is_map_loading()
        mapBriefingPresent = gim.is_map_briefing_visible()
        defaultCameraViewVisible = gim.is_default_camera_view_visible()

        # Update instance state if any map load/eor screen is present
        # (only _set_ map loading state here, since it should only be _unset_ when attempting to spawn
        if (onRoundFinishScreen or mapIsLoading or mapBriefingPresent) and not gis.map_loading():
            gis.set_map_loading(True)

        # Always reset iteration counter if default camera view is no longer visible
        if not defaultCameraViewVisible and iterationsOnDefaultCameraView > 0:
            logging.info('Game is no longer on default camera view, resetting counter')
            iterationsOnDefaultCameraView = 0
        if config.limit_rtl() and onRoundFinishScreen and gis.get_round_num() >= config.get_instance_trl():
            logging.info('Game instance has reached rtl limit, restart required')
            gis.set_rtl_restart_required(True)
        elif mapIsLoading:
            logging.info('Map is loading')
            # Reset state once if it still reflected to be on the (same) map
            if gis.rotation_on_map():
                logging.info('Performing map rotation reset')
                gis.map_rotation_reset()
            time.sleep(3)
        elif mapBriefingPresent:
            logging.info('Map briefing present, checking map')
            currentMapName = gim.get_map_name()
            currentGameMode = gim.get_game_mode()
            currentMapSize = gim.get_map_size()

            # Update map state if relevant and required
            # Map size should always be != -1 even for unknown maps, only reason for it being -1 would be that the map
            # briefing was no longer visible when map size was checked (which is why we run it last)
            if currentMapSize != -1 and (
                    currentMapName != gis.get_rotation_map_name() or
                    currentMapSize != gis.get_rotation_map_size() or
                    currentGameMode != gis.get_rotation_game_mode()
            ):
                logging.debug(f'Updating map state: {currentMapName}; {currentGameMode}; {currentMapSize}')
                gis.set_rotation_map_name(currentMapName)
                gis.set_rotation_map_size(currentMapSize)
                gis.set_rotation_game_mode(currentGameMode)

                # Give go-ahead for active joining
                logging.debug('Enabling active joining')
                gis.set_active_join_possible(True)

            if gis.active_join_possible():
                # Check if join game button is present
                logging.debug('Could actively join, checking for button')
                joinGameButtonPresent = gim.is_join_game_button_visible()

                if joinGameButtonPresent:
                    # TODO
                    pass

            time.sleep(3)
        elif onRoundFinishScreen:
            logging.info('Game is on round finish screen')
            # Reset state
            gis.round_end_reset()
            # Unpause player rotation
            config.unpause_player_rotation()
            time.sleep(3)
        elif defaultCameraViewVisible and gis.round_spawned() and \
                iterationsOnDefaultCameraView == 0:
            # In rare cases, an AFK/dead player might be detected as the default camera view
            # => try to rotate to next player to "exit" what is detected as the default camera view
            logging.info('Game is on default camera view, trying to rotate to next player')
            gim.rotate_to_next_player()
            iterationsOnDefaultCameraView += 1
            time.sleep(3)
        elif defaultCameraViewVisible and gis.round_spawned() and \
                iterationsOnDefaultCameraView < config.get_max_iterations_on_default_camera_view():
            # Default camera view is visible after spawning once, either after a round restart or after the round ended
            logging.info('Game is still on default camera view, waiting to see if round ended')
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
            # Default camera view has been visible for a while, failed to restart spectating by pressing space
            # => spawn-suicide again to restart spectating
            logging.info('Game is still on default camera view, queueing another spawn-suicide to restart spectating')
            gis.set_round_spawned(False)
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
                # No need to immediately rotate to next player (usually done after spawn-suicide)
                # => set iteration counter to 0
                iterationsOnPlayer = 0
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
            if currentTeam is not None:
                gis.set_round_team(currentTeam)
                logging.debug(f'Current team index is {gis.get_round_team()} '
                              f'({"USMC/EU/..." if gis.get_round_team() == 0 else "MEC/CHINA/..."})')
            elif gim.spawn_coordinates_available():
                # We should be able to detect the team if we have spawn coordinates for the map/size/game mode combination
                logging.error('Failed to determine current team, retrying')
                # Force another attempt re-enable hud
                gis.set_hud_hidden(True)
                continue
            elif not gis.get_round_spawn_randomize_coordinates():
                # If we were not able to detect a team and map/size/game mod combination is not supported,
                # assume that team detection is not available (unsupported mod/custom map)
                logging.warning('Team detection is not available, switching to spawn point coordinate randomization')
                gis.set_round_spawn_randomize_coordinates(True)

            logging.info('Spawning once')
            spawnSucceeded = False
            if not gis.get_round_spawn_randomize_coordinates():
                try:
                    spawnSucceeded = gim.spawn_suicide()
                except SpawnCoordinatesNotAvailableException:
                    logging.warning(f'Spawn point coordinates not available current combination of map/size/game mode '
                                    f'({gis.get_rotation_map_name()}/'
                                    f'{gis.get_rotation_map_size()}/'
                                    f'{gis.get_rotation_game_mode()}), switching to spawn point coordinate randomization')
                    gis.set_round_spawn_randomize_coordinates(True)

            if gis.get_round_spawn_randomize_coordinates():
                logging.info(f'Attempting to spawn by selecting randomly generated spawn point coordinates')
                spawnSucceeded = gim.spawn_suicide(randomize=True)

            logging.info('Spawn succeeded' if spawnSucceeded else 'Spawn failed, retrying')
            gis.set_round_spawned(spawnSucceeded)

            # Set counter to max to skip spectator
            iterationsOnPlayer = config.get_max_iterations_on_player()
            # Unpause in order to not stay on the spectator after suicide
            config.unpause_player_rotation()
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
                # Set counter to max to rotate off current player right away
                iterationsOnPlayer = config.get_max_iterations_on_player()
            else:
                time.sleep(2)
        elif not onRoundFinishScreen:
            logging.info('Rotating to next player')
            gim.rotate_to_next_player()
            iterationsOnPlayer = 0


if __name__ == '__main__':
    run()
