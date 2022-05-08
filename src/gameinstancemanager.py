import logging
import re
import time

import numpy as np
import pyautogui
import win32com.client
import win32con
import win32gui

import constants
from exceptions import UnsupportedMapException
from gameinstancestate import GameInstanceState
from helpers import Window, find_window_by_title, get_resolution_window_size, mouse_move_to_game_window_coord, \
    ocr_screenshot_game_window_region, auto_press_key, mouse_reset_legacy, mouse_move_legacy, mouse_click_legacy, \
    is_responding_pid, histogram_screenshot_region, \
    calc_cv2_hist_delta, ImageOperation

# Remove the top left corner from pyautogui failsafe points
# (avoid triggering failsafe exception due to mouse moving to top left during spawn)
del pyautogui.FAILSAFE_POINTS[0]


MAP_NAME_REGEX_NvN = re.compile(r'(\d+).?v.?(\d+)')
MAP_NAME_REGEX_SEPARATORS = re.compile(r'[_\s]')


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
    def launch_instance(self) -> bool:
        """
        Launch a new game instance via a shell (launching via shell "detaches" game process from spectator process,
        so that spectator can be restarted without having to restart the game)
        :return: True if game was launched successfully, else False
        """
        # Init shell
        shell = win32com.client.Dispatch("WScript.Shell")

        window_size = get_resolution_window_size(self.resolution)

        # Prepare command
        command = f'cmd /c start /b /d "{self.game_path}" {constants.BF2_EXE} +restart 1 ' \
                  f'+playerName "{self.player_name}" +playerPassword "{self.player_pass}" ' \
                  f'+szx {window_size[0]} +szy {window_size[1]} +fullscreen 0 +wx 5 +wy 5 ' \
                  f'+multi 1 +developer 1 +disableShaderCache 1 +ignoreAsserts 1'

        # Run command
        shell.Run(command)

        # Wait for game window to come up
        game_window_present = False
        check_count = 0
        check_limit = 5
        while not game_window_present and check_count < check_limit:
            game_window_present = self.find_instance()
            check_count += 1
            time.sleep(4)

        # If game window came up, give it some time for login etc.
        if game_window_present:
            time.sleep(6)

        return game_window_present

    def find_instance(self) -> bool:
        self.game_window = find_window_by_title(constants.BF2_WINDOW_TITLE, 'BF2')

        window_size = get_resolution_window_size(self.resolution)
        window_matches_resolution = True
        if self.game_window is not None and \
                (self.game_window.rect[2] - 21, self.game_window.rect[3] - 44) != window_size:
            logging.error('Existing game window is a different resolution/size than expected')
            window_matches_resolution = False

        return self.game_window is not None and window_matches_resolution

    def quit_instance(self) -> bool:
        menu_open = self.open_menu()

        if not menu_open:
            return False

        # Click quit menu item
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'quit-menu-item')
        time.sleep(.2)
        pyautogui.leftClick()

        time.sleep(2)

        return not is_responding_pid(self.game_window.pid)

    def open_menu(self) -> bool:
        # Spam press ESC if menu is not already visible
        attempt = 0
        max_attempts = 5
        while not self.is_in_menu() and attempt < max_attempts:
            auto_press_key(0x01)
            attempt += 1
            time.sleep(1)

        return self.is_in_menu()

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
        histogram = histogram_screenshot_region(
            self.game_window,
            *constants.COORDINATES[self.resolution]['hists']['menu']['multiplayer']
        )
        delta = calc_cv2_hist_delta(
            histogram,
            self.histograms[self.resolution]['menu']['multiplayer']['active']
        )

        return delta < constants.HISTCMP_MAX_DELTA

    def is_disconnect_button_visible(self) -> bool:
        return 'disconnect' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'disconnect-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_round_end_screen_visible(self) -> bool:
        ocr_result = ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'eor-header-items',
            image_ops=[(ImageOperation.invert, None)]
        )

        round_end_labels = ['score list', 'top players', 'top scores', 'map briefing']

        return any(round_end_label in ocr_result for round_end_label in round_end_labels)

    def is_connect_to_ip_button_visible(self) -> bool:
        return 'connect to ip' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'connect-to-ip-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_join_game_button_visible(self) -> bool:
        # Get ocr result of bottom left corner where "join game"-button would be
        return 'join game' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'join-game-button',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_map_loading(self) -> bool:
        # Check if game is on round end screen
        on_round_end_screen = self.is_round_end_screen_visible()

        # Check if join game button is present
        join_game_button_present = self.is_join_game_button_visible()

        return on_round_end_screen and not join_game_button_present

    def is_map_briefing_visible(self) -> bool:
        return 'map briefing' in ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'map-briefing-header',
            image_ops=[(ImageOperation.invert, None)]
        )

    def is_spawn_menu_visible(self) -> bool:
        # Get ocr result of "special forces" class label/name
        return 'special forces' in  ocr_screenshot_game_window_region(
            self.game_window,
            self.resolution,
            'special-forces-class-label',
            image_ops=[(ImageOperation.invert, None)]
        )

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
        # Replace spaces/underscores with dashes
        ocr_result = MAP_NAME_REGEX_SEPARATORS.sub('-', ocr_result)

        map_name = None
        # Make sure map name is valid
        # Also check while replacing first g with q to account for common ocr error
        if ocr_result.lower() in constants.COORDINATES['spawns'].keys():
            map_name = ocr_result.lower()
        elif re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result.lower()) in constants.COORDINATES['spawns'].keys():
            map_name = re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result.lower())

        return map_name

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

        return map_size

    def get_player_team(self) -> int:
        # Get histograms of team selection areas
        team_selection_histograms = []
        for coord_set in constants.COORDINATES[self.resolution]['hists']['teams']:
            histogram = histogram_screenshot_region(
                self.game_window,
                *coord_set
            )
            team_selection_histograms.append(histogram)

        # Calculate histogram deltas
        histogram_deltas = {
            'to_usmc_active': calc_cv2_hist_delta(
                team_selection_histograms[0],
                self.histograms[self.resolution]['teams']['usmc']['active']
            ),
            'to_eu_active': calc_cv2_hist_delta(
                team_selection_histograms[0],
                self.histograms[self.resolution]['teams']['eu']['active']
            ),
            'to_china_active': calc_cv2_hist_delta(
                team_selection_histograms[1],
                self.histograms[self.resolution]['teams']['china']['active'],
            ),
            'to_mec_active': calc_cv2_hist_delta(
                team_selection_histograms[1],
                self.histograms[self.resolution]['teams']['mec']['active']
            ),
        }

        # Compare histograms to constant to determine team
        team = None
        if histogram_deltas['to_usmc_active'] < constants.HISTCMP_MAX_DELTA or \
                histogram_deltas['to_eu_active'] < constants.HISTCMP_MAX_DELTA:
            # Player is on USMC/EU team
            team = 0
        elif histogram_deltas['to_china_active'] < constants.HISTCMP_MAX_DELTA or \
                histogram_deltas['to_mec_active'] < constants.HISTCMP_MAX_DELTA:
            # Player is on MEC/CHINA team
            team = 1

        return team

    def is_sufficient_action_on_screen(self, screenshot_count: int = 3, screenshot_sleep: float = .55,
                                       min_delta: float = .022) -> bool:
        histograms = []

        left, top, right, bottom = self.game_window.rect

        # Take screenshots and calculate histograms
        for i in range(0, screenshot_count):
            # Take screenshot and calculate histogram
            histogram = histogram_screenshot_region(self.game_window, 168, 31, right - left - 336, bottom - top - 40)
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

        logging.debug(f'Average histogram delta: {average_delta}')

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
            pyautogui.leftClick()

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
        pyautogui.leftClick()

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
        pyautogui.leftClick()

        # Successfully joining a server means leaving the menu, so wait for menu to disappear
        # (cancel further checks when a game/error message is present)
        check_count = 0
        check_limit = 16
        in_menu = True
        game_message_present = False
        while in_menu and not game_message_present and check_count < check_limit:
            in_menu = self.is_in_menu()
            game_message_present = self.is_game_message_visible()
            check_count += 1
            time.sleep(1)

        return not in_menu

    def disconnect_from_server(self) -> None:
        # Press ESC
        auto_press_key(0x01)
        time.sleep(5)
        # Make sure disconnect button is present
        if self.is_disconnect_button_visible():
            # Move cursor onto disconnect button and click
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'disconnect-button')
            time.sleep(.2)
            pyautogui.leftClick()

        time.sleep(1.2)

    @staticmethod
    def toggle_hud(direction: int) -> None:
        # Open/toggle console
        auto_press_key(0x1d)
        time.sleep(.1)

        # Clear out command input
        pyautogui.press('backspace', presses=2, interval=.05)

        # Write command
        pyautogui.write(f'renderer.drawHud {str(direction)}', interval=.05)
        time.sleep(.3)

        # Hit enter
        pyautogui.press('enter')
        time.sleep(.1)

        # X / toggle console
        auto_press_key(0x1d)
        time.sleep(.1)

    @staticmethod
    def open_spawn_menu(sleep: float = 1.5) -> None:
        auto_press_key(0x1c)
        time.sleep(sleep)

    def spawn_suicide(self) -> bool:
        # Treat spawn attempt as failed if no spawn point could be selected
        if self.is_spawn_point_selectable() and self.select_spawn_point():
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
            mouse_click_legacy()

        # Suicide button may be visible even though we did not detect a spawn as selected
        # e.g. when spectator is still alive from a previous spawn-suicide attempt
        if self.is_suicide_button_visible():
            mouse_reset_legacy()
            # Click suicide button
            mouse_move_to_game_window_coord(self.game_window, self.resolution, 'suicide-button', True)
            time.sleep(.3)
            mouse_click_legacy()
            time.sleep(.5)

        # Reset mouse again to make sure it does not block any OCR attempts
        mouse_reset_legacy()

        return not self.is_suicide_button_visible()

    def select_spawn_point(self) -> bool:
        # Make sure spawning on map and size is supported
        map_name = self.state.get_rotation_map_name()
        map_size = str(self.state.get_rotation_map_size())
        if map_name not in constants.COORDINATES['spawns'].keys() or \
                map_size not in constants.COORDINATES['spawns'][map_name].keys():
            raise UnsupportedMapException('No coordinates for current map/size')

        # Reset mouse to top left corner
        mouse_reset_legacy()

        # Select default spawn based on current team
        spawn_coordinates = constants.COORDINATES['spawns'][map_name][map_size][self.state.get_round_team()]
        mouse_move_legacy(spawn_coordinates[0], spawn_coordinates[1])
        time.sleep(.3)
        mouse_click_legacy()

        # Try any alternate spawns if primary one is not available
        alternate_spawns = constants.COORDINATES['spawns'][map_name][str(map_size)][2:]
        if not self.is_spawn_point_selected() and len(alternate_spawns) > 0:
            logging.warning('Default spawn point could not be selected, trying alternate spawn points')
            # Iterate over alternate spawns in reverse order for team 1
            # (spawns are ordered by "likeliness" of team 0 having control over them)
            if self.state.get_round_team() == 1:
                alternate_spawns.reverse()

            # Try to select any of the alternate spawn points
            for coordinates in alternate_spawns:
                logging.debug(f'Trying spawn coordinates {coordinates}')
                mouse_reset_legacy()
                mouse_move_legacy(*coordinates)
                time.sleep(.1)
                mouse_click_legacy()
                time.sleep(.1)
                if self.is_spawn_point_selected():
                    break

        return self.is_spawn_point_selected()

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

    @staticmethod
    def rotate_to_next_player():
        auto_press_key(0x2e)

    def join_game(self) -> None:
        # Move cursor onto join game button and click
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'join-game-button')
        time.sleep(.2)
        pyautogui.leftClick()

    def close_game_message(self) -> None:
        # Move cursor onto ok button and click
        mouse_move_to_game_window_coord(self.game_window, self.resolution, 'game-message-close-button')
        time.sleep(.2)
        pyautogui.leftClick()
