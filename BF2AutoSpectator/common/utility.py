import ctypes
import os
import subprocess
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple, List, Union

import cv2
import jellyfish
import numpy as np
import psutil
import pyautogui
import pytesseract
import win32api
import win32con
import win32gui
import win32process
from PIL import Image, ImageOps
from numpy import ndarray

from BF2AutoSpectator.common import constants
from BF2AutoSpectator.common.config import Config
from BF2AutoSpectator.common.logger import logger

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

    def get_size(self) -> Tuple[int, int]:
        # Size on Windows contains the window header and the halo/shadow around the window,
        # which needs to be subtracted to get the real size
        left, top, right, bottom = self.rect
        return right - constants.WINDOW_SHADOW_SIZE - left - constants.WINDOW_SHADOW_SIZE, \
            bottom - constants.WINDOW_SHADOW_SIZE - top - constants.WINDOW_TITLE_BAR_HEIGHT


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
    :param game_window: Game window to move mouse in/on
    :param resolution: resolution to get/use coordinates for
    :param key: key of click target in coordinates dict
    :param legacy: whether to use legacy mouse move instead of pyautogui move
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


def is_cursor_on_game_window(game_window: Window) -> bool:
    # https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-cursorinfo
    flags, handle, (px, py) = win32gui.GetCursorInfo()
    # Get current (!) game window rectangle
    try:
        left, top, right, bottom = win32gui.GetWindowRect(game_window.handle)
    except win32gui.error:  # PyCharm claims win32gui.error does not exist, but it does
        return False

    """
    Allow cursor to only be within the actual window "body", ignore the title bar and the shadow around it. If the game 
    is currently not in the menu (meaning we are controlling the mouse movement by mickeys), the cursor position is of
    no use. However, Windows flags the cursor as hidden and returns the handle as 0.
    """
    if flags == 0 and handle == 0 or \
            left + constants.WINDOW_SHADOW_SIZE <= px <= right - constants.WINDOW_SHADOW_SIZE and \
            top + constants.WINDOW_TITLE_BAR_HEIGHT <= py <= bottom - constants.WINDOW_SHADOW_SIZE:
        return True

    return False


def mouse_click_in_game_window(game_window: Window, legacy: bool = False) -> None:
    if not is_cursor_on_game_window(game_window):
        logger.warning(f'Mouse cursor is not on game window, ignoring mouse click')
        return

    if legacy:
        mouse_click_legacy()
    else:
        pyautogui.leftClick()


# Mouse click using old mouse_event method
def mouse_click_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_reset_legacy() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -10000, -10000)
    time.sleep(.2)


def mouse_reset(game_window: Window) -> None:
    """
    Reset mouse cursor to the center of the game window (via pyautogui)
    :param game_window: Game window to move mouse in/on
    :return:
    """
    left, top, right, bottom = game_window.rect
    pyautogui.moveTo((right - left)/2 + left, (bottom - top - 40)/2 + top)


def screenshot_region(
        x: int, y: int, w: int, h: int,
        image_ops: Optional[List[Tuple[ImageOperation, Optional[dict]]]] = None,
        show: bool = False
) -> Image:
    """
    Take a screenshot of the specified screen region (wrapper for pyautogui.screenshot)
    :param x: x coordinate of region start
    :param y: y coordinate of region start
    :param w: region width
    :param h: region height
    :param image_ops: List of image operation tuples, format: (operation, arguments)
    :param show: whether to show the screenshot
    :return:
    """
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

    # Save screenshot to debug directory if debugging is enabled
    config = Config()
    if config.debug_screenshot():
        # Save screenshot
        screenshot.save(
            os.path.join(
                Config.DEBUG_DIR,
                f'ocr_screenshot-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")}.jpg'
            )
        )

    return screenshot


def screenshot_game_window_region(
        game_window: Window,
        x: int, y: int, w: int, h: int,
        image_ops: Optional[List[Tuple[ImageOperation, Optional[dict]]]] = None,
        show: bool = False
) -> Image:
    """
    Take a screenshot of the specified game window region
    :param game_window: game window to take screenshot of
    :param x: x coordinate of region start
    :param y: y coordinate of region start
    :param w: region width
    :param h: region height
    :param image_ops: List of image operation tuples, format: (operation, arguments)
    :param show: whether to show the screenshot
    :return:
    """

    return screenshot_region(game_window.rect[0] + x, game_window.rect[1] + y, w, h, image_ops, show)


def init_pytesseract(tesseract_path: str) -> None:
    pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_path, constants.TESSERACT_EXE)


def image_to_string(image: Image, ocr_config: str) -> str:
    """
    Extract text from an image (wrapper for pytesseract.image_to_string)
    :param image: PIL image to extract text from
    :param ocr_config: config/parameters for Tesseract OCR (see https://guides.nyu.edu/tesseract/usage)
    :return:
    """
    # pytesseract stopped stripping \n\x0c from ocr results,
    # returning raw results instead (https://github.com/madmaze/pytesseract/issues/297)
    # so strip those characters as well as spaces after getting the result
    ocr_result = pytesseract.image_to_string(image, config=ocr_config).strip(' \n\x0c')

    # Print ocr result if debugging is enabled
    config = Config()
    if config.debug_screenshot():
        logger.debug(f'OCR result: {ocr_result}')

    return ocr_result.lower()


# Take a screenshot of the given region and run the result through OCR
def ocr_screenshot_region(x: int, y: int, w: int, h: int,
                          image_ops: Optional[List[Tuple[ImageOperation, Optional[dict]]]] = None,
                          crops: Optional[List[Tuple[int, int, int, int]]] = None,
                          show: bool = False, ocr_config: str = r'--oem 3 --psm 7') -> Union[str, List[str]]:
    screenshot = screenshot_region(x, y, w, h, image_ops, show)

    if crops is None:
        return image_to_string(screenshot, ocr_config)

    ocr_results: List[str] = []
    for crop in crops:
        cropped = ImageOps.crop(screenshot, crop)
        ocr_results.append(image_to_string(cropped, ocr_config))

    return ocr_results


def ocr_screenshot_game_window_region(game_window: Window, resolution: str, key: str,
                                      image_ops: Optional[List[Tuple[ImageOperation, Optional[dict]]]] = None,
                                      crops: Optional[List[Tuple[int, int, int, int]]] = None,
                                      show: bool = False, ocr_config: str = r'--oem 3 --psm 7') -> Union[str, List[str]]:
    """
    Run a region of a game window through OCR (wrapper for ocr_screenshot_region)
    :param game_window: game window to take screenshot of
    :param resolution: resolution to get/use coordinates for
    :param key: key of region in coordinates dict
    :param image_ops: List of image operation tuples, format: (operation, arguments)
    :param crops: List of image crop tuples, format: (left, top, right, bottom)
    :param show: whether to show the screenshot
    :param ocr_config: config/parameters for Tesseract OCR (see https://guides.nyu.edu/tesseract/usage)
    :return:
    """

    return ocr_screenshot_region(
        game_window.rect[0] + constants.COORDINATES[resolution]['ocr'][key][0],
        game_window.rect[1] + constants.COORDINATES[resolution]['ocr'][key][1],
        constants.COORDINATES[resolution]['ocr'][key][2],
        constants.COORDINATES[resolution]['ocr'][key][3],
        image_ops,
        crops,
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


def get_proc_by_pid(pid: int) -> Optional[psutil.Process]:
    for proc in psutil.process_iter(attrs=['pid']):
        if proc.pid == pid:
            return proc


def get_command_line_by_pid(pid: int) -> Optional[List[str]]:
    proc = get_proc_by_pid(pid)

    if proc is None:
        return

    try:
        return proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return


def get_mod_from_command_line(pid: int) -> Optional[str]:
    command_line = get_command_line_by_pid(pid)

    if command_line is None:
        return

    for index, arg in enumerate(command_line):
        # Next argument after "+modPath" should be the mod path value
        if arg == '+modPath' and index + 1 < len(command_line):
            # Return mod path without leading "mods/"
            return command_line[index + 1][5:]


def run_conman(args: List[str]) -> None:
    command = [os.path.join(Config.ROOT_DIR, 'redist', 'bf2-conman.exe'), '--no-gui', *args]
    p = subprocess.run(command, timeout=1.0)
    return p.check_returncode()


def is_similar_str(a: str, b: str, threshold: float = .8) -> bool:
    return jellyfish.jaro_distance(a, b) >= threshold
