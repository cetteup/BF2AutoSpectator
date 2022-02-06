import logging
import re
import time

import cv2
import numpy as np
import pyautogui
import win32com.client
import win32con
import win32gui

from exceptions import UnsupportedMapException
from gameinstancestate import GameInstanceState
from helpers import Window, find_window_by_title, get_resolution_window_size, mouse_move_to_game_window_coord, \
    ocr_screenshot_game_window_region, auto_press_key, screenshot_game_window_region, calc_cv2_hist_from_pil_image, \
    mouse_reset_legacy, mouse_move_legacy, mouse_click_legacy, is_responding_pid
import constants

# Remove the top left corner from pyautogui failsafe points
# (avoid triggering failsafe exception due to mouse moving to left left during spawn)
del pyautogui.FAILSAFE_POINTS[0]


class GameInstanceManager:
    __game_path: str
    __player_name: str
    __player_pass: str
    __histograms: dict

    __game_window: Window = None
    __resolution: str

    __state: GameInstanceState

    def __init__(self, game_path: str, player_name: str, player_pass: str, histograms: dict):
        self.__game_path = game_path
        self.__player_name = player_name
        self.__player_pass = player_pass
        self.__histograms = histograms

        # Init game instance state
        self.__state = GameInstanceState()

    """
    Attribute getters/setters
    """
    def get_state(self) -> GameInstanceState:
        return self.__state

    def get_game_window(self) -> Window:
        return self.__game_window

    """
    Functions for launching, finding and destroying/quitting a game instance
    """
    def launch_instance(self, resolution: str) -> bool:
        """
        Launch a new game instance via a shell (launching via shell "detaches" game process from spectator process,
        so that spectator can be restarted without having to restart the game)
        :param resolution: resolution to use for the game window [720p, 900p]
        :return:
        """
        # Init shell
        shell = win32com.client.Dispatch("WScript.Shell")

        self.__resolution = resolution
        window_size = get_resolution_window_size(self.__resolution)

        # Prepare command
        command = f'cmd /c start /b /d "{self.__game_path}" {constants.BF2_EXE} +restart 1 ' \
                  f'+playerName "{self.__player_name}" +playerPassword "{self.__player_pass}" ' \
                  f'+szx {window_size[0]} +szy {window_size[1]} +fullscreen 0 +wx 5 +wy 5 ' \
                  f'+multi 1 +developer 1 +disableShaderCache 1 +ignoreAsserts 1'

        # Run command
        shell.Run(command)

        # Wait for game window to come up
        game_window_present = False
        check_count = 0
        check_limit = 5
        while not game_window_present and check_count < check_limit:
            game_window_present = self.__find_instance()
            check_count += 1
            time.sleep(4)

        # If game window came up, give it some time for login etc.
        if game_window_present:
            time.sleep(6)

        return game_window_present

    def __find_instance(self) -> bool:
        self.__game_window = find_window_by_title(constants.BF2_WINDOW_TITLE, 'BF2')

        window_size = get_resolution_window_size(self.__resolution)
        window_matches_resolution = True
        if self.__game_window is not None and \
                (self.__game_window.rect[2] - 21, self.__game_window.rect[3] - 44) != window_size:
            logging.error('Existing game window is a different resolution/size than expected')
            window_matches_resolution = False

        return self.__game_window is not None and window_matches_resolution

    def find_instance(self, resolution: str) -> bool:
        self.__resolution = resolution

        return self.__find_instance()

    def quit_instance(self) -> bool:
        # Spam press ESC if menu is not already visible
        attempt = 0
        max_attempts = 5
        while 'quit' not in ocr_screenshot_game_window_region(self.__game_window, self.__resolution,
                                                              'quit-menu-item', True) and attempt < max_attempts:
            auto_press_key(0x01)
            attempt += 1
            time.sleep(1)

        # Click quit menu item
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'quit-menu-item')
        time.sleep(.2)
        pyautogui.leftClick()

        time.sleep(2)

        return not is_responding_pid(self.__game_window.pid)

    """
    Functions for detecting game state elements
    """
    def check_for_game_message(self) -> bool:
        # Get ocr result of game message area
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'game-message-header',
            True
        )

        return 'game message' in ocr_result

    def ocr_game_message(self) -> str:
        # Get ocr result of game message content region
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'game-message-text',
            True
        )

        return ocr_result

    def check_if_in_menu(self) -> bool:
        # Get ocr result of quit menu item area
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'quit-menu-item',
            True
        )

        return 'quit' in ocr_result

    def check_if_round_ended(self) -> bool:
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'eor-header-items',
            True
        )

        round_end_labels = ['score list', 'top players', 'top scores', 'map briefing']

        return any(round_end_label in ocr_result for round_end_label in round_end_labels)

    def check_for_join_game_button(self) -> bool:
        # Get ocr result of bottom left corner where "join game"-button would be
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'join-game-button',
            True
        )

        return 'join game' in ocr_result

    def check_if_map_is_loading(self) -> bool:
        # Check if game is on round end screen
        on_round_end_screen = self.check_if_round_ended()

        # Check if join game button is present
        join_game_button_present = self.check_for_join_game_button()

        return on_round_end_screen and not join_game_button_present

    def check_for_map_briefing(self) -> bool:
        # Get ocr result of top left "map briefing" area
        map_briefing_present = 'map briefing' in ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'map-briefing-header',
            True
        )

        return map_briefing_present

    def check_if_spawn_menu_visible(self) -> bool:
        # Get ocr result of "special forces" class label/name
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'special-forces-class-label',
            True
        )

        return 'special forces' in ocr_result

    def get_map_name(self) -> str:
        # Screenshot and OCR map name area
        ocr_result = ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'eor-map-name',
            True
        )

        # Replace spaces with dashes
        ocr_result = ocr_result.replace(' ', '-')

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
            self.__game_window,
            self.__resolution,
            'eor-map-size',
            True
        )

        map_size = -1
        # Make sure ocr result only contains numbers
        if re.match(r'^[0-9]+$', ocr_result):
            map_size = int(ocr_result)

        return map_size

    def get_player_team(self) -> int:
        # Take team selection screenshots
        team_selection_screenshots = []
        for coord_set in constants.COORDINATES[self.__resolution]['hists']['teams']:
            team_selection_screenshots.append(
                screenshot_game_window_region(self.__game_window,
                                              coord_set[0], coord_set[1], coord_set[2], coord_set[3])
            )

        # Get histograms of screenshots
        team_selection_histograms = []
        for team_selection_screenshot in team_selection_screenshots:
            team_selection_histograms.append(calc_cv2_hist_from_pil_image(team_selection_screenshot))

        # Calculate histogram deltas
        histogram_deltas = {
            'to_usmc_active': cv2.compareHist(team_selection_histograms[0],
                                              self.__histograms[self.__resolution]['teams']['usmc']['active'],
                                              cv2.HISTCMP_BHATTACHARYYA),
            'to_eu_active': cv2.compareHist(team_selection_histograms[0],
                                            self.__histograms[self.__resolution]['teams']['eu']['active'],
                                            cv2.HISTCMP_BHATTACHARYYA),
            'to_china_active': cv2.compareHist(team_selection_histograms[1],
                                               self.__histograms[self.__resolution]['teams']['china']['active'],
                                               cv2.HISTCMP_BHATTACHARYYA),
            'to_mec_active': cv2.compareHist(team_selection_histograms[1],
                                             self.__histograms[self.__resolution]['teams']['mec']['active'],
                                             cv2.HISTCMP_BHATTACHARYYA),
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

        left, top, right, bottom = self.__game_window.rect

        # Take screenshots and calculate histograms
        for i in range(0, screenshot_count):
            # Take screenshot
            screenshot = pyautogui.screenshot(region=(left + 168, top + 31, right - left - 336, bottom - top - 40))
            # Calculate histogram
            histograms.append(calc_cv2_hist_from_pil_image(screenshot))

            # Sleep before taking next screenshot
            if i + 1 < screenshot_count:
                time.sleep(screenshot_sleep)

        histogram_deltas = []
        # Calculate histogram differences
        for j in range(0, len(histograms) - 1):
            histogram_deltas.append(cv2.compareHist(histograms[j], histograms[j + 1], cv2.HISTCMP_BHATTACHARYYA))

        # Take average of deltas
        average_delta = np.average(histogram_deltas)

        logging.debug(f'Average histogram delta: {average_delta}')

        return average_delta > min_delta

    """
    Functions to interact with the game instance (=change state)
    """
    def bring_to_foreground(self) -> None:
        win32gui.ShowWindow(self.__game_window.handle, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(self.__game_window.handle)

    def connect_to_server(self, server_ip: str, server_port: str, server_pass: str = None) -> bool:
        # Move cursor onto bfhq menu item and click
        # Required to reset multiplayer menu
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'bfhq-menu-item')
        time.sleep(.2)
        pyautogui.leftClick()

        time.sleep(3)

        # Move cursor onto multiplayer menu item and click
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'multiplayer-menu-item')
        time.sleep(.2)
        pyautogui.leftClick()

        check_count = 0
        check_limit = 10
        connect_to_ip_button_present = False
        while not connect_to_ip_button_present and check_count < check_limit:
            connect_to_ip_button_present = 'connect to ip' in ocr_screenshot_game_window_region(
                self.__game_window,
                self.__resolution,
                'connect-to-ip-button',
                True
            )
            check_count += 1
            time.sleep(1)

        if not connect_to_ip_button_present:
            return False

        # Move cursor onto connect to ip button and click
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'connect-to-ip-button')
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
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'connect-to-ip-ok-button')
        time.sleep(.2)
        pyautogui.leftClick()

        # Successfully joining a server means leaving the menu, so wait for menu to disappear
        # (cancel further checks when a game/error message is present)
        check_count = 0
        check_limit = 16
        in_menu = True
        game_message_present = False
        while in_menu and not game_message_present and check_count < check_limit:
            in_menu = self.check_if_in_menu()
            game_message_present = self.check_for_game_message()
            check_count += 1
            time.sleep(1)

        return not in_menu

    def disconnect_from_server(self) -> None:
        # Press ESC
        auto_press_key(0x01)
        time.sleep(5)
        # Make sure disconnect button is present
        if 'disconnect' in ocr_screenshot_game_window_region(self.__game_window, self.__resolution,
                                                             'disconnect-button', True):
            # Move cursor onto disconnect button and click
            mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'disconnect-button')
            time.sleep(.2)
            pyautogui.leftClick()

        time.sleep(1.2)

    def toggle_hud(self, direction: int) -> None:
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

    def open_spawn_menu(self) -> None:
        auto_press_key(0x1c)
        time.sleep(1.5)

    def spawn_suicide(self) -> bool:
        # Make sure spawning on map and size is supported
        map_name = self.__state.get_rotation_map_name()
        map_size = str(self.__state.get_rotation_map_size())
        if map_name not in constants.COORDINATES['spawns'].keys() or \
                map_size not in constants.COORDINATES['spawns'][map_name].keys():
            raise UnsupportedMapException('No coordinates for current map/size')

        # Reset mouse to top left corner
        mouse_reset_legacy()

        # Select default spawn based on current team
        spawn_coordinates = constants.COORDINATES['spawns'][map_name][str(map_size)][self.__state.get_round_team()]
        mouse_move_legacy(spawn_coordinates[0], spawn_coordinates[1])
        time.sleep(.3)
        mouse_click_legacy()

        # Hit enter to spawn
        auto_press_key(0x1c)
        time.sleep(1)

        # Hit enter again to re-open spawn menu
        auto_press_key(0x1c)
        time.sleep(.3)

        # Reset cursor again
        mouse_reset_legacy()

        # De-select spawn point
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'spawnpoint-deselect', True)
        time.sleep(0.3)
        mouse_click_legacy()

        # Reset cursor once more
        mouse_reset_legacy()

        suicide_button_present = 'suicide' in ocr_screenshot_game_window_region(
            self.__game_window,
            self.__resolution,
            'suicide-button',
            True
        )

        if suicide_button_present:
            # Click suicide button
            mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'suicide-button', True)
            time.sleep(.3)
            mouse_click_legacy()
            time.sleep(.5)

        return suicide_button_present

    def rotate_to_next_player(self):
        auto_press_key(0x2e)

    def join_game(self) -> None:
        # Move cursor onto join game button and click
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'join-game-button')
        time.sleep(.2)
        pyautogui.leftClick()

    def close_game_message(self) -> None:
        # Move cursor onto ok button and click
        mouse_move_to_game_window_coord(self.__game_window, self.__resolution, 'game-message-close-button')
        time.sleep(.2)
        pyautogui.leftClick()
