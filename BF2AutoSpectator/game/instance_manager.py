import os
import random
import re
import subprocess
import time
from typing import Tuple, Optional

import numpy as np
import pyautogui
import win32con
import win32gui

from BF2AutoSpectator.common import constants
from BF2AutoSpectator.common.exceptions import SpawnCoordinatesNotAvailableException
from BF2AutoSpectator.common.logger import logger
from BF2AutoSpectator.common.utility import Window, find_window_by_title, get_resolution_window_size, \
    mouse_move_to_game_window_coord, mouse_click_in_game_window, ocr_screenshot_game_window_region, auto_press_key, \
    mouse_reset_legacy, mouse_move_legacy, is_responding_pid, histogram_screenshot_region, calc_cv2_hist_delta, \
    ImageOperation, mouse_reset, get_mod_from_command_line, run_conman, ocr_screenshot_region, is_similar_str, \
    press_key, release_key
from .instance_state import GameInstanceState

# Remove the top left corner from pyautogui failsafe points
# (avoid triggering failsafe exception due to mouse moving to top left during spawn)
del pyautogui.FAILSAFE_POINTS[0]


MAP_NAME_REGEX_NvN = re.compile(r'(\d+).?v.?(\d+)')
MAP_NAME_REGEX_SEPARATORS = re.compile(r'[_.\s]')
MAP_NAME_REGEX_EXTRA = re.compile(r'[\'()]')
MAP_NAME_REGEX_MULTI = re.compile(r'[-]{2,}')


class GameInstanceManager:
    game_path: str
    player_name: str
    player_pass: str
    resolution: str
    histograms: dict

    game_window: Window = None

    state: GameInstanceState

    def __init__(self, game_path: str, player_name: str, player_pass: str, resolution: str, histograms: dict):
        self.game_path = game_path
        self.player_name = player_name
        self.player_pass = player_pass
        self.resolution = resolution
        self.histograms = histograms

        # Init game instance state
        self.state = GameInstanceState()

    """
    Attribute getters/setters
    """
    def get_state(self) -> GameInstanceState:
        return self.state

    def get_game_window(self) -> Window:
        return self.game_window

    """
    Functions for launching, finding and destroying/quitting a game instance
    """
    @staticmethod
    def prepare_game_launch() -> None:
        """
        BF2 will query any server in the server history upon login, significantly slowing down the login and thus the
        launch. The effect is even greater if any of the servers in the history are offline. For those, BF2 waits for
        the status query to time out. So, use bf2-conman (https://github.com/cetteup/conman/releases/tag/v0.1.5)
        to purge the server history. We also remove old demo bookmarks and purge the shader and logo cache, just to
        keep this nice and neat.
        """
        try:
            run_conman([
                '--purge-server-history',
                '--purge-old-demo-bookmarks',
                '--purge-shader-cache',
                '--purge-logo-cache'
            ])
        except subprocess.SubprocessError as e:
            logger.error(f'Failed to run pre-launch cleanup ({e})')

    def launch_instance(self, mod: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Launch a new game instance
        :return: True if game was launched successfully, else False
        """
        self.prepare_game_launch()

        szx, szy = get_resolution_window_size(self.resolution)

        # Prepare command
        command = [
            os.path.join(self.game_path, constants.BF2_EXE), '+restart', '1', '+modPath', f'mods/{mod}',
            '+playerName', self.player_name, '+playerPassword', self.player_pass,
            '+szx', str(szx), '+szy', str(szy), '+fullscreen', '0', '+wx', '5', '+wy', '5',
            '+developer', '1', '+disableShaderCache', '1', '+ignoreAsserts', '1'
        ]

        # Run command
        p = subprocess.Popen(command, close_fds=True, cwd=self.game_path)

        # Wait for game window to come up
        game_window_present, correct_params, running_mod = False, False, None
        check_count = 0
        check_limit = 5
        while p.poll() is None and not game_window_present and check_count < check_limit:
            # If we join a server with a different mod without knowing it, the game will restart with that mod
            # => update config to use whatever mod the game is now running with
            game_window_present, correct_params, running_mod = self.find_instance(mod)
            check_count += 1
            time.sleep(4)

        # If game window came up, give it some time for login etc.
        if game_window_present:
            time.sleep(6)

        return game_window_present, correct_params, running_mod

    def find_instance(self, mod: str) -> Tuple[bool, bool, Optional[str]]:
        self.game_window = find_window_by_title(constants.BF2_WINDOW_TITLE, 'BF2')

        if self.game_window is None:
            return False, False, None

        # Found a game window => validate mod and resolution match expected values
        running_mod = get_mod_from_command_line(self.game_window.pid)
        logger.debug(f'Found game is running mod "{running_mod}"')
        logger.debug(f'Expected mod is "{mod}"')

        actual_window_size = self.game_window.get_size()
        expected_window_size = get_resolution_window_size(self.resolution)
        logger.debug(f'Found game window size is {actual_window_size}')
        logger.debug(f'Expected game window size is {expected_window_size}')

        as_expected = True
        if running_mod != mod:
            logger.warning('Found game is running a different mod than expected')
            as_expected = False
        if actual_window_size != expected_window_size:
            logger.warning('Found game window is a different resolution/size than expected')
            as_expected = False

        return True, as_expected, running_mod

    def quit_instance(self) -> bool:
        if not self.open_menu():
            return False

        # Click quit menu item
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'quit-menu-item')
        time.sleep(.2)
        mouse_click_in_game_window(self.game_window)

        time.sleep(2)

        return not is_responding_pid(self.game_window.pid)

    def open_menu(self, max_attempts: int = 5, sleep: float = 1.0) -> bool:
        # Spam press ESC if menu is not already visible
        attempt = 0
        while not (in_menu := self.is_in_menu()) and attempt < max_attempts:
            auto_press_key(0x01)
            attempt += 1
            time.sleep(sleep)

        if not in_menu:
            return False

        # Reset the mouse to the center of the screen in order to not block any common OCR/histogram spots
        mouse_reset(self.game_window)

        return True

    """
    Functions for detecting game state elements
    """
    def is_game_message_visible(self) -> bool:
        return 'game message' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'game-message-header',
            image_ops=[(ImageOperation.invert, None)]
        )

    def ocr_game_message(self) -> str:
        # Get ocr result of game message content region
        return ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'game-message-text',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_in_menu(self) -> bool:
        # Get ocr result of quit menu item area
        return 'quit' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'quit-menu-item',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_multiplayer_menu_active(self) -> bool:
        return self.is_menu_item_active('multiplayer')

    def is_join_internet_menu_active(self) -> bool:
        return self.is_menu_item_active('join-internet')

    def is_menu_item_active(self, menu_item: str) -> bool:
        histogram = histogram_screenshot_region(
            self.game_window,
            *constants.COORDINATES[self.resolution]['hists']['menu'][menu_item]
        )
        delta = calc_cv2_hist_delta(
            histogram,
            self.histograms[self.resolution]['menu'][menu_item]['active']
        )

        return delta < constants.HISTCMP_MAX_DELTA

    def is_disconnect_prompt_visible(self) -> bool:
        return 'disconnect' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'disconnect-prompt-header',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_disconnect_button_visible(self) -> bool:
        return 'disconnect' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'disconnect-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_play_now_button_visible(self) -> bool:
        return 'play now' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'play-now-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_round_end_screen_visible(self) -> bool:
        round_end_screen_items = ['score-list', 'top-players', 'top-scores', 'map-briefing']
        active = [self.is_round_end_screen_item_active(item) for item in round_end_screen_items]

        # During map load, only item is active at any time. When the round just ended, all are active.
        if not (all(active) or len([a for a in active if a]) == 1):
            return False

        # Run expensive multi-ocr only after faster histogram based detection succeeded
        item_labels = ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'eor-header-items',
            image_ops=[(ImageOperation.invert, None)],
            crops=constants.COORDINATES[self.resolution]['crops']['eor-header-items']
        )

        # Due to the eor header items being transparent, ocr is not going to always detect all items
        # So, we'll take any ocr match (the strings are fairly unique)
        return any(label in item_labels for label in ['score list', 'top players', 'top scores', 'map briefing'])

    def is_round_end_screen_item_active(self, round_end_screen_item: str) -> bool:
        histogram = histogram_screenshot_region(
            self.game_window,
            *constants.COORDINATES[self.resolution]['hists']['eor'][round_end_screen_item]
        )
        delta = calc_cv2_hist_delta(
            histogram,
            self.histograms[self.resolution]['eor'][round_end_screen_item]['active']
        )

        return delta < constants.HISTCMP_MAX_DELTA

    def is_connect_to_ip_button_visible(self) -> bool:
        return 'connect to ip' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'connect-to-ip-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_join_game_button_visible(self) -> bool:
        # Reset mouse to avoid blocking ocr of button region
        mouse_reset(self.game_window)

        # Get ocr result of bottom left corner where "join game"-button would be
        return 'join game' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'join-game-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_map_loading(self) -> bool:
        # Check if join game button is present (check this first in order to avoid race condition where eor screen
        # is visible when checked but join game button is not visible because we entered the map)
        join_game_button_present = self.is_join_game_button_visible()

        # Check if game is on round end screen
        return self.is_round_end_screen_visible() and not join_game_button_present

    def is_map_briefing_visible(self) -> bool:
        return 'map briefing' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'map-briefing-header',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_spawn_menu_visible(self) -> bool:
        histogram = histogram_screenshot_region(
            self.game_window,
            *constants.COORDINATES[self.resolution]['hists']['spawn-menu']['close-button']
        )
        delta = calc_cv2_hist_delta(
            histogram,
            self.histograms[self.resolution]['spawn-menu']['close-button']
        )

        return delta < constants.HISTCMP_MAX_DELTA

    def get_map_name(self) -> str:
        # Screenshot and OCR map name area
        ocr_result = ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'eor-map-name',
            image_ops=[(ImageOperation.invert, None)]
        )

        # Make sure any weird OCR result for 2v2/NvN maps are turned into just NvN
        ocr_result = MAP_NAME_REGEX_NvN.sub('\\1v\\2', ocr_result)
        # Replace spaces/underscores/dots with dashes
        ocr_result = MAP_NAME_REGEX_SEPARATORS.sub('-', ocr_result)
        # Remove any other special characters
        ocr_result = MAP_NAME_REGEX_EXTRA.sub('', ocr_result)
        # "Merge" multiple dashes into one
        ocr_result = MAP_NAME_REGEX_MULTI.sub('-', ocr_result)

        # Convert to lower case
        ocr_result = ocr_result.lower()

        logger.debug(f'Detected map name is "{ocr_result}"')

        # Check if map is known
        # Also check while replacing first g with q, second t with i and trailing colon with e
        # to account for common ocr errors
        if ocr_result in constants.COORDINATES['spawns'].keys():
            # If block only serves to not run regex if ocr result already matches a known map
            return ocr_result
        elif (normalized := re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result)) \
                in constants.COORDINATES['spawns'].keys():
            return normalized
        elif (normalized := re.sub(r'^([^t]*?t[^t]+?)t(.*)$', '\\1i\\2', ocr_result)) \
                in constants.COORDINATES['spawns'].keys():
            return normalized
        elif (normalized := re.sub(r'^(.*?):$', '\\1e', ocr_result)) \
                in constants.COORDINATES['spawns'].keys():
            return normalized
        else:
            return ocr_result

    def get_map_size(self) -> int:
        # Screenshot and OCR map size region
        ocr_result = ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'eor-map-size',
            image_ops=[(ImageOperation.invert, None)]
        )

        map_size = -1
        # Make sure ocr result only contains numbers
        if re.match(r'^[0-9]+$', ocr_result):
            map_size = int(ocr_result)

        logger.debug(f'Detected map size is {map_size}')

        return map_size

    def get_game_mode(self) -> str:
        ocr_result = ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'eor-game-mode',
            image_ops=[(ImageOperation.invert, None)]
        )

        logger.debug(f'Detected game mode is {ocr_result.lower()}')

        return ocr_result.lower()

    def get_player_team(self) -> Optional[int]:
        # Get histograms of team selection areas
        team_selection_histograms = []
        for coord_set in constants.COORDINATES[self.resolution]['hists']['teams']:
            histogram = histogram_screenshot_region(
                self.game_window,
                *coord_set
            )
            team_selection_histograms.append(histogram)

        # Calculate histogram deltas and compare against known ones
        team = None
        for team_key in constants.TEAMS_SPAWN_MENU_LEFT:
            histogram_delta = calc_cv2_hist_delta(
                team_selection_histograms[0],
                self.histograms[self.resolution]['teams'][team_key]['active']
            )

            if histogram_delta < constants.HISTCMP_MAX_DELTA:
                team = 0
                break

        for team_key in constants.TEAMS_SPAWN_MENU_RIGHT:
            histogram_delta = calc_cv2_hist_delta(
                team_selection_histograms[1],
                self.histograms[self.resolution]['teams'][team_key]['active']
            )

            if histogram_delta < constants.HISTCMP_MAX_DELTA:
                team = 1
                break

        logger.debug(f'Detected team is {team}')

        return team

    def is_default_camera_view_visible(self) -> bool:
        map_name = self.state.get_rotation_map_name()
        # Return false if map has not been determined (yet) or is not supported
        if map_name is None or map_name not in self.histograms[self.resolution]['maps']['default-camera-view']:
            return False

        left, top, right, bottom = self.game_window.rect
        # Offset the screenshot to not include the window's title bar
        histogram = histogram_screenshot_region(
            self.game_window,
            168,
            constants.WINDOW_TITLE_BAR_HEIGHT,
            right - left - 336,
            bottom - top - 40
        )
        delta = calc_cv2_hist_delta(
            histogram,
            self.histograms[self.resolution]['maps']['default-camera-view'][map_name]
        )

        return delta < constants.DEFAULT_CAMERA_VIEW_HISTCMP_MAX_DELTA

    def is_sufficient_action_on_screen(self, screenshot_count: int = 3, screenshot_sleep: float = .55,
                                       min_delta: float = .022) -> bool:
        histograms = []

        left, top, right, bottom = self.game_window.rect

        # Take screenshots and calculate histograms
        for i in range(0, screenshot_count):
            # Offset the screenshot to not include the window's title bar
            histogram = histogram_screenshot_region(
                self.game_window,
                168,
                constants.WINDOW_TITLE_BAR_HEIGHT,
                right - left - 336,
                bottom - top - 40
            )
            histograms.append(histogram)

            # Sleep before taking next screenshot
            if i + 1 < screenshot_count:
                time.sleep(screenshot_sleep)

        histogram_deltas = []
        # Calculate histogram differences
        for j in range(0, len(histograms) - 1):
            histogram_deltas.append(calc_cv2_hist_delta(histograms[j], histograms[j + 1]))

        # Take average of deltas
        average_delta = np.average(histogram_deltas)

        logger.debug(f'Average histogram delta: {average_delta}')

        return average_delta > min_delta

    """
    Functions to interact with the game instance (=change state)
    """
    def bring_to_foreground(self) -> None:
        win32gui.ShowWindow(self.game_window.handle, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(self.game_window.handle)

    def connect_to_server(self, server_ip: str, server_port: str, server_pass: str = None) -> bool:
        if not self.is_multiplayer_menu_active():
            # Move cursor onto multiplayer menu item and click
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'multiplayer-menu-item')
            time.sleep(.2)
            mouse_click_in_game_window(self.game_window)

        if not self.is_join_internet_menu_active():
            # Move cursor onto join internet menu item and click
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'join-internet-menu-item')
            time.sleep(.2)
            mouse_click_in_game_window(self.game_window)

        check_count = 0
        check_limit = 10
        while not self.is_connect_to_ip_button_visible() and check_count < check_limit:
            check_count += 1
            time.sleep(1)

        if not self.is_connect_to_ip_button_visible():
            return False

        # Move cursor onto connect to ip button and click
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'connect-to-ip-button')
        time.sleep(.2)
        mouse_click_in_game_window(self.game_window)

        # Give field popup time to appear
        time.sleep(.3)

        # Clear out ip field
        pyautogui.press('backspace', presses=20, interval=.05)

        # Write ip
        pyautogui.write(server_ip, interval=.05)

        # Hit tab to enter port
        pyautogui.press('tab')

        # Clear out port field
        pyautogui.press('backspace', presses=10, interval=.05)

        # Write port
        pyautogui.write(server_port, interval=.05)

        time.sleep(.3)

        # Write password if required
        # Field clears itself, so need to clear manually
        if server_pass is not None:
            pyautogui.press('tab')

            pyautogui.write(server_pass, interval=.05)

            time.sleep(.3)

        # Move cursor onto ok button and click
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'connect-to-ip-ok-button')
        time.sleep(.2)
        mouse_click_in_game_window(self.game_window)

        # Successfully joining a server means leaving the menu, so wait for menu to disappear
        # (cancel further checks when a game/error message is present)
        check_count = 0
        check_limit = 16
        in_menu = True
        game_message_visible = False
        while in_menu and not game_message_visible and check_count < check_limit:
            in_menu = self.is_in_menu()
            game_message_visible = self.is_game_message_visible()
            # Game will show a "you need to disconnect first" prompt if it was still connected to a server
            if self.is_disconnect_prompt_visible():
                logger.warning('Disconnect prompt is visible, clicking "Yes" to disconnect')
                # Click "yes" in order to disconnect
                mouse_move_to_game_window_coord(self.game_window, self.resolution, 'disconnect-prompt-yes-button')
                time.sleep(.2)
                mouse_click_in_game_window(self.game_window)
                time.sleep(.5)
                # Stop checking, since we will stay in menu (game only disconnects here, we need to retry connecting)
                break
            check_count += 1
            time.sleep(1)

        return not in_menu

    def disconnect_from_server(self) -> bool:
        # Make sure disconnect button is present
        if self.is_disconnect_button_visible():
            # Move cursor onto disconnect button and click
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'disconnect-button')
            time.sleep(.2)
            mouse_click_in_game_window(self.game_window)

            # Reset mouse to avoid blocking ocr of button region
            mouse_reset(self.game_window)

            check = 0
            max_checks = 5
            while not self.is_play_now_button_visible() and check < max_checks:
                check += 1
                time.sleep(.3)

        # We should still be in the menu but see the "play now" button instead of the "disconnect" button
        return self.is_in_menu() and self.is_play_now_button_visible()

    def toggle_hud(self, direction: int) -> bool:
        return self.issue_console_command(f'renderer.drawHud {str(direction)}')

    def issue_console_command(self, command: str) -> bool:
        # Open/toggle console
        self.toggle_console()

        # Clear out command input
        attempt = 0
        max_attempts = 5
        while not (ready := self.is_console_ready()) and attempt < max_attempts:
            pyautogui.press('backspace', presses=pow((attempt + 1), 2), interval=.05)
            attempt += 1

        if not ready:
            return False

        # Write command
        pyautogui.write(command, interval=.05)
        time.sleep(.3)

        # Read command back
        written_command = self.get_console_command(len(command))
        if not is_similar_str(command, written_command.lstrip('>')):
            return False

        # Hit enter
        pyautogui.press('enter')
        time.sleep(.1)

        # X / toggle console
        self.toggle_console()

        return not self.is_console_ready()

    def is_console_ready(self) -> bool:
        # We should only see the input "prompt"
        return self.get_console_command(3) == '>'

    def get_console_command(self, characters: int) -> str:
        """
        Read current console command, including ">" prompt
        :param characters: number of characters to read
        :return: current console command (note: due to how tiny the text is,
        don't expect an exact match with the command that was put in)
        """
        # Set screenshot width based on command length (add 5px per character)
        return ocr_screenshot_region(
            self.game_window.rect[0] + constants.COORDINATES[self.resolution]['ocr']['console-command'][0],
            self.game_window.rect[1] + constants.COORDINATES[self.resolution]['ocr']['console-command'][1],
            constants.COORDINATES[self.resolution]['ocr']['console-command'][2] + characters * 6,
            constants.COORDINATES[self.resolution]['ocr']['console-command'][3]
        )

    @staticmethod
    def toggle_console() -> None:
        auto_press_key(0x1d)
        time.sleep(.25)

    @staticmethod
    def open_spawn_menu(sleep: float = 1.5) -> None:
        auto_press_key(0x1c)
        time.sleep(sleep)

    def spawn_coordinates_available(self) -> bool:
        map_name = self.state.get_rotation_map_name()
        return map_name in constants.COORDINATES['spawns'].keys() and \
               str(self.state.get_rotation_map_size()) in constants.COORDINATES['spawns'][map_name].keys() and \
               self.state.get_rotation_game_mode() == 'conquest'

    def spawn_suicide(self, randomize: bool = False) -> bool:
        # Treat spawn attempt as failed if no spawn point could be selected
        if self.is_spawn_point_selectable() and \
                (randomize and self.select_random_spawn_point() or (not randomize and self.select_spawn_point())):
            # Hit enter to spawn
            auto_press_key(0x1c)
            time.sleep(1)

            # Re-open spawn menu
            self.open_spawn_menu(.3)

            # Reset cursor again
            mouse_reset_legacy()

            # De-select spawn point
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'spawnpoint-deselect', True)
            time.sleep(0.3)
            mouse_click_in_game_window(self.game_window, legacy=True)

        # Suicide button may be visible even though we did not detect a spawn as selected
        # e.g. when spectator is still alive from a previous spawn-suicide attempt
        suicide_button_visible = self.is_suicide_button_visible()
        if suicide_button_visible:
            mouse_reset_legacy()
            # Click suicide button
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'suicide-button', True)
            time.sleep(.3)
            mouse_click_in_game_window(self.game_window, legacy=True)
            time.sleep(.5)

        # Reset mouse again to make sure it does not block any OCR attempts
        mouse_reset_legacy()

        # Make sure the button was visible before but is not any longer
        return suicide_button_visible and not self.is_suicide_button_visible()

    def select_spawn_point(self) -> bool:
        # Make sure spawning on map and size is supported
        map_name = self.state.get_rotation_map_name()
        map_size = str(self.state.get_rotation_map_size())
        if not self.spawn_coordinates_available():
            raise SpawnCoordinatesNotAvailableException

        # Reset mouse to top left corner
        mouse_reset_legacy()

        # Select default spawn based on current team
        spawn_coordinates = constants.COORDINATES['spawns'][map_name][map_size][self.state.get_round_team()]
        mouse_move_legacy(spawn_coordinates[0], spawn_coordinates[1])
        time.sleep(.3)
        mouse_click_in_game_window(self.game_window, legacy=True)

        # Try any alternate spawns if primary one is not available
        alternate_spawns = constants.COORDINATES['spawns'][map_name][str(map_size)][2:]
        if not self.is_spawn_point_selected() and len(alternate_spawns) > 0:
            logger.warning('Default spawn point could not be selected, trying alternate spawn points')
            # Iterate over alternate spawns in reverse order for team 1
            # (spawns are ordered by "likeliness" of team 0 having control over them)
            if self.state.get_round_team() == 1:
                alternate_spawns.reverse()

            # Try to select any of the alternate spawn points
            for coordinates in alternate_spawns:
                logger.debug(f'Trying spawn coordinates {coordinates}')
                mouse_reset_legacy()
                mouse_move_legacy(*coordinates)
                time.sleep(.1)
                mouse_click_in_game_window(self.game_window, legacy=True)
                time.sleep(.1)
                if self.is_spawn_point_selected():
                    break

        return self.is_spawn_point_selected()

    def select_random_spawn_point(self) -> bool:
        attempt = 0
        max_attempts = 5
        while not self.is_spawn_point_selected() and attempt < max_attempts:
            # Reset mouse to top left corner
            mouse_reset_legacy()

            # Try to select a spawn point by randomly clicking on the spawn menu map
            # (use bigger step, since clicking next to a spawn point also works)
            spawn_coordinates = random.randrange(260, 613, 22), random.randrange(50, 403, 22)
            mouse_move_legacy(spawn_coordinates[0], spawn_coordinates[1])
            time.sleep(.3)
            mouse_click_in_game_window(self.game_window, legacy=True)

            attempt += 1

        return self.is_spawn_point_selected()

    @staticmethod
    def start_spectating_via_freecam_toggle() -> None:
        auto_press_key(0x39)
        time.sleep(.2)

    def is_spawn_point_selectable(self) -> bool:
        return 'select' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'spawn-selected-text',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_spawn_point_selected(self) -> bool:
        return 'done' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'spawn-selected-text',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_suicide_button_visible(self) -> bool:
        return 'suicide' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'suicide-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def show_scoreboard(self, duration: float = .5) -> bool:
        # Press tab
        press_key(0x0f)
        time.sleep(.25)

        # Scoreboard should be visible
        if not self.is_scoreboard_visible():
            release_key(0x0f)
            return False

        time.sleep(duration)

        # Release tab
        release_key(0x0f)
        time.sleep(.25)

        # Scoreboard should no longer be visible
        return not self.is_scoreboard_visible()

    def is_scoreboard_visible(self) -> bool:
        for side in ['table-icons-left', 'table-icons-right']:
            histogram = histogram_screenshot_region(
                self.game_window,
                *constants.COORDINATES[self.resolution]['hists']['scoreboard'][side]
            )

            delta = calc_cv2_hist_delta(
                histogram,
                self.histograms[self.resolution]['scoreboard'][side]
            )

            if delta >= constants.HISTCMP_MAX_DELTA:
                return False

        return True

    @staticmethod
    def rotate_to_next_player():
        auto_press_key(0x2e)

    def join_game(self) -> None:
        # Move cursor onto join game button and click
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'join-game-button')
        time.sleep(.2)
        mouse_click_in_game_window(self.game_window)

    def close_game_message(self) -> None:
        # Move cursor onto ok button and click
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'game-message-close-button')
        time.sleep(.2)
        mouse_click_in_game_window(self.game_window)
