import ctypes
import os
import re
import subprocess
import time
import argparse
import sys

import pyautogui
import pytesseract
import requests
import win32com.client
import win32gui
import win32api
import win32con
from PIL import ImageOps
from bs4 import BeautifulSoup

from gameinstancestate import GameInstanceState

SendInput = ctypes.windll.user32.SendInput

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)
FREECAM_SERVERS = [
    '185.107.96.105',
    '185.107.96.106'
]
HISTOGRAMS = {
    'teams': {
        'usmc': {
            'active': [102, 10, 2, 4, 1, 6, 6, 3, 3, 3, 3, 4, 1, 1, 3, 4, 4, 2, 5, 1, 6, 3, 5, 1, 1, 6, 4, 1, 1, 1, 4,
                       1, 1, 2, 3, 5, 1, 5, 4, 11, 2, 1, 5, 4, 5, 3, 3, 10, 4, 5, 4, 1, 1, 6, 1, 3, 2, 10, 1, 5, 3, 4,
                       1, 2, 3, 3, 2, 4, 5, 2, 3, 5, 4, 9, 1, 5, 1, 2, 2, 4, 4, 3, 6, 4, 4, 2, 8, 6, 7, 2, 3, 4, 3, 3,
                       3, 3, 4, 8, 4, 3, 8, 4, 2, 7, 1, 1, 2, 5, 3, 6, 3, 3, 6, 6, 3, 4, 1, 7, 2, 102, 10, 2, 4, 1, 6,
                       6, 3, 3, 3, 2, 4, 1, 1, 4, 4, 4, 2, 5, 1, 3, 4, 4, 3, 2, 3, 6, 1, 1, 1, 1, 1, 4, 1, 1, 1, 3, 5,
                       4, 3, 13, 3, 1, 5, 4, 5, 3, 3, 10, 4, 5, 4, 1, 6, 1, 1, 3, 2, 10, 1, 5, 3, 4, 1, 1, 3, 1, 3, 2,
                       4, 5, 2, 3, 2, 6, 3, 7, 2, 5, 1, 3, 4, 4, 3, 1, 8, 4, 1, 9, 4, 9, 2, 2, 5, 1, 3, 5, 2, 6, 5, 4,
                       3, 2, 6, 3, 4, 2, 7, 1, 1, 5, 4, 4, 4, 4, 1, 6, 6, 3, 4, 1, 7, 2, 102, 10, 2, 3, 2, 6, 6, 2, 4,
                       2, 1, 3, 4, 1, 1, 3, 4, 4, 1, 2, 5, 6, 1, 4, 3, 1, 1, 6, 3, 1, 1, 1, 1, 1, 4, 1, 1, 1, 3, 5, 1,
                       5, 4, 10, 3, 1, 5, 5, 5, 2, 3, 10, 2, 5, 2, 4, 1, 1, 6, 1, 4, 9, 2, 1, 3, 4, 2, 3, 1, 2, 2, 1, 3,
                       3, 3, 5, 2, 2, 3, 3, 4, 9, 2, 4, 1, 2, 2, 4, 4, 1, 3, 5, 4, 4, 9, 4, 3, 7, 2, 1, 5, 1, 3, 5, 1,
                       3, 4, 5, 4, 3, 3, 5, 6, 3, 7, 1, 1, 2, 5, 2, 4, 3, 3, 3, 3, 4, 6, 2, 4, 1, 7, 2],
            'inactive': [23, 3, 8, 2, 6, 7, 62, 11, 2, 3, 2, 2, 8, 5, 2, 1, 3, 1, 1, 2, 1, 3, 2, 6, 2, 2, 1, 4, 4, 4, 4,
                         1, 6, 1, 1, 1, 1, 1, 4, 1, 1, 1, 3, 5, 3, 4, 1, 12, 2, 1, 1, 5, 5, 1, 6, 4, 1, 10, 3, 4, 1, 4,
                         3, 3, 1, 1, 3, 3, 8, 2, 5, 3, 2, 3, 3, 1, 3, 3, 1, 2, 5, 1, 2, 3, 1, 6, 4, 6, 1, 1, 5, 2, 6, 3,
                         1, 5, 4, 4, 3, 1, 9, 2, 6, 6, 2, 1, 5, 1, 6, 2, 2, 6, 1, 7, 4, 2, 7, 5, 2, 1, 8, 1, 5, 2, 3, 3,
                         4, 4, 2, 5, 6, 3, 4, 1, 7, 2, 23, 3, 8, 8, 1, 7, 64, 11, 4, 3, 9, 4, 3, 2, 2, 2, 2, 4, 3, 4, 2,
                         5, 1, 6, 4, 3, 6, 2, 1, 1, 2, 4, 2, 2, 4, 4, 5, 5, 11, 1, 7, 5, 5, 4, 11, 3, 5, 5, 4, 2, 3, 5,
                         9, 6, 3, 5, 2, 2, 4, 2, 2, 6, 3, 3, 8, 4, 5, 5, 1, 5, 4, 4, 6, 6, 4, 11, 5, 7, 3, 6, 3, 5, 5,
                         4, 8, 4, 2, 9, 5, 3, 6, 8, 5, 4, 5, 7, 6, 6, 1, 7, 1, 1, 1, 1, 7, 5, 9, 7, 9, 8, 5, 7, 4, 12,
                         2, 8, 10, 4, 8, 5, 10, 13, 4, 11, 5, 7, 5, 11, 6, 7, 6, 2, 10, 4, 3, 3, 3, 7, 12, 5, 10, 2, 10,
                         11, 5, 8, 6, 7, 15, 5, 6, 2, 5, 7, 2, 4, 9, 4, 7, 5, 7, 7, 4, 6, 23, 1, 9, 3, 16, 2, 17, 62]
        },
        'mec': {
            'active': [205, 7, 1, 2, 2, 1, 2, 3, 3, 3, 5, 7, 2, 3, 4, 2, 3, 5, 3, 1, 1, 1, 3, 1, 2, 1, 3, 1, 2, 1, 2, 1,
                       1, 3, 2, 2, 2, 3, 4, 4, 2, 3, 7, 1, 1, 1, 2, 3, 3, 2, 5, 1, 1, 2, 4, 2, 2, 4, 3, 2, 3, 10, 7, 11,
                       5, 2, 5, 2, 1, 9, 1, 1, 2, 3, 1, 3, 3, 2, 2, 2, 4, 2, 1, 1, 4, 1, 1, 10, 3, 6, 2, 3, 4, 4, 5, 1,
                       3, 3, 4, 1, 2, 2, 2, 3, 5, 5, 2, 3, 4, 1, 1, 3, 1, 6, 205, 7, 1, 2, 2, 1, 2, 3, 3, 3, 2, 9, 1, 2,
                       3, 4, 2, 3, 2, 4, 2, 1, 1, 1, 1, 3, 1, 2, 2, 2, 1, 1, 1, 2, 2, 3, 2, 4, 1, 4, 2, 2, 2, 2, 3, 7,
                       1, 1, 1, 2, 2, 3, 1, 2, 5, 1, 1, 2, 4, 2, 2, 4, 1, 4, 3, 10, 7, 11, 5, 2, 5, 2, 2, 8, 2, 1, 2, 3,
                       3, 3, 2, 4, 1, 5, 1, 2, 4, 1, 8, 2, 3, 6, 3, 4, 2, 5, 5, 1, 2, 3, 4, 1, 2, 2, 4, 3, 7, 1, 2, 3,
                       4, 1, 1, 3, 1, 6, 205, 7, 1, 2, 1, 1, 1, 1, 2, 4, 1, 3, 2, 9, 1, 2, 3, 4, 2, 5, 3, 3, 1, 1, 1, 3,
                       1, 1, 2, 3, 1, 1, 1, 1, 2, 1, 1, 2, 1, 2, 2, 2, 3, 2, 2, 4, 2, 1, 2, 7, 1, 2, 2, 2, 1, 3, 2, 5,
                       2, 2, 1, 5, 2, 4, 1, 4, 3, 4, 11, 2, 11, 5, 2, 4, 1, 2, 1, 9, 2, 2, 3, 1, 3, 3, 1, 1, 2, 2, 4, 2,
                       1, 1, 4, 1, 1, 8, 2, 3, 6, 2, 3, 2, 2, 5, 4, 1, 1, 2, 1, 2, 4, 1, 2, 2, 2, 2, 3, 3, 5, 2, 2, 2,
                       4, 3, 1, 1, 6],
            'inactive': [23, 15, 2, 1, 14, 2, 15, 141, 6, 3, 3, 1, 1, 1, 1, 3, 2, 1, 1, 3, 2, 2, 6, 1, 1, 3, 3, 2, 2, 1,
                         2, 2, 1, 1, 3, 1, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1, 3, 1, 2, 1, 3, 1, 1, 3, 4, 1, 1, 3, 5, 3, 2, 1,
                         3, 1, 3, 1, 6, 1, 2, 1, 6, 3, 6, 4, 2, 1, 9, 7, 10, 2, 5, 4, 1, 1, 2, 8, 1, 1, 1, 2, 2, 2, 4,
                         1, 2, 2, 2, 2, 4, 1, 1, 4, 1, 1, 8, 4, 7, 3, 3, 3, 5, 4, 1, 1, 2, 5, 2, 1, 2, 2, 2, 3, 2, 7, 1,
                         2, 3, 4, 1, 1, 3, 1, 6, 23, 16, 2, 16, 1, 15, 145, 5, 2, 3, 1, 3, 2, 4, 2, 3, 6, 4, 3, 3, 2, 3,
                         1, 1, 1, 1, 4, 1, 2, 1, 1, 3, 3, 3, 3, 3, 4, 1, 4, 2, 3, 2, 2, 6, 2, 3, 3, 4, 1, 6, 3, 5, 2, 9,
                         5, 2, 10, 6, 12, 6, 4, 2, 2, 8, 1, 3, 3, 4, 3, 2, 3, 6, 2, 4, 2, 8, 5, 6, 2, 4, 5, 4, 4, 3, 2,
                         3, 3, 2, 5, 4, 7, 3, 4, 4, 1, 4, 6, 6, 2, 3, 5, 5, 8, 6, 3, 7, 3, 3, 8, 5, 6, 2, 9, 9, 5, 3, 4,
                         5, 3, 6, 4, 4, 9, 4, 5, 12, 17, 10, 4, 4, 5, 3, 6, 5, 4, 1, 4, 5, 4, 4, 3, 5, 6, 3, 4, 5, 1, 3,
                         5, 4, 4, 4, 1, 6, 3, 6, 6, 3, 1, 30, 2, 17, 3, 14, 2, 20, 142]
        },
        'china': {
            'active': [135, 2, 4, 1, 4, 2, 5, 1, 1, 2, 3, 4, 6, 1, 2, 3, 7, 7, 4, 2, 2, 3, 1, 3, 2, 3, 4, 3, 1, 2, 2, 1,
                       5, 2, 2, 2, 1, 2, 3, 4, 1, 3, 4, 1, 12, 5, 1, 3, 1, 1, 1, 4, 3, 3, 1, 4, 5, 3, 3, 2, 4, 2, 1, 1,
                       3, 2, 2, 4, 2, 3, 6, 3, 9, 4, 2, 1, 3, 2, 13, 3, 2, 10, 2, 6, 4, 3, 2, 8, 4, 1, 4, 4, 3, 3, 3, 4,
                       5, 5, 4, 10, 3, 5, 2, 1, 2, 11, 2, 1, 2, 4, 13, 3, 10, 2, 3, 1, 6, 135, 2, 4, 1, 4, 2, 5, 1, 1,
                       1, 3, 4, 3, 5, 2, 3, 7, 3, 8, 2, 1, 1, 1, 3, 1, 4, 3, 2, 4, 2, 3, 1, 1, 5, 2, 2, 2, 1, 3, 2, 2,
                       2, 3, 3, 2, 1, 12, 5, 1, 3, 1, 1, 3, 2, 3, 3, 1, 4, 5, 3, 3, 2, 3, 2, 2, 1, 3, 2, 2, 4, 2, 3, 3,
                       3, 1, 5, 10, 1, 2, 3, 2, 13, 5, 2, 8, 3, 5, 3, 4, 2, 6, 2, 4, 4, 4, 4, 5, 1, 9, 2, 3, 4, 10, 3,
                       5, 2, 2, 9, 3, 3, 2, 4, 13, 3, 10, 2, 3, 1, 6, 135, 2, 4, 3, 2, 2, 5, 1, 1, 2, 2, 4, 1, 6, 3, 3,
                       7, 3, 4, 4, 2, 1, 1, 3, 1, 1, 4, 3, 2, 4, 1, 1, 2, 1, 1, 1, 5, 3, 1, 2, 1, 2, 3, 2, 2, 1, 3, 4,
                       11, 2, 5, 1, 3, 1, 1, 1, 4, 3, 3, 1, 1, 3, 5, 1, 3, 2, 2, 4, 1, 2, 1, 2, 2, 1, 2, 4, 2, 1, 5, 3,
                       1, 5, 6, 4, 2, 1, 3, 2, 10, 3, 3, 2, 10, 3, 5, 4, 3, 2, 6, 2, 4, 4, 1, 4, 3, 5, 1, 4, 5, 2, 4, 5,
                       8, 3, 5, 3, 2, 8, 3, 2, 1, 2, 1, 13, 6, 10, 1, 1, 3, 1, 6],
            'inactive': [17, 1, 1, 2, 1, 9, 2, 2, 9, 1, 9, 91, 1, 4, 3, 1, 4, 3, 5, 3, 1, 1, 4, 2, 3, 1, 2, 2, 1, 1, 1,
                         2, 5, 1, 1, 2, 1, 2, 3, 2, 3, 5, 3, 1, 1, 1, 1, 1, 5, 4, 2, 1, 3, 1, 2, 1, 1, 2, 1, 2, 6, 2, 1,
                         10, 3, 2, 1, 1, 1, 3, 3, 2, 1, 6, 1, 3, 4, 2, 3, 1, 1, 4, 2, 2, 3, 1, 3, 3, 4, 1, 2, 5, 1, 5,
                         10, 1, 1, 2, 3, 2, 12, 3, 4, 1, 7, 6, 2, 1, 3, 3, 2, 7, 4, 2, 3, 5, 3, 4, 2, 4, 5, 3, 3, 3, 11,
                         2, 5, 1, 2, 2, 11, 3, 2, 4, 13, 3, 2, 8, 2, 3, 1, 6, 18, 1, 2, 1, 9, 3, 10, 1, 9, 94, 2, 7, 3,
                         3, 6, 1, 3, 4, 3, 3, 1, 3, 1, 4, 6, 2, 2, 3, 5, 5, 3, 3, 1, 1, 7, 4, 4, 1, 3, 3, 3, 7, 2, 10,
                         3, 3, 1, 4, 2, 2, 5, 3, 1, 6, 1, 4, 2, 4, 4, 1, 5, 3, 2, 4, 3, 5, 1, 11, 5, 2, 4, 11, 3, 7, 8,
                         6, 2, 5, 4, 7, 5, 4, 6, 2, 5, 3, 7, 5, 6, 10, 6, 2, 5, 9, 3, 2, 4, 16, 10, 2, 3, 7, 7, 4, 2, 9,
                         16, 4, 5, 11, 5, 7, 12, 8, 9, 6, 4, 8, 6, 8, 10, 3, 12, 5, 14, 5, 2, 13, 4, 4, 9, 4, 3, 2, 6,
                         7, 4, 7, 5, 1, 6, 4, 4, 3, 6, 9, 6, 4, 3, 2, 4, 5, 5, 3, 2, 3, 9, 9, 5, 11, 3, 7, 6, 3, 4, 4,
                         20, 5, 10, 2, 10, 2, 11, 92]
        }
    }
}


# =============================================================================
# Print a line preceded by a timestamp
# =============================================================================
def print_log(message: object) -> None:
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} # {str(message)}')


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


# Actuals Functions

def PressKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def ReleaseKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def auto_press_key(hexKeyCode):
    PressKey(hexKeyCode)
    time.sleep(.08)
    ReleaseKey(hexKeyCode)


def window_enumeration_handler(hwnd, top_windows):
    """Add window title and ID to array."""
    top_windows.append({
        'handle': hwnd,
        'title': win32gui.GetWindowText(hwnd),
        'rect': win32gui.GetWindowRect(hwnd),
        'pid': re.sub(r'^.*pid\: ([0-9]+)\)$', '\\1', win32gui.GetWindowText(hwnd))
    })


def check_if_round_ended(left: int, top: int) -> bool:
    ocr_result = ocr_screenshot_region(
        left + 72,
        top + 82,
        740,
        20,
        True
    )

    round_end_labels = ['score list', 'top players', 'top scores', 'map briefing']

    return any(round_end_label in ocr_result for round_end_label in round_end_labels)


def check_if_map_is_loading(left: int, top: int) -> bool:
    on_round_end_screen = check_if_round_ended(left, top)

    join_game_button_present = 'join game' in ocr_screenshot_region(
        left + 1163,
        top + 725,
        80,
        16,
        True
    )

    return on_round_end_screen and not join_game_button_present


def check_for_game_message(left: int, top: int) -> bool:
    screenshot = pyautogui.screenshot(region=(left + 400, top + 223, 130, 25))
    inverted = ImageOps.invert(screenshot)
    ocr_result = pytesseract.image_to_string(inverted)
    print_log(f'Game message check ocr: {ocr_result}')
    return 'game message' in ocr_result.lower()


def ocr_game_message(left: int, top: int) -> bool:
    screenshot = pyautogui.screenshot(region=(left + 400, top + 246, 470, 16))
    inverted = ImageOps.invert(screenshot)
    custom_config = r'--oem 3 --psm 7'
    ocr_result = pytesseract.image_to_string(inverted, config=custom_config)
    print_log(f'Game message ocr: {ocr_result}')
    return ocr_result.lower()


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


def get_player_team_histogram(left: int, top: int) -> int:
    # Take team selection screenshots
    team_selection_screenshots = [
        pyautogui.screenshot(region=(left + 68, top + 69, 41, 13)),
        pyautogui.screenshot(region=(left + 209, top + 69, 41, 13))
    ]

    # Get histograms of screenshots (removing zeroes)
    team_selection_histograms = []
    for team_selection_screenshot in team_selection_screenshots:
        team_selection_histograms.append(list_filter_zeroes(team_selection_screenshot.histogram()))

    # Compare histograms to constant to determine team
    team = None
    if team_selection_histograms[0] == HISTOGRAMS['teams']['usmc']['active']:
        # Player is on USMC team
        team = 0
    elif team_selection_histograms[1] == HISTOGRAMS['teams']['mec']['active']:
        # Player is on MEC/PLA team
        team = 1

    return team


def check_if_server_full(server_ip: str, server_port: str) -> bool:
    response = requests.get(f'https://www.gametracker.com/server_info/{server_ip}:{server_port}')
    soup = BeautifulSoup(response.text, 'html.parser')
    current_players = int(soup.select_one('#HTML_num_players').text)
    max_players = int(soup.select_one('#HTML_max_players').text)

    return current_players == max_players


def disconnect_from_server(left: int, top: int) -> None:
    # Press ESC
    auto_press_key(0x01)
    time.sleep(5)
    # Move cursor onto disconnect button and click
    ctypes.windll.user32.SetCursorPos(left + 1210, top + 725)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)


def connect_to_server(left: int, top: int, server_ip: str, server_port: str, server_pass: str = None) -> None:
    # Move cursor onto bfhq menu item and click
    # Required to reset multiplayer menu
    pyautogui.moveTo(left + 111, top + 50)
    time.sleep(.2)
    pyautogui.leftClick()

    time.sleep(3)

    # Move cursor onto multiplayer menu item and click
    pyautogui.moveTo(left + 331, top + 50)
    time.sleep(.2)
    pyautogui.leftClick()

    time.sleep(4)

    # Move cursor onto connect to ip button and click
    pyautogui.moveTo(left + 111, top + 452)
    time.sleep(.2)
    pyautogui.leftClick()

    # Give field popup time to appear
    time.sleep(.3)

    # Clear out ip field
    for i in range(0, 20):
        pyautogui.press('backspace')

    # Write ip
    pyautogui.write(server_ip)

    # Hit tab to enter port
    pyautogui.press('tab')

    # Clear out port field
    for i in range(0, 10):
        pyautogui.press('backspace')

    # Write port
    pyautogui.write(server_port)

    time.sleep(.3)

    # Write password if required
    # Field clears itself, so need to clear manually
    if server_pass is not None:
        pyautogui.press('tab')

        pyautogui.write(server_pass)

        time.sleep(.3)

    # Move cursor onto ok button and click
    pyautogui.moveTo(left + 777, top + 362)
    time.sleep(.2)
    pyautogui.leftClick()


def close_game_message(left: int, top: int) -> None:
    # Move cursor onto ok button and click
    ctypes.windll.user32.SetCursorPos(left + 806, top + 412)
    time.sleep(.1)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)


def ocr_player_name(left: int, top: int) -> str:
    screenshot = pyautogui.screenshot(region=(left + 875, top + 471, 110, 100))
    screenshot.show()
    orcResults = []
    custom_config = r'--oem 3 --psm 7'
    for i in range(0, screenshot.height, 6):
        screenshot.height
        cropped = ImageOps.crop(screenshot, (0, i, 0, screenshot.height - (12 + i)))
        inverted = ImageOps.autocontrast(ImageOps.invert(cropped))
        inverted.show()
        orcResults.append(pytesseract.image_to_string(inverted, config=custom_config))
        print_log(orcResults[-1])

    # Adding custom options
    return orcResults[-1]


def get_sever_player_count(left: int, top: int) -> int:
    # Press/hold tab
    PressKey(0x0f)
    time.sleep(.5)

    # Take screenshot
    screenshot = pyautogui.screenshot(region=(left + 180, top + 656, 647, 17))
    # Invert
    screenshot = ImageOps.invert(screenshot)

    # Release tab
    ReleaseKey(0x0f)

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


def ocr_player_scoreboard(left: int, top: int, right: int, bottom: int) -> list:
    # Init list
    players = []

    # Press/hold tab
    PressKey(0x0f)
    time.sleep(.5)

    # Take screenshot
    screenshot = pyautogui.screenshot(region=(left + 8, top + 31, right - left - 16, bottom - top - 40))
    screenshot.show()

    # Release tab
    ReleaseKey(0x0f)

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


def spawn_suicide(team: int):
    # Reset mouse to top left corner
    mouse_reset_legacy()

    # Select default spawn based on current team
    if team == 0:
        # Player is on USMC team, move cursor to USMC default spawn point
        mouse_move_legacy(382, 390)
    elif team == 1:
        # Player is on MEC team, move cursor to MEC default spawn point
        mouse_move_legacy(569, 160)
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
    mouse_move_legacy(250, 50)
    time.sleep(0.3)
    mouse_click_legacy()

    # Reset cursor once more
    mouse_reset_legacy()

    # Click suicide button
    mouse_move_legacy(469, 459)
    time.sleep(.3)
    mouse_click_legacy()
    time.sleep(.5)


def toggle_hud(direction: int):
    # Open/toggle console
    auto_press_key(0x1d)
    time.sleep(.1)

    # Write command
    pyautogui.write(f'renderer.drawHud {str(direction)}')
    time.sleep(.1)

    # Hit enter
    pyautogui.press('enter')
    time.sleep(.1)

    # X / toggle console
    auto_press_key(0x1d)
    time.sleep(.1)


# Move mouse using old mouse_event method (relative, by "mickeys)
def mouse_move_legacy(dx: int, dy: int) -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)
    time.sleep(.08)


# Mouse click using old mouse_event method
def mouse_click_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_reset_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -10000, -10000)
    time.sleep(.5)


def init_game_instance(bf2_path: str, player_name: str, player_pass: str,
                       server_ip: str = None, server_port: str = None) -> None:
    # Init shell
    shell = win32com.client.Dispatch("WScript.Shell")

    # Prepare command
    command = f'cmd /c start /b /d "{bf2_path}" BF2.exe +restart 1 ' \
              f'+playerName "{player_name}" +playerPassword "{player_pass}" ' \
              f'+szx 1280 +szy 720 +fullscreen 0 +wx 5 +wy 5 ' \
              f'+multi 1 +developer 1 +disableShaderCache 1'

    # Add server details to command if provided
    if server_ip is not None and server_port is not None:
        command += f' +joinServer {server_ip} +port {server_port}'

    # Run command
    shell.Run(command)
    time.sleep(15)


def find_window_by_title(search_title: str) -> dict:
    # Call window enumeration handler
    win32gui.EnumWindows(window_enumeration_handler, top_windows)
    bf2_window = None
    for window in top_windows:
        if search_title in window['title']:
            bf2_window = window

    return bf2_window


# Take a screenshot of the given region and run the result through OCR
def ocr_screenshot_region(x: int, y: int, w: int, h: int, invert: bool = False, show: bool = False,
                          config: str = r'--oem 3 --psm 7') -> str:
    screenshot = pyautogui.screenshot(region=(x, y, w, h))
    if invert:
        screenshot = ImageOps.invert(screenshot)
    if show:
        screenshot.show()
    ocr_result = pytesseract.image_to_string(screenshot, config=config)
    # print_log(f'OCR result: {ocr_result}')
    return ocr_result.lower()


def is_responding_pid(pid: int) -> bool:
    """Check if a program (based on its PID) is responding"""
    cmd = 'tasklist /FI "PID eq %d" /FI "STATUS eq running"' % pid
    status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return str(pid) in str(status)


def taskkill_pid(pid: int) -> bool:
    cmd = 'taskkill /F /PID %d' % pid
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return 'has been terminated' in str(output)


parser = argparse.ArgumentParser(description='Launch and control a Battlefield 2 spectator instance')
parser.add_argument('--player-name', help='Account name of spectating player', type=str, required=True)
parser.add_argument('--player-pass', help='Account password of spectating player', type=str, required=True)
parser.add_argument('--server-ip', help='IP of sever to join for spectating', type=str, required=True)
parser.add_argument('--server-port', help='Port of sever to join for spectating', type=str, default='16567')
parser.add_argument('--server-pass', help='Password of sever to join for spectating', type=str)
parser.add_argument('--game-path', help='Path to BF2 install folder',
                    type=str, default='C:\\Program Files (x86)\\EA Games\\Battlefield 2\\')
parser.add_argument('--tesseract-path', help='Path to Tesseract install folder',
                    type=str, default='C:\\Program Files\\Tesseract-OCR\\')
parser.add_argument('--no-start', dest='start_game', action='store_false')
parser.add_argument('--no-connect', dest='connect', action='store_false')
parser.set_defaults(start_game=True, connect=True)
args = parser.parse_args()

# Init global vars/settings
pytesseract.pytesseract.tesseract_cmd = os.path.join(args.tesseract_path, 'tesseract.exe')
top_windows = []

# Make sure provided paths are valid
if not os.path.isfile(pytesseract.pytesseract.tesseract_cmd):
    sys.exit(f'Could not find tesseract.exe in given install folder: {args.tesseract_path}')
elif not os.path.isfile(os.path.join(args.game_path, 'BF2.exe')):
    sys.exit(f'Could not find BF2.exe in given game install folder: {args.game_path}')

# Init game instance state store
gameInstanceState = GameInstanceState()

# Init game instance if requested
if args.start_game and args.server_pass is None:
    print_log('Initializing spectator game instance and joining server')
    init_game_instance(
        args.game_path,
        args.player_name,
        args.player_pass,
        args.server_ip,
        args.server_port
    )
    gameInstanceState.set_spectator_on_server(True)
elif args.start_game and args.server_pass is not None:
    print_log('Initializing idle spectator game instance')
    init_game_instance(
        args.game_path,
        args.player_name,
        args.player_pass
    )
    time.sleep(5)

# Update state
gameInstanceState.set_server_ip(args.server_ip)
gameInstanceState.set_server_port(args.server_port)
gameInstanceState.set_server_password(args.server_pass)

# Find BF2 window
print_log('Finding BF2 window')
bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:')
print_log(f'Found window: {bf2Window}')

# Connect to server if requested/required
if not args.start_game and args.connect or args.start_game and args.server_pass is not None:
    try:
        win32gui.ShowWindow(bf2Window['handle'], win32con.SW_SHOW)
        win32gui.SetForegroundWindow(bf2Window['handle'])

        # Connect to server
        connect_to_server(
            bf2Window['rect'][0],
            bf2Window['rect'][1],
            gameInstanceState.get_server_ip(),
            gameInstanceState.get_server_port(),
            gameInstanceState.get_server_password()
        )
        time.sleep(10)
        gameInstanceState.set_spectator_on_server(True)
    except Exception as e:
        print_log('BF2 window is gone, restart required')
        print_log(str(e))
        gameInstanceState.set_error_restart_required(True)

# Make sure we successfully joined the server
print_log('Making sure spectator successfully joined server')
joined = False
while not joined:
    joined = get_player_team(args.server_ip, args.server_port) is not None
    time.sleep(5)

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

    # Check for "Not responding" in title of BF2 window (added on game freeze)
    if not gameInstanceState.error_restart_required() and not is_responding_pid(int(bf2Window['pid'])):
        print_log('BF2 froze, restart required')
        gameInstanceState.set_error_restart_required(True)
        # Kill frozen instance by pid
        killed = taskkill_pid(int(bf2Window['pid']))
        print_log(f'Frozen window killed: {killed}')
        # Give Windows time to actually close the window
        time.sleep(2)
        continue

    # Start a new game instance if required
    if gameInstanceState.error_restart_required():
        # Init game new game instance
        init_game_instance(
            args.game_path,
            args.player_name,
            args.player_pass,
            gameInstanceState.get_server_ip(),
            gameInstanceState.get_server_port()
        )
        # Update window dict
        bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:')
        # Reset state
        gameInstanceState.restart_reset()
        continue

    # Make sure we are still in the game
    gameMessagePresent = check_for_game_message(bf2Window['rect'][0], bf2Window['rect'][1])
    print_log(f'Game message present: {str(gameMessagePresent)}')
    if gameMessagePresent:
        print_log('Game message present, ocr-ing message')
        gameMessage = ocr_game_message(bf2Window['rect'][0], bf2Window['rect'][1])

        # Close game message to enable actions
        close_game_message(bf2Window['rect'][0], bf2Window['rect'][1])

        if 'full' in gameMessage:
            print_log('Server full, trying to rejoin in 30 seconds')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            time.sleep(20)
            gameInstanceState.set_spectator_on_server(True)
        elif 'kicked' in gameMessage:
            print_log('Got kicked, trying to rejoin')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            gameInstanceState.set_spectator_on_server(True)
        elif 'banned' in gameMessage:
            sys.exit('Got banned, contact server admin')
        elif 'connection' in gameMessage and 'lost' in gameMessage or \
                'failed to connect' in gameMessage:
            print_log('Connection lost, trying to reconnect')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            gameInstanceState.set_spectator_on_server(True)
        elif 'modified content' in gameMessage:
            print_log('Got kicked for modified content, trying to rejoin')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            gameInstanceState.set_spectator_on_server(True)
        else:
            sys.exit(gameMessage)

        time.sleep(10)
        continue

    # Player is not on server, check if rejoining is possible and makes sense
    if not gameInstanceState.spectator_on_server():
        # Check number of free slots
        # TODO
        connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
        gameInstanceState.set_spectator_on_server(True)

    onRoundFinishScreen = check_if_round_ended(bf2Window['rect'][0], bf2Window['rect'][1])
    print_log(f'onRoundFinishScreen: {onRoundFinishScreen}')
    mapIsLoading = check_if_map_is_loading(bf2Window['rect'][0], bf2Window['rect'][1])
    print_log(f'mapIsLoading: {mapIsLoading}')
    if onRoundFinishScreen or mapIsLoading:
        # Reset state
        gameInstanceState.round_end_reset()
        # Reset spawn flag every round on non-freecam servers
        if gameInstanceState.get_server_ip() not in FREECAM_SERVERS:
            gameInstanceState.set_rotation_spawned(False)
        # If map is loading, reset spawn flag
        if mapIsLoading:
            gameInstanceState.map_rotation_reset()
        time.sleep(10)
    elif not gameInstanceState.rotation_spawned():
        # Re-enable hud if required
        if gameInstanceState.hud_hidden():
            print_log('Enabling hud')
            toggle_hud(1)
            # Update state
            gameInstanceState.set_hud_hidden(False)
            # Give game time to swap teams
            time.sleep(3)
        print_log('Determining team')
        gameInstanceState.set_round_team(get_player_team_histogram(bf2Window['rect'][0], bf2Window['rect'][1]))
        print_log(f'Current team: {"USMC" if gameInstanceState.get_round_team() == 0 else "MEC/CHINA"}')
        print_log('Spawning once')
        spawn_suicide(gameInstanceState.get_round_team())
        gameInstanceState.set_rotation_spawned(True)
    elif not gameInstanceState.hud_hidden():
        print_log('Hiding hud')
        toggle_hud(0)
        gameInstanceState.set_hud_hidden(True)
        # Enable free cam
        print_log('Enabling free cam')
        auto_press_key(0x39)
    elif not gameInstanceState.round_started_spectation():
        # Disable free cam
        print_log('Disabling free cam')
        auto_press_key(0x39)
        gameInstanceState.set_round_started_spectation(True)
        # Increase round number/counter
        gameInstanceState.increase_round_num()
        # time.sleep(20)
    else:
        auto_press_key(0x2e)
        time.sleep(22)

    serverIsFull = get_sever_player_count(bf2Window['rect'][0], bf2Window['rect'][1]) == 64
    print_log(f'Server is full {serverIsFull}')
    if serverIsFull and gameInstanceState.spectator_on_server():
        disconnect_from_server(bf2Window['rect'][0], bf2Window['rect'][1])
        gameInstanceState.set_spectator_on_server(False)
        time.sleep(30)
