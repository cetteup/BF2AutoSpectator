import ctypes
import logging
import os
import subprocess
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple, List

import cv2
import numpy as np
import pyautogui
import pytesseract
import win32api
import win32con
import win32gui
import win32process
from PIL import Image, ImageOps
from numpy import ndarray

import constants
from config import Config

SendInput = ctypes.windll.user32.SendInput
# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)


class Window:
    handle: int
    title: str
    rect: Tuple[int, int, int, int]
    class_name: str
    pid: int

    def __init__(self, handle: int, title: str, rect: Tuple[int, int, int, int], class_name: str, pid: int):
        self.handle = handle
        self.title = title
        self.rect = rect
        self.class_name = class_name
        self.pid = pid


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


class ImageOperation(Enum):
    invert = 1
    solarize = 2


def list_filter_zeroes(list_with_zeroes: list) -> list:
    list_without_zeroes = filter(lambda num: num > 0, list_with_zeroes)

    return list(list_without_zeroes)


def is_responding_pid(pid: int) -> bool:
    """Check if a program (based on its PID) is responding"""
    cmd = 'tasklist /FI "PID eq %d" /FI "STATUS eq running"' % pid
    status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return str(pid) in str(status)


def taskkill_pid(pid: int) -> bool:
    cmd = 'taskkill /F /PID %d' % pid
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return 'has been terminated' in str(output)


def press_key(key_code: int) -> None:
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, key_code, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(key_code: int) -> None:
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, key_code, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def auto_press_key(key_code: int) -> None:
    press_key(key_code)
    time.sleep(.08)
    release_key(key_code)


def window_enumeration_handler(hwnd: int, top_windows: list):
    """Add window title and ID to array."""
    tid, pid = win32process.GetWindowThreadProcessId(hwnd)
    window = Window(
        hwnd,
        win32gui.GetWindowText(hwnd),
        win32gui.GetWindowRect(hwnd),
        win32gui.GetClassName(hwnd),
        pid
    )

    top_windows.append(window)


def find_window_by_title(search_title: str, search_class: str = None) -> Optional[Window]:
    # Reset top windows array
    top_windows = []

    # Call window enumeration handler
    win32gui.EnumWindows(window_enumeration_handler, top_windows)
    found_window = None
    for window in top_windows:
        if search_title in window.title and \
                (search_class is None or search_class in window.class_name):
            found_window = window

    return found_window


# Move mouse using old mouse_event method (relative, by "mickeys)
def mouse_move_legacy(dx: int, dy: int) -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)
    time.sleep(.08)


def mouse_move_to_game_window_coord(game_window: Window, resolution: str, key: str, legacy: bool = False) -> None:
    """
    Move mouse cursor to specified game window coordinates
    :param resolution: resolution to get/use coordinates for
    :param key: key of click target in coordinates dict
    :param legacy: whether to use legacy mouse move instead of pyautogui move
    :param game_window: Game window to move mouse in/on
    :return:
    """
    if legacy:
        mouse_move_legacy(constants.COORDINATES[resolution]['clicks'][key][0],
                          constants.COORDINATES[resolution]['clicks'][key][1])
    else:
        pyautogui.moveTo(
            game_window.rect[0] + constants.COORDINATES[resolution]['clicks'][key][0],
            game_window.rect[1] + constants.COORDINATES[resolution]['clicks'][key][1]
        )


# Mouse click using old mouse_event method
def mouse_click_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_reset_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -10000, -10000)
    time.sleep(.5)


def screenshot_game_window_region(game_window: Window, x: int, y: int, w: int, h: int) -> Image:
    """
    Take a screenshot of the specified game window region (wrapper for pyautogui.screenshot)
    :param game_window: game window to take screenshot of
    :param x: x coordinate of region start
    :param y: y coordinate of region start
    :param w: region width
    :param h: region height
    :return:
    """

    return pyautogui.screenshot(region=(game_window.rect[0] + x, game_window.rect[1] + y, w, h))


def init_pytesseract(tesseract_path: str) -> None:
    pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_path, constants.TESSERACT_EXE)


# Take a screenshot of the given region and run the result through OCR
def ocr_screenshot_region(x: int, y: int, w: int, h: int,
                          image_ops: Optional[List[Tuple[ImageOperation, Optional[dict]]]] = None,
                          show: bool = False, ocr_config: str = r'--oem 3 --psm 7') -> str:
    screenshot = pyautogui.screenshot(region=(x, y, w, h))
    if image_ops is not None:
        for operation in image_ops:
            method, args = operation
            if method is ImageOperation.invert:
                screenshot = ImageOps.invert(screenshot)
            elif method is ImageOperation.solarize:
                screenshot = ImageOps.solarize(screenshot, **(args if args is not None else {}))
    if show:
        screenshot.show()
    # pytesseract stopped stripping \n\x0c from ocr results,
    # returning raw results instead (https://github.com/madmaze/pytesseract/issues/297)
    # so strip those characters as well as spaces after getting the result
    ocr_result = pytesseract.image_to_string(screenshot, config=ocr_config).strip(' \n\x0c')

    # Save screenshot to debug directory and print ocr result if debugging is enabled
    config = Config()
    if config.debug_screenshot():
        # Save screenshot
        screenshot.save(
            os.path.join(
                Config.DEBUG_DIR,
                f'ocr_screenshot-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")}.jpg'
            )
        )
        # Print ocr result
        logging.debug(f'OCR result: {ocr_result}')

    return ocr_result.lower()


def ocr_screenshot_game_window_region(game_window: Window, resolution: str, key: str,
                                      image_ops: Optional[List[Tuple[ImageOperation, Optional[dict]]]] = None,
                                      show: bool = False, ocr_config: str = r'--oem 3 --psm 7') -> str:
    """
    Run a region of a game window through OCR (wrapper for ocr_screenshot_region)
    :param game_window: game window to take screenshot of
    :param resolution: resolution to get/use coordinates for
    :param image_ops: List of image operation tuples (format: (operation, arguments)
    :param key: key of region in coordinates dict
    :param show: whether to show the screenshot
    :param ocr_config: config/parameters for Tesseract OCR
    :return:
    """

    return ocr_screenshot_region(
        game_window.rect[0] + constants.COORDINATES[resolution]['ocr'][key][0],
        game_window.rect[1] + constants.COORDINATES[resolution]['ocr'][key][1],
        constants.COORDINATES[resolution]['ocr'][key][2],
        constants.COORDINATES[resolution]['ocr'][key][3],
        image_ops,
        show,
        ocr_config
    )


def histogram_screenshot_region(game_window: Window, x: int, y: int, w: int, h: int) -> ndarray:
    screenshot = screenshot_game_window_region(game_window, x, y, w, h)

    return calc_cv2_hist_from_pil_image(screenshot)


def calc_cv2_hist_from_pil_image(pil_image: Image) -> ndarray:
    # Convert PIL to cv2 image
    cv_image = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR)
    histogram = cv2.calcHist([cv_image], [0], None, [256], [0, 256])

    return histogram


def calc_cv2_hist_delta(a: ndarray, b: ndarray) -> float:
    return cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA)


def get_resolution_window_size(resolution: str) -> Tuple[int, int]:
    # Set window size based on resolution
    window_size = None
    if resolution == '720p':
        window_size = (1280, 720)
    elif resolution == '900p':
        window_size = (1600, 900)

    return window_size
