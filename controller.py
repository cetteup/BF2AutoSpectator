import ctypes
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

SendInput = ctypes.windll.user32.SendInput

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)


# =============================================================================
# Print a line preceded by a timestamp
# =============================================================================
def print_log(message: object) -> None:
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} # {str(message)}')


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
    screenshot = pyautogui.screenshot(region=(left + 5, top + 30, 1000, 50))
    inverted = ImageOps.invert(screenshot)
    custom_config = r'--oem 3 --psm 7'
    ocr_result = pytesseract.image_to_string(inverted, config=custom_config)
    print_log(f'Round end check ocr: {ocr_result}')
    return 'join game button' in ocr_result.lower()


def check_if_map_is_loading(left: int, top: int) -> bool:
    screenshot = pyautogui.screenshot(region=(left + 5, top + 30, 500, 50))
    inverted = ImageOps.invert(screenshot)
    custom_config = r'--oem 3 --psm 7'
    ocr_result = pytesseract.image_to_string(inverted, config=custom_config)
    print_log(f'Map loading check ocr: {ocr_result}')
    return 'cancel loading' in ocr_result.lower()


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


def connect_to_server(left: int, top: int, server_ip: str, server_port: str) -> None:
    # Move cursor onto bfhq menu item and click
    # Required to reset multiplayer menu
    ctypes.windll.user32.SetCursorPos(left + 111, top + 50)
    time.sleep(.1)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)

    time.sleep(3)

    # Move cursor onto multiplayer menu item and click
    ctypes.windll.user32.SetCursorPos(left + 331, top + 50)
    time.sleep(.1)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)

    time.sleep(4)

    # Move cursor onto connect to ip button and click
    ctypes.windll.user32.SetCursorPos(left + 111, top + 452)
    time.sleep(.1)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)

    time.sleep(.3)

    # Init shell
    shell = win32com.client.Dispatch("WScript.Shell")

    # Clear out ip field
    for i in range(0, 20):
        shell.SendKeys('{BKSP}', 0)
        time.sleep(.08)

    # Type ip address
    for i in range(0, len(server_ip)):
        shell.SendKeys(server_ip[i], 0)
        time.sleep(.08)

    # Hit tab to enter port if required
    if server_port != '16567':
        for i in range(0, 4):
            shell.SendKeys('{BKSP}', 0)
            time.sleep(.08)

        for i in range(0, len(server_port)):
            shell.SendKeys(server_port[i], 0)
            time.sleep(.08)

    time.sleep(.3)

    # Move cursor onto ok button and click
    ctypes.windll.user32.SetCursorPos(left + 777, top + 362)
    time.sleep(.1)
    ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)


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
        cropped = ImageOps.crop(screenshot, (708, 114 + i * 24, 290, 101 + (20 - i) * 24))
        custom_config = r'--oem 3 --psm 7'
        ocr_result = pytesseract.image_to_string(cropped, config=custom_config)
        print(ocr_result)
        players[0].append(ocr_result.lower())

    # OCR MEC players
    players.append([])
    for i in range(0, 21):
        cropped = ImageOps.crop(screenshot, (84, 114 + i * 24, 920, 101 + (20 - i) * 24))
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


def hide_hud():
    # X / toggle console
    auto_press_key(0x1d)
    # Type "renderer.drawHud 0"
    auto_press_key(0x13)
    auto_press_key(0x12)
    auto_press_key(0x31)
    auto_press_key(0x20)
    auto_press_key(0x12)
    auto_press_key(0x13)
    auto_press_key(0x12)
    auto_press_key(0x13)
    auto_press_key(0x34)
    auto_press_key(0x20)
    auto_press_key(0x13)
    auto_press_key(0x1e)
    auto_press_key(0x11)
    auto_press_key(0x23)
    auto_press_key(0x16)
    auto_press_key(0x20)
    auto_press_key(0x39)
    auto_press_key(0x0b)
    # Hit enter
    auto_press_key(0x1c)
    # X / toggle console
    auto_press_key(0x1d)


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
                       server_ip: str, server_port: str) -> None:
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.Run(f'cmd /c start /b /d "{bf2_path}" BF2.exe +restart 1 +playerName '
              f'"{player_name}" +playerPassword "{player_pass}" +joinServer {server_ip} '
              f'+port {server_port} +szx 1280 +szy 720 +fullscreen 0 +wx 5 +wy 5 +multi 1 '
              f'+developer 1 +disableShaderCache 1')
    time.sleep(15)


def find_window_by_title(search_title: str) -> dict:
    # Call window enumeration handler
    win32gui.EnumWindows(window_enumeration_handler, top_windows)
    bf2_window = None
    for window in top_windows:
        if search_title in window['title']:
            bf2_window = window

    return bf2_window


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
parser.add_argument('--bf2-path', help='Path to BF2 install folder',
                    type=str, default='C:\\Program Files (x86)\\EA Games\\Battlefield 2\\')
parser.add_argument('--tesseract-path', help='Path to Tesseract install folder',
                    type=str, default='C:\\Program Files\\Tesseract-OCR\\')
args = parser.parse_args()

# Init global vars/settings
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
top_windows = []

# Init game instance
# print_log('Initializing spectator game instance')
init_game_instance(args.bf2_path, args.player_name, args.player_pass, args.server_ip, args.server_port)

# Find BF2 window
print_log('Finding BF2 window')
bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:')
print_log(f'Found window: {bf2Window}')

# Make sure we successfully joined the server
print_log('Making sure spectator successfully joined server')
joined = False
while not joined:
    joined = get_player_team(args.server_ip, args.server_port) is not None
    time.sleep(5)

spawnedOnce = False
hudHidden = False
startedSpectation = False
restartRequired = False
playerExpectedOnServer = False
while True:
    # Try to bring BF2 window to foreground
    if not restartRequired:
        try:
            win32gui.ShowWindow(bf2Window['handle'], win32con.SW_SHOW)
            win32gui.SetForegroundWindow(bf2Window['handle'])
        except Exception as e:
            print_log('BF2 window is gone, restart required')
            print_log(str(e))
            restartRequired = True

    # Check for "Not responding" in title of BF2 window (added on game freeze)
    if not restartRequired and not is_responding_pid(int(bf2Window['pid'])):
        print_log('BF2 froze, restart required')
        restartRequired = True
        # Kill frozen instance by pid
        killed = taskkill_pid(int(bf2Window['pid']))
        print_log(f'Frozen window killed: {killed}')
        # Give Windows time to actually close the window
        time.sleep(2)
        continue

    # Start a new game instance if required
    if restartRequired:
        # Init game new game instance
        init_game_instance(args.bf2_path, args.player_name, args.player_pass, args.server_ip, args.server_port)
        # Update window dict
        bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:')
        # Unset restart flag
        restartRequired = False
        # Reset other flags
        spawnedOnce = False
        hudHidden = False
        startedSpectation = False
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
            playerExpectedOnServer= True
        elif 'kicked' in gameMessage:
            print_log('Got kicked, trying to rejoin')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            playerExpectedOnServer = True
        elif 'banned' in gameMessage:
            print_log('Got banned, contact server admin')
            break
        elif 'connection' in gameMessage and 'lost' in gameMessage or \
                'failed to connect' in gameMessage:
            print_log('Connection lost, trying to reconnect')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            playerExpectedOnServer = True
        elif 'modified content' in gameMessage:
            print_log('Got kicked for modified content, trying to rejoin')
            connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
            playerExpectedOnServer = True
        else:
            print_log(gameMessage)
            break

        time.sleep(10)
        continue

    # Player is not on server, check if rejoining is possible and makes sense
    if not playerExpectedOnServer:
        # Check number of free slots
        # TODO
        connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
        playerExpectedOnServer = True

    onRoundFinishScreen = check_if_round_ended(bf2Window['rect'][0], bf2Window['rect'][1])
    print_log(f'onRoundFinishScreen: {onRoundFinishScreen}')
    mapIsLoading = check_if_map_is_loading(bf2Window['rect'][0], bf2Window['rect'][1])
    print_log(f'mapIsLoading: {mapIsLoading}')
    if onRoundFinishScreen or mapIsLoading:
        startedSpectation = False
        time.sleep(10)
    elif not spawnedOnce:
        print_log('Spawning once')
        spawn_suicide(get_player_team(args.server_ip, args.server_port))
        spawnedOnce = True
    elif not hudHidden:
        print_log('Hiding hud')
        hide_hud()
        hudHidden = True
        # Enable free cam
        print_log('Enabling free cam')
        auto_press_key(0x39)
    elif not startedSpectation:
        # Disable free cam
        print_log('Disabling free cam')
        auto_press_key(0x39)
        startedSpectation = True
        # time.sleep(20)
    else:
        auto_press_key(0x2e)
        time.sleep(22)
    print_log('USMC' if get_player_team(args.server_ip, args.server_port) == 0 else 'MEC')

    serverIsFull = check_if_server_full(args.server_ip, args.server_port)
    print_log(f'Server is full {serverIsFull}')
    if serverIsFull and playerExpectedOnServer:
        disconnect_from_server(bf2Window['rect'][0], bf2Window['rect'][1])
        playerExpectedOnServer = False
        time.sleep(30)
