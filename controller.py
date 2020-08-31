import argparse
import ctypes
import os
import pickle
import re
import subprocess
import sys
import time
from datetime import datetime

import cv2
import numpy as np
import pyautogui
import pytesseract
import requests
import win32api
import win32com.client
import win32con
import win32gui
from PIL import Image, ImageOps
from bs4 import BeautifulSoup

from exceptions import *
from gameinstancestate import GameInstanceState

SendInput = ctypes.windll.user32.SendInput

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)
HISTCMP_MAX_DELTA = 0.2
COORDINATES = {
    '720p': {
        # format for click coordinates: tuple(x coordinate, y coordinate)
        # legacy mouse moves use relative offsets instead of absolute coordinates, but are stored the same way
        'clicks': {
            'bfhq-menu-item': (111, 50),
            'multiplayer-menu-item': (331, 50),
            'quit-menu-item': (1182, 50),
            'connect-to-ip-button': (111, 452),
            'connect-to-ip-ok-button': (777, 362),
            'disconnect-button': (1210, 725),
            'game-message-close-button': (806, 412),
            'join-game-button': (1210, 725),
            'spawnpoint-deselect': (250, 50),
            'suicide-button': (469, 459)
        },
        # format for ocr coordinates: tuple(x coordinate, y coordinate, width, height)
        'ocr': {
            'quit-menu-item': (1160, 42, 45, 20),
            'game-message-header': (400, 223, 130, 25),
            'game-message-text': (400, 245, 470, 18),
            'connect-to-ip-button': (50, 448, 110, 18),
            'disconnect-button': (1133, 725, 92, 16),
            'eor-header-items': (72, 82, 740, 20),
            'join-game-button': (1163, 725, 80, 16),
            'map-briefing-header': (24, 112, 115, 20),
            'special-forces-class-label': (60, 125, 140, 18),
            'eor-map-name': (769, 114, 210, 17),
            'eor-map-size': (1256, 570, 20, 17),
            'suicide-button': (940, 678, 75, 19)
        },
        'hists': {
            'teams': [(68, 69, 41, 13), (209, 69, 41, 13)]
        }
    },
    '900p': {
        # format for click coordinates: tuple(x coordinate, y coordinate)
        # legacy mouse moves use relative offsets instead of absolute coordinates, but are stored the same way
        'clicks': {
            'bfhq-menu-item': (138, 52),
            'multiplayer-menu-item': (410, 52),
            'quit-menu-item': (1468, 52),
            'connect-to-ip-button': (122, 558),
            'connect-to-ip-ok-button': (958, 440),
            'disconnect-button': (1468, 906),
            'game-message-close-button': (1002, 501),
            'join-game-button': (1468, 906),
            'spawnpoint-deselect': (250, 50),
            'suicide-button': (497, 455)
        },
        # format for ocr coordinates: tuple(x coordinate, y coordinate, width, height)
        'ocr': {
            'quit-menu-item': (1449, 47, 47, 22),
            'game-message-header': (500, 274, 152, 25),
            'game-message-text': (500, 300, 520, 20),
            'connect-to-ip-button': (62, 551, 134, 22),
            'disconnect-button': (1418, 900, 108, 20),
            'eor-header-items': (88, 94, 924, 22),
            'join-game-button': (1450, 900, 98, 18),
            'map-briefing-header': (26, 133, 141, 22),
            'special-forces-class-label': (73, 149, 164, 20),
            'eor-map-name': (956, 134, 250, 21),
            'eor-map-size': (1564, 706, 24, 18),
            'suicide-button': (1173, 841, 88, 20)
        },
        'hists': {
            'teams': [(81, 77, 60, 18), (257, 77, 60, 18)]
        }
    },
    # format for spawn coordinates: list(team 0 tuple, team 1 tuple) with tuple(x offset, y offset)
    'spawns': {
        'dalian-plant': {
            '64': [(618, 218), (296, 296)]
        },
        'strike-at-karkand': {
            '16': [(490, 390), (463, 98)],
            '64': [(382, 390), (569, 160)]
        },
        'dragon-valley': {
            '64': [(517, 56), (476, 363)]
        },
        'fushe-pass': {
            '64': [(562, 132), (253, 312)]
        },
        'daqing-oilfields': {
            '64': [(500, 346), (363, 137)]
        },
        'gulf-of-oman': {
            '16': [(416, 355), (434, 122)],
            '64': [(308, 326), (581, 132)]
        },
        'road-to-jalalabad': {
            '16': [(382, 315), (487, 133)],
            '64': [(314, 159), (569, 156)]
        },
        'wake-island-2007': {
            '64': [(359, 158), (524, 290)]
        },
        'zatar-wetlands': {
            '64': [(372, 44), (604, 336)]
        },
        'sharqi-peninsula': {
            '16': [(495, 209), (360, 284)],
            '64': [(476, 220), (321, 128)]
        },
        'kubra-dam': {
            '64': [(494, 137), (336, 330)]
        },
        'operation-clean-sweep': {
            '64': [(326, 120), (579, 249)]
        },
        'mashtuur-city': {
            '16': [(503, 316), (406, 155)],
            '64': [(563, 319), (328, 89)]
        },
        'midnight-sun': {
            '64': [(590, 207), (317, 287)]
        },
        'operation-road-rage': {
            '64': [(419, 32), (458, 407)]
        },
        'taraba-quarry': {
            '32': [(569, 346), (310, 379)]
        },
        'great-wall': {
            '32': [(529, 122), (368, 360)]
        },
        'highway-tampa': {
            '64': [(612, 246), (428, 52)]
        },
        'operation-blue-pearl': {
            '64': [(588, 268), (280, 154)]
        },
        'songhua-stalemate': {
            '64': [(565, 244), (306, 234)]
        },
        'operation-harvest': {
            '64': [(544, 393), (509, 93)]
        },
        'operation-smoke-screen': {
            '32': [(434, 98), (466, 383)]
        }
    }
}


# =============================================================================
# Print a line preceded by a timestamp
# =============================================================================
def print_log(message: object) -> None:
    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} # {str(message)}')


def list_filter_zeroes(list_with_zeroes: list) -> list:
    list_without_zeroes = filter(lambda num: num > 0, list_with_zeroes)

    return list(list_without_zeroes)


class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]


def press_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def auto_press_key(hexKeyCode):
    press_key(hexKeyCode)
    time.sleep(.08)
    release_key(hexKeyCode)


# Move mouse using old mouse_event method (relative, by "mickeys)
def mouse_move_legacy(dx: int, dy: int) -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)
    time.sleep(.08)


def mouse_move_to_game_window_coord(key: str, legacy: bool = False) -> None:
    """
    Move mouse cursor to specified game window coordinates
    :param key: key of click target in coordinates dict
    :param legacy: whether to use legacy mouse move instead of pyautogui move
    :return:
    """

    if legacy:
        mouse_move_legacy(COORDINATES[RESOLUTION]['clicks'][key][0], COORDINATES[RESOLUTION]['clicks'][key][1])
    else:
        global bf2Window
        pyautogui.moveTo(
            bf2Window['rect'][0] + COORDINATES[RESOLUTION]['clicks'][key][0],
            bf2Window['rect'][1] + COORDINATES[RESOLUTION]['clicks'][key][1]
        )


# Mouse click using old mouse_event method
def mouse_click_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_reset_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -10000, -10000)
    time.sleep(.5)


def window_enumeration_handler(hwnd, top_windows):
    """Add window title and ID to array."""
    top_windows.append({
        'handle': hwnd,
        'title': win32gui.GetWindowText(hwnd),
        'rect': win32gui.GetWindowRect(hwnd),
        'class': win32gui.GetClassName(hwnd),
        'pid': re.sub(r'^.*pid\: ([0-9]+)\)$', '\\1', win32gui.GetWindowText(hwnd))
    })


def find_window_by_title(search_title: str, search_class: str = None) -> dict:
    # Reset top windows array
    top_windows = []

    # Call window enumeration handler
    win32gui.EnumWindows(window_enumeration_handler, top_windows)
    found_window = None
    for window in top_windows:
        if search_title in window['title'] and \
                (search_class is None or search_class in window['class']):
            found_window = window

    return found_window


def is_responding_pid(pid: int) -> bool:
    """Check if a program (based on its PID) is responding"""
    cmd = 'tasklist /FI "PID eq %d" /FI "STATUS eq running"' % pid
    status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return str(pid) in str(status)


def taskkill_pid(pid: int) -> bool:
    cmd = 'taskkill /F /PID %d' % pid
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return 'has been terminated' in str(output)


def calc_cv2_hist_from_pil_image(pil_image: Image):
    # Convert PIL to cv2 image
    cv_image = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR)
    histogram = cv2.calcHist([cv_image], [0], None, [256], [0, 256])

    return histogram


def screenshot_game_window_region(x: int, y: int, w: int, h: int) -> Image:
    """
    Take a screenshot of the specified game window region (wrapper for pyautogui.screenshot)
    :param x: x coordinate of region start
    :param y: y coordinate of region start
    :param w: region width
    :param h: region height
    :return: 
    """
    
    global bf2Window
    
    return pyautogui.screenshot(region=(bf2Window['rect'][0] + x, bf2Window['rect'][1] + y, w, h))


# Take a screenshot of the given region and run the result through OCR
def ocr_screenshot_region(x: int, y: int, w: int, h: int, invert: bool = False, show: bool = False,
                          config: str = r'--oem 3 --psm 7') -> str:
    screenshot = pyautogui.screenshot(region=(x, y, w, h))
    if invert:
        screenshot = ImageOps.invert(screenshot)
    if show:
        screenshot.show()
    ocr_result = pytesseract.image_to_string(screenshot, config=config)

    # Save screenshot to debug directory and print ocr result if debugging is enabled
    if args.debug_screenshot:
        # Reference global variable
        global directories
        # Save screenshot
        screenshot.save(
            os.path.join(
                directories['debug'],
                f'ocr_screenshot-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")}.jpg'
            )
        )
        # Print ocr result
        print_log(f'OCR result: {ocr_result}')

    return ocr_result.lower()


def ocr_screenshot_game_window_region(key: str, invert: bool = False, show: bool = False,
                                      config: str = r'--oem 3 --psm 7') -> str:
    """
    Run a region of a game window through OCR (wrapper for ocr_screenshot_region)
    :param key: key of region in coordinates dict
    :param invert: whether to invert the screenshot
    :param show: whether to show the screenshot
    :param config: config/parameters for Tesseract OCR
    :return:
    """

    global bf2Window

    return ocr_screenshot_region(
        bf2Window['rect'][0] + COORDINATES[RESOLUTION]['ocr'][key][0],
        bf2Window['rect'][1] + COORDINATES[RESOLUTION]['ocr'][key][1],
        COORDINATES[RESOLUTION]['ocr'][key][2],
        COORDINATES[RESOLUTION]['ocr'][key][3],
        invert,
        show,
        config
    )


def check_for_game_message() -> bool:
    # Get ocr result of game message area
    ocr_result = ocr_screenshot_game_window_region(
        'game-message-header',
        True
    )

    return 'game message' in ocr_result


def ocr_game_message() -> str:
    # Get ocr result of game message content region
    ocr_result = ocr_screenshot_game_window_region(
        'game-message-text',
        True
    )

    return ocr_result


def check_if_round_ended() -> bool:
    ocr_result = ocr_screenshot_game_window_region(
        'eor-header-items',
        True
    )

    round_end_labels = ['score list', 'top players', 'top scores', 'map briefing']

    return any(round_end_label in ocr_result for round_end_label in round_end_labels)


def check_for_join_game_button() -> bool:
    # Get ocr result of bottom left corner where "join game"-button would be
    ocr_result = ocr_screenshot_game_window_region(
        'join-game-button',
        True
    )

    return 'join game' in ocr_result


def check_if_map_is_loading() -> bool:
    # Check if game is on round end screen
    on_round_end_screen = check_if_round_ended()

    # Check if join game button is present
    join_game_button_present = check_for_join_game_button()

    return on_round_end_screen and not join_game_button_present


def check_for_map_briefing() -> bool:
    # Get ocr result of top left "map briefing" area
    map_briefing_present = 'map briefing' in ocr_screenshot_game_window_region(
        'map-briefing-header',
        True
    )

    return map_briefing_present


def check_if_spawn_menu_visible() -> bool:
    # Get ocr result of "special forces" class label/name
    ocr_result = ocr_screenshot_game_window_region(
        'special-forces-class-label',
        True
    )

    return 'special forces' in ocr_result


def get_map_name() -> str:
    # Screenshot and OCR map name area
    ocr_result = ocr_screenshot_game_window_region(
        'eor-map-name',
        True
    )

    # Replace spaces with dashes
    ocr_result = ocr_result.replace(' ', '-')

    map_name = None
    # Make sure map name is valid
    # Also check while replacing first g with q to account for common ocr error
    if ocr_result.lower() in COORDINATES['spawns'].keys():
        map_name = ocr_result.lower()
    elif re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result.lower()) in COORDINATES['spawns'].keys():
        map_name = re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result.lower())

    return map_name


def get_map_size() -> int:
    # Screenshot and OCR map size region
    ocr_result = ocr_screenshot_game_window_region(
        'eor-map-size',
        True
    )

    map_size = -1
    # Make sure ocr result only contains numbers
    if re.match(r'^[0-9]+$', ocr_result):
        map_size = int(ocr_result)

    return map_size


def get_player_team(server_ip: str, server_port: str) -> int:
    response = requests.get(f'https://www.bf2hub.com/server/{server_ip}:{server_port}/')
    soup = BeautifulSoup(response.text, 'html.parser')
    player_link = soup.select_one('a[href="/stats/500310001"]')
    team = None
    if player_link is not None:
        td_class = player_link.find_parents('td')[-1].get('class')[-1]
        # Player's are added to USMC team by default
        # Thus, consider USMC team to be team 0, MEC to be team 1
        team = 0 if td_class == 'pl_team_2' else 1

    return team


def get_player_team_histogram() -> int:
    # Take team selection screenshots
    team_selection_screenshots = []
    for coord_set in COORDINATES[RESOLUTION]['hists']['teams']:
        team_selection_screenshots.append(
            screenshot_game_window_region(coord_set[0], coord_set[1], coord_set[2], coord_set[3])
        )

    # Get histograms of screenshots
    team_selection_histograms = []
    for team_selection_screenshot in team_selection_screenshots:
        team_selection_histograms.append(calc_cv2_hist_from_pil_image(team_selection_screenshot))

    # Calculate histogram deltas
    histogram_deltas = {
        'to_usmc_active': cv2.compareHist(team_selection_histograms[0], HISTOGRAMS[RESOLUTION]['teams']['usmc']['active'],
                                          cv2.HISTCMP_BHATTACHARYYA),
        'to_eu_active': cv2.compareHist(team_selection_histograms[0], HISTOGRAMS[RESOLUTION]['teams']['eu']['active'],
                                        cv2.HISTCMP_BHATTACHARYYA),
        'to_china_active': cv2.compareHist(team_selection_histograms[1], HISTOGRAMS[RESOLUTION]['teams']['china']['active'],
                                           cv2.HISTCMP_BHATTACHARYYA),
        'to_mec_active': cv2.compareHist(team_selection_histograms[1], HISTOGRAMS[RESOLUTION]['teams']['mec']['active'],
                                         cv2.HISTCMP_BHATTACHARYYA),
    }

    # Compare histograms to constant to determine team
    team = None
    if histogram_deltas['to_usmc_active'] < HISTCMP_MAX_DELTA or \
            histogram_deltas['to_eu_active'] < HISTCMP_MAX_DELTA:
        # Player is on USMC/EU team
        team = 0
    elif histogram_deltas['to_china_active'] < HISTCMP_MAX_DELTA or \
            histogram_deltas['to_mec_active'] < HISTCMP_MAX_DELTA:
        # Player is on MEC/CHINA team
        team = 1

    return team


def check_if_server_full(server_ip: str, server_port: str) -> bool:
    response = requests.get(f'https://www.gametracker.com/server_info/{server_ip}:{server_port}')
    soup = BeautifulSoup(response.text, 'html.parser')
    current_players = int(soup.select_one('#HTML_num_players').text)
    max_players = int(soup.select_one('#HTML_max_players').text)

    return current_players == max_players


def ocr_player_scoreboard(left: int, top: int, right: int, bottom: int) -> list:
    # Init list
    players = []

    # Press/hold tab
    press_key(0x0f)
    time.sleep(.5)

    # Take screenshot
    screenshot = pyautogui.screenshot(region=(left + 8, top + 31, right - left - 16, bottom - top - 40))
    screenshot.show()

    # Release tab
    release_key(0x0f)

    # OCR USMC players
    players.append([])
    for i in range(0, 21):
        cropped = ImageOps.crop(screenshot, (84, 114 + i * 24, 920, 101 + (20 - i) * 24))
        custom_config = r'--oem 3 --psm 7'
        ocr_result = pytesseract.image_to_string(cropped, config=custom_config)
        print(ocr_result)
        players[0].append(ocr_result.lower())

    # OCR MEC players
    players.append([])
    for i in range(0, 21):
        cropped = ImageOps.crop(screenshot, (708, 114 + i * 24, 290, 101 + (20 - i) * 24))
        custom_config = r'--oem 3 --psm 7'
        ocr_result = pytesseract.image_to_string(cropped, config=custom_config)
        print(ocr_result)
        players[1].append(ocr_result.lower())

    return players


def get_server_player_count() -> int:
    # Press/hold tab
    press_key(0x0f)
    time.sleep(.5)

    # Take screenshot
    screenshot = screenshot_game_window_region(180, 656, 647, 17)
    # Invert
    screenshot = ImageOps.invert(screenshot)

    # Release tab
    release_key(0x0f)

    # Crop team totals from screenshot
    team_count_crops = [
        ImageOps.crop(screenshot, (0, 0, 625, 0)),
        ImageOps.crop(screenshot, (625, 0, 0, 0))
    ]

    player_count = 0
    for team_count_crop in team_count_crops:
        # OCR team count
        custom_config = r'--oem 3 --psm 8'
        ocr_result = pytesseract.image_to_string(team_count_crop, config=custom_config)

        # If we only have numbers, parse to int and add to total
        if re.match(r'^[0-9]+$', ocr_result):
            player_count += int(ocr_result)

    return player_count


def ocr_player_name() -> str:
    screenshot = screenshot_game_window_region(875, 471, 110, 100)
    orc_results = []
    custom_config = r'--oem 3 --psm 7'
    for i in range(0, screenshot.height, 6):
        cropped = ImageOps.crop(screenshot, (0, i, 0, screenshot.height - (12 + i)))
        inverted = ImageOps.autocontrast(ImageOps.invert(cropped))
        orc_results.append(pytesseract.image_to_string(inverted, config=custom_config))

    return orc_results[-1]


def init_game_instance(bf2_path: str, player_name: str, player_pass: str) -> None:
    # Init shell
    shell = win32com.client.Dispatch("WScript.Shell")

    window_size = ()
    if RESOLUTION == '720p':
        window_size = (1280, 720)
    elif RESOLUTION == '900p':
        window_size = (1600, 900)

    # Prepare command
    command = f'cmd /c start /b /d "{bf2_path}" BF2.exe +restart 1 ' \
              f'+playerName "{player_name}" +playerPassword "{player_pass}" ' \
              f'+szx {window_size[0]} +szy {window_size[1]} +fullscreen 0 +wx 5 +wy 5 ' \
              f'+multi 1 +developer 1 +disableShaderCache 1 +ignoreAsserts 1'

    # Run command
    shell.Run(command)

    # Wait for game window to come up
    game_window_present = False
    check_count = 0
    check_limit = 5
    while not game_window_present and check_count < check_limit:
        game_window_present = find_window_by_title('BF2 (v1.5.3153-802.0, pid:', 'BF2') is not None
        check_count += 1
        time.sleep(4)

    # If game window came up, give it some time for login etc.
    if game_window_present:
        time.sleep(6)

    return game_window_present


def quit_game_instance() -> bool:
    global bf2Window

    # Spam press ESC if menu is not already visible
    attempt = 0
    max_attempts = 5
    while 'quit' not in ocr_screenshot_game_window_region('quit-menu-item', True) and attempt < max_attempts:
        auto_press_key(0x01)
        attempt += 1
        time.sleep(1)

    # Click quit menu item
    mouse_move_to_game_window_coord('quit-menu-item')
    time.sleep(.2)
    pyautogui.leftClick()

    time.sleep(2)

    return not is_responding_pid(int(bf2Window['pid']))


def connect_to_server(server_ip: str, server_port: str, server_pass: str = None) -> bool:
    # Move cursor onto bfhq menu item and click
    # Required to reset multiplayer menu
    mouse_move_to_game_window_coord('bfhq-menu-item')
    time.sleep(.2)
    pyautogui.leftClick()

    time.sleep(3)

    # Move cursor onto multiplayer menu item and click
    mouse_move_to_game_window_coord('multiplayer-menu-item')
    time.sleep(.2)
    pyautogui.leftClick()

    check_count = 0
    check_limit = 10
    connect_to_ip_button_present = False
    while not connect_to_ip_button_present and check_count < check_limit:
        connect_to_ip_button_present = 'connect to ip' in ocr_screenshot_game_window_region(
            'connect-to-ip-button',
            True
        )
        check_count += 1
        time.sleep(1)

    if not connect_to_ip_button_present:
        return False

    # Move cursor onto connect to ip button and click
    mouse_move_to_game_window_coord('connect-to-ip-button')
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
    mouse_move_to_game_window_coord('connect-to-ip-ok-button')
    time.sleep(.2)
    pyautogui.leftClick()

    return True


def controller_update_current_server(server_ip: str, server_port: str, server_pass: str = None, in_rotation: bool = False) -> bool:
    requestOk = False
    try:
        response = requests.post(f'{args.controller_base_uri}/servers/current', data={
            'app_key': args.controller_app_key,
            'ip': server_ip,
            'port': server_port,
            'password': server_pass,
            'in_rotation': str(in_rotation).lower()
        })

        if response.status_code == 200:
            requestOk = True
    except Exception as e:
        print_log(e)

    return requestOk


def controller_get_join_server() -> dict:
    join_sever = None
    try:
        response = requests.get(f'{args.controller_base_uri}/servers/join')

        if response.status_code == 200:
            join_sever = response.json()
    except Exception as e:
        print_log(e)

    return join_sever


def disconnect_from_server() -> None:
    # Press ESC
    auto_press_key(0x01)
    time.sleep(5)
    # Make sure disconnect button is present
    if 'disconnect' in ocr_screenshot_game_window_region('disconnect-button', True):
        # Move cursor onto disconnect button and click
        mouse_move_to_game_window_coord('disconnect-button')
        time.sleep(.2)
        pyautogui.leftClick()

    time.sleep(1.2)


def close_game_message() -> None:
    # Move cursor onto ok button and click
    mouse_move_to_game_window_coord('game-message-close-button')
    time.sleep(.2)
    pyautogui.leftClick()


def join_game() -> None:
    # Move cursor onto join game button and click
    mouse_move_to_game_window_coord('join-game-button')
    time.sleep(.2)
    pyautogui.leftClick()


def spawn_suicide(map_name: str, map_size: int, team: int) -> bool:
    # Make sure spawning on map and size is supported
    if map_name not in COORDINATES['spawns'].keys() or \
            str(map_size) not in COORDINATES['spawns'][map_name].keys():
        raise UnsupportedMapException('No coordinates for current map/size')

    # Reset mouse to top left corner
    mouse_reset_legacy()

    # Select default spawn based on current team
    spawn_coordinates = COORDINATES['spawns'][map_name][str(map_size)][team]
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
    mouse_move_to_game_window_coord('spawnpoint-deselect', True)
    time.sleep(0.3)
    mouse_click_legacy()

    # Reset cursor once more
    mouse_reset_legacy()

    suicide_button_present = 'suicide' in ocr_screenshot_game_window_region(
        'suicide-button',
        True
    )

    if suicide_button_present:
        # Click suicide button
        mouse_move_to_game_window_coord('suicide-button', True)
        time.sleep(.3)
        mouse_click_legacy()
        time.sleep(.5)

    return suicide_button_present


def toggle_hud(direction: int):
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


def is_sufficient_action_on_screen(screenshot_count: int = 3, screenshot_sleep: float = .55,
                                   min_delta: float = .022) -> bool:
    histograms = []

    global bf2Window
    left, top, right, bottom = bf2Window['rect']

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

    if args.debug_log:
        print_log(f'Average histogram delta: {average_delta}')

    return average_delta > min_delta


parser = argparse.ArgumentParser(description='Launch and control a Battlefield 2 spectator instance')
parser.add_argument('--version', action='version', version='bf2-auto-spectator v0.2.1')
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
parser.add_argument('--no-start', dest='start_game', action='store_false')
parser.add_argument('--no-rtl-limit', dest='limit_rtl', action='store_false')
parser.add_argument('--debug-log', dest='debug_log', action='store_true')
parser.add_argument('--debug-screenshot', dest='debug_screenshot', action='store_true')
parser.set_defaults(start_game=True, limit_rtl=True, debug_log=False, debug_screenshot=False, use_controller=False)
args = parser.parse_args()

# Init global vars/settings
pytesseract.pytesseract.tesseract_cmd = os.path.join(args.tesseract_path, 'tesseract.exe')
top_windows = []
directories = {
    'root': os.path.dirname(os.path.realpath(__file__))
}

RESOLUTION = args.game_res

# Remove the top left corner from pyautogui failsafe points
# (avoid triggering failsafe exception due to mouse moving to left left during spawn)
del pyautogui.FAILSAFE_POINTS[0]

# Make sure provided paths are valid
if not os.path.isfile(pytesseract.pytesseract.tesseract_cmd):
    sys.exit(f'Could not find tesseract.exe in given install folder: {args.tesseract_path}')
elif not os.path.isfile(os.path.join(args.game_path, 'BF2.exe')):
    sys.exit(f'Could not find BF2.exe in given game install folder: {args.game_path}')

# Load pickles
print_log('Loading pickles')
directories['pickle'] = os.path.join(directories['root'], 'pickle')
with open(os.path.join(directories['pickle'], 'histograms.pickle'), 'rb') as histogramFile:
    HISTOGRAMS = pickle.load(histogramFile)

# Init debug directory if debugging is enabled
if args.debug_screenshot:
    directories['debug'] = os.path.join(directories['root'], 'debug')
    # Create debug output dir if needed
    if not os.path.isdir(directories['debug']):
        os.mkdir(directories['debug'])

# Init game instance state store
gameInstanceState = GameInstanceState(args.server_ip, args.server_port, args.server_pass)

# Check whether the controller has a server join
if args.use_controller:
    print_log('Checking for join server on controller')
    joinServer = controller_get_join_server()
    if joinServer is not None and \
            (joinServer['ip'] != gameInstanceState.get_server_ip() or
             str(joinServer['gamePort']) != gameInstanceState.get_server_port()):
        # Spectator is supposed to be on different server
        print_log('Controller has a server to join')
        gameInstanceState.set_server_ip(joinServer['ip'])
        gameInstanceState.set_server_port(str(joinServer['gamePort']))
        gameInstanceState.set_server_password(joinServer['password'])

# Init game instance if requested
if args.start_game:
    print_log('Initializing spectator game instance')
    init_game_instance(
        args.game_path,
        args.player_name,
        args.player_pass
    )

# Find BF2 window
print_log('Finding BF2 window')
bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:', 'BF2')
print_log(f'Found window: {bf2Window}')

# Connect to server
try:
    win32gui.ShowWindow(bf2Window['handle'], win32con.SW_SHOW)
    win32gui.SetForegroundWindow(bf2Window['handle'])

    # Connect to server
    print_log('Connecting to server')
    connected = connect_to_server(
        gameInstanceState.get_server_ip(),
        gameInstanceState.get_server_port(),
        gameInstanceState.get_server_password()
    )
    time.sleep(5)
    gameInstanceState.set_spectator_on_server(connected)
except Exception as e:
    print_log('BF2 window is gone, restart required')
    print_log(str(e))
    gameInstanceState.set_error_restart_required(True)

# Update controller
if args.use_controller:
    controller_update_current_server(
        gameInstanceState.get_server_ip(),
        gameInstanceState.get_server_port(),
        gameInstanceState.get_server_password()
    )

# Start with 4 to switch away from dead spectator right away
iterationsOnPlayer = 5
while True:
    # Try to bring BF2 window to foreground
    if not gameInstanceState.error_restart_required():
        try:
            win32gui.ShowWindow(bf2Window['handle'], win32con.SW_SHOW)
            win32gui.SetForegroundWindow(bf2Window['handle'])
        except Exception as e:
            print_log('BF2 window is gone, restart required')
            print_log(str(e))
            gameInstanceState.set_error_restart_required(True)

    # Check if game froze
    if not gameInstanceState.error_restart_required() and not is_responding_pid(int(bf2Window['pid'])):
        print_log('Game froze, checking unresponsive count')
        # Game will temporarily freeze when map load finishes or when joining server, so don't restart right away
        if gameInstanceState.get_error_unresponsive_count() < 3:
            print_log('Unresponsive count below limit, giving time to recover')
            # Increase unresponsive count
            gameInstanceState.increase_error_unresponsive_count()
            # Check again in 2 seconds
            time.sleep(2)
            continue
        else:
            print_log('Unresponsive count exceeded limit, scheduling restart')
            gameInstanceState.set_error_restart_required(True)
    elif not gameInstanceState.error_restart_required() and gameInstanceState.get_error_unresponsive_count() > 0:
        print_log('Game recovered from temp freeze, resetting unresponsive count')
        # Game got it together, reset unresponsive count
        gameInstanceState.reset_error_unresponsive_count()

    # Check for (debug assertion) error window
    if not gameInstanceState.error_restart_required() and find_window_by_title('BF2 Error') is not None:
        print_log('BF2 Error window present, scheduling restart')
        gameInstanceState.set_error_restart_required(True)

    # Start a new game instance if required
    if gameInstanceState.rtl_restart_required() or gameInstanceState.error_restart_required():
        if bf2Window is not None and gameInstanceState.rtl_restart_required():
            # Quit out of current instnace
            print_log('Quitting existing game instance')
            quitSuccessful = quit_game_instance()
            print_log(f'Quit successful: {quitSuccessful}')
            gameInstanceState.set_rtl_restart_required(False)
            # If quit was not successful, switch to error restart
            if not quitSuccessful:
                print_log('Quitting existing game instance failed, switching to error restart')
                gameInstanceState.set_error_restart_required(True)
        # Don't use elif here so error restart can be executed right after a failed quit attempt
        if bf2Window is not None and gameInstanceState.error_restart_required():
            # Kill any remaining instance by pid
            print_log('Killing existing game instance')
            killed = taskkill_pid(int(bf2Window['pid']))
            print_log(f'Instance killed: {killed}')
            # Give Windows time to actually close the window
            time.sleep(3)

        # Init game new game instance
        init_game_instance(
            args.game_path,
            args.player_name,
            args.player_pass
        )
        # Update window dict
        bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:', 'BF2')

        # Connect to server
        try:
            win32gui.ShowWindow(bf2Window['handle'], win32con.SW_SHOW)
            win32gui.SetForegroundWindow(bf2Window['handle'])

            # Connect to server
            print_log('Connecting to server')
            connected = connect_to_server(
                gameInstanceState.get_server_ip(),
                gameInstanceState.get_server_port(),
                gameInstanceState.get_server_password()
            )
            time.sleep(5)
            # Reset state
            gameInstanceState.restart_reset()
            gameInstanceState.set_spectator_on_server(connected)
        except Exception as e:
            print_log('BF2 window is gone, restart required')
            print_log(str(e))
        continue

    # Make sure we are still in the game
    gameMessagePresent = check_for_game_message()
    if gameMessagePresent:
        print_log('Game message present, ocr-ing message')
        gameMessage = ocr_game_message()

        # Close game message to enable actions
        close_game_message()

        if 'full' in gameMessage:
            print_log('Server full, trying to rejoin in 30 seconds')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
            # Connect to server waits 10, wait another 20 = 30
            time.sleep(20)
        elif 'kicked' in gameMessage:
            print_log('Got kicked, trying to rejoin')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
        elif 'banned' in gameMessage:
            sys.exit('Got banned, contact server admin')
        elif 'connection' in gameMessage and 'lost' in gameMessage or \
                'failed to connect' in gameMessage:
            print_log('Connection lost, trying to reconnect')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
        elif 'modified content' in gameMessage:
            print_log('Got kicked for modified content, trying to rejoin')
            # Update state
            gameInstanceState.set_spectator_on_server(False)
        elif 'invalid ip address' in gameMessage:
            print_log('Join by ip dialogue bugged, restart required')
            # Set restart flag
            gameInstanceState.set_error_restart_required(True)
        else:
            sys.exit(gameMessage)

        continue

    # If we are using a controller, check if server switch is required and possible
    # (spectator not on server or fully in game)
    if args.use_controller and (not gameInstanceState.spectator_on_server() or
                                (gameInstanceState.spectator_on_server() and gameInstanceState.rotation_on_map() and iterationsOnPlayer == 5)):
        print_log('Checking for join server on controller')
        joinServer = controller_get_join_server()
        # Update server and switch if spectator is supposed to be on a different server of password was updated
        if joinServer is not None and \
                (joinServer['ip'] != gameInstanceState.get_server_ip() or
                 str(joinServer['gamePort']) != gameInstanceState.get_server_port() or
                 joinServer['password'] != gameInstanceState.get_server_password()):
            # Spectator is supposed to be on different server
            print_log('Controller has a server to join')
            gameInstanceState.set_server_ip(joinServer['ip'])
            gameInstanceState.set_server_port(str(joinServer['gamePort']))
            gameInstanceState.set_server_password(joinServer['password'])
            gameInstanceState.set_spectator_on_server(False)
            print_log('Queued server switch, disconnecting from current server')
            disconnect_from_server()
        elif gameInstanceState.spectator_on_server():
            controller_update_current_server(
                gameInstanceState.get_server_ip(),
                gameInstanceState.get_server_port(),
                gameInstanceState.get_server_password()
            )

    # Player is not on server, check if rejoining is possible and makes sense
    if not gameInstanceState.spectator_on_server():
        # Check number of free slots
        # TODO
        # (Re-)connect to server
        print_log('(Re-)Connecting to server')
        connected = connect_to_server(
            gameInstanceState.get_server_ip(),
            gameInstanceState.get_server_port(),
            gameInstanceState.get_server_password()
        )
        # Treat re-connecting as map rotation (state wise)
        gameInstanceState.map_rotation_reset()
        time.sleep(5)
        # Update state
        gameInstanceState.set_spectator_on_server(connected)
        # Update controller
        if connected and args.use_controller:
            controller_update_current_server(
                gameInstanceState.get_server_ip(),
                gameInstanceState.get_server_port(),
                gameInstanceState.get_server_password()
            )
        continue

    onRoundFinishScreen = check_if_round_ended()
    mapIsLoading = check_if_map_is_loading()
    mapBriefingPresent = check_for_map_briefing()

    if args.limit_rtl and onRoundFinishScreen and gameInstanceState.get_round_num() >= args.instance_rtl:
        print_log('Game instance has reached rtl limit, restart required')
        gameInstanceState.set_rtl_restart_required(True)
    elif mapIsLoading:
        print_log('Map is loading')
        # Reset state once if it still reflected to be on the (same) map
        if gameInstanceState.rotation_on_map():
            print_log('Performing map rotation reset')
            gameInstanceState.map_rotation_reset()
        iterationsOnPlayer = 5
        time.sleep(3)
    elif mapBriefingPresent:
        print_log('Map briefing present, checking map')
        currentMapName = get_map_name()
        currentMapSize = get_map_size()

        # Update map state if relevant and required
        if currentMapName is not None and currentMapSize != -1 and \
                (currentMapName != gameInstanceState.get_rotation_map_name() or
                 currentMapSize != gameInstanceState.get_rotation_map_size()):
            print_log(f'Updating map state: {currentMapName}; {currentMapSize}')
            gameInstanceState.set_rotation_map_name(currentMapName)
            gameInstanceState.set_rotation_map_size(currentMapSize)

            # Give go-ahead for active joining
            print_log('Enabling active joining')
            gameInstanceState.set_active_join_possible(True)

        if gameInstanceState.active_join_possible():
            # Check if join game button is present
            print_log('Could actively join, checking for button')
            joinGameButtonPresent = check_for_join_game_button()

            if joinGameButtonPresent:
                # TODO
                pass

        time.sleep(3)
    elif onRoundFinishScreen:
        print_log('Game is on round finish screen')
        # Reset state
        gameInstanceState.round_end_reset()
        # Set counter to 4 again to skip spectator
        iterationsOnPlayer = 5
        time.sleep(3)
    elif not onRoundFinishScreen and not gameInstanceState.round_spawned():
        # Re-enable hud if required
        if gameInstanceState.hud_hidden():
            # Give game time to swap teams
            time.sleep(3)
            # Re-enable hud
            print_log('Enabling hud')
            toggle_hud(1)
            # Update state
            gameInstanceState.set_hud_hidden(False)
            time.sleep(1)

        spawnMenuVisible = check_if_spawn_menu_visible()
        if not spawnMenuVisible:
            print_log('Spawn menu not visible, opening with enter')
            auto_press_key(0x1c)
            time.sleep(1.5)
            # Force another attempt re-enable hud
            gameInstanceState.set_hud_hidden(True)
            continue

        print_log('Determining team')
        currentTeam = get_player_team_histogram()
        if currentTeam is not None and \
                gameInstanceState.get_rotation_map_name() is not None and \
                gameInstanceState.get_rotation_map_size() != -1:
            gameInstanceState.set_round_team(currentTeam)
            print_log(f'Current team: {"USMC" if gameInstanceState.get_round_team() == 0 else "MEC/CHINA"}')
            print_log('Spawning once')
            try:
                spawnSucceeded = spawn_suicide(
                    gameInstanceState.get_rotation_map_name(),
                    gameInstanceState.get_rotation_map_size(),
                    gameInstanceState.get_round_team()
                )
                print_log('Spawn succeeded' if spawnSucceeded else 'Spawn failed, retrying')
                gameInstanceState.set_round_spawned(spawnSucceeded)
            except UnsupportedMapException as e:
                print_log('Spawning not supported on current map/size')
                # Wait map out by "faking" spawn
                gameInstanceState.set_round_spawned(True)
        elif gameInstanceState.get_rotation_map_name() is not None and \
                gameInstanceState.get_rotation_map_size() != -1:
            print_log('Failed to determine current team, retrying')
            # Force another attempt re-enable hud
            gameInstanceState.set_hud_hidden(True)
            time.sleep(2)
            continue
        else:
            # Map detection failed, force reconnect
            print_log('Map detection failed, disconnecting')
            disconnect_from_server()
            # Update state
            gameInstanceState.set_spectator_on_server(False)
            continue
    elif not onRoundFinishScreen and not gameInstanceState.hud_hidden():
        print_log('Hiding hud')
        toggle_hud(0)
        gameInstanceState.set_hud_hidden(True)
        # Increase round number/counter
        gameInstanceState.increase_round_num()
        print_log(f'Entering round #{gameInstanceState.get_round_num()} using this instance')
        # Spectator has "entered" map, update state accordingly
        gameInstanceState.set_rotation_on_map(True)
    elif not onRoundFinishScreen and iterationsOnPlayer < 5:
        # Check if player is afk
        if not is_sufficient_action_on_screen():
            print_log('Insufficient action on screen')
            iterationsOnPlayer = 5
        else:
            print_log('Nothing to do, stay on player')
            iterationsOnPlayer += 1
            time.sleep(2)
    elif not onRoundFinishScreen:
        print_log('Rotating to next player')
        auto_press_key(0x2e)
        iterationsOnPlayer = 0

    # serverIsFull = get_server_player_count() == 64
    # print_log(f'Server is full {serverIsFull}')
    # if serverIsFull and gameInstanceState.spectator_on_server():
    #     disconnect_from_server()
    #     gameInstanceState.set_spectator_on_server(False)
    #     time.sleep(30)
