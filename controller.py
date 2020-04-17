import ctypes
import os
import re
import subprocess
import time
import argparse
import sys

import cv2
import numpy as np
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
from exceptions import *

SendInput = ctypes.windll.user32.SendInput

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)
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
        'eu': {
            'active': [336, 3, 1, 1, 1, 1, 3, 1, 2, 1, 1, 1, 3, 6, 2, 7, 3, 2, 3, 4, 2, 1, 1, 4, 1, 2, 1, 1, 1, 1, 1, 1,
                       1, 1, 2, 1, 3, 1, 4, 1, 6, 1, 2, 2, 2, 2, 5, 9, 4, 1, 1, 2, 1, 2, 1, 3, 2, 2, 1, 1, 1, 2, 2, 3,
                       3, 1, 5, 1, 2, 3, 2, 5, 1, 2, 8, 2, 2, 3, 3, 2, 2, 1, 2, 1, 3, 2, 2, 1, 3, 336, 3, 1, 1, 1, 1, 3,
                       1, 2, 1, 1, 1, 3, 6, 1, 6, 4, 2, 1, 3, 4, 3, 1, 2, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3, 1,
                       4, 1, 6, 1, 2, 4, 2, 5, 9, 4, 1, 1, 2, 1, 1, 1, 2, 2, 2, 2, 1, 1, 2, 2, 3, 3, 2, 3, 2, 1, 2, 1,
                       3, 2, 5, 5, 6, 3, 3, 3, 2, 3, 3, 3, 2, 2, 1, 3, 336, 3, 1, 1, 1, 1, 3, 1, 2, 1, 1, 1, 2, 2, 6, 1,
                       7, 2, 2, 1, 3, 4, 3, 1, 2, 2, 1, 1, 2, 1, 1, 1, 1, 2, 1, 2, 1, 1, 3, 2, 2, 1, 5, 2, 2, 4, 2, 3,
                       2, 9, 4, 1, 1, 2, 1, 1, 1, 1, 3, 2, 1, 1, 1, 1, 1, 1, 2, 3, 1, 3, 1, 3, 2, 1, 2, 1, 2, 2, 5, 1,
                       5, 5, 2, 2, 1, 3, 2, 2, 2, 1, 3, 1, 2, 3, 1, 1, 3],
            'inactive': [27, 25, 1, 25, 28, 234, 3, 1, 2, 1, 2, 5, 3, 1, 1, 2, 1, 2, 3, 4, 1, 3, 3, 2, 2, 3, 3, 1, 2, 1,
                         2, 1, 1, 1, 1, 2, 1, 2, 1, 2, 3, 5, 2, 3, 2, 2, 2, 2, 4, 3, 9, 1, 4, 2, 1, 1, 1, 2, 2, 1, 1, 2,
                         1, 1, 2, 2, 1, 3, 3, 2, 3, 1, 3, 2, 2, 2, 5, 2, 8, 1, 3, 1, 2, 5, 2, 1, 2, 1, 3, 2, 2, 1, 3,
                         27, 25, 26, 3, 25, 235, 2, 1, 1, 2, 1, 5, 3, 1, 3, 1, 1, 2, 3, 1, 6, 1, 3, 4, 3, 3, 1, 1, 2, 1,
                         2, 2, 1, 2, 2, 3, 4, 7, 4, 1, 1, 3, 3, 3, 3, 1, 9, 4, 2, 1, 2, 2, 2, 1, 2, 1, 2, 2, 2, 4, 3, 4,
                         2, 3, 2, 4, 5, 1, 5, 6, 2, 4, 4, 3, 3, 3, 3, 1, 1, 2, 1, 3, 1, 4, 3, 3, 3, 2, 3, 5, 9, 4, 7, 3,
                         3, 5, 4, 5, 3, 2, 2, 2, 3, 3, 1, 3, 3, 7, 10, 3, 3, 3, 2, 4, 5, 3, 3, 1, 2, 2, 1, 2, 2, 2, 2,
                         1, 2, 4, 7, 5, 3, 1, 11, 4, 4, 1, 29, 26, 26, 28, 235]
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
SPAWN_COORDINATES = {
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


def check_for_game_message(left: int, top: int) -> bool:
    # Get ocr result of game message area
    ocr_result = ocr_screenshot_region(
        left + 400,
        top + 223,
        130,
        25,
        True
    )

    return 'game message' in ocr_result


def ocr_game_message(left: int, top: int) -> str:
    # Get ocr result of game message content region
    ocr_result = ocr_screenshot_region(
        left + 400,
        top + 245,
        470,
        18,
        True
    )

    return ocr_result


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


def check_for_join_game_button(left: int, top: int) -> bool:
    # Get ocr result of bottom left corner where "join game"-button would be
    ocr_result = ocr_screenshot_region(
        left + 1163,
        top + 725,
        80,
        16,
        True
    )

    return 'join game' in ocr_result


def check_if_map_is_loading(left: int, top: int) -> bool:
    # Check if game is on round end screen
    on_round_end_screen = check_if_round_ended(left, top)

    # Check if join game button is present
    join_game_button_present = check_for_join_game_button(left, top)

    return on_round_end_screen and not join_game_button_present


def check_for_map_briefing(left: int, top: int) -> bool:
    # Get ocr result of top left "map briefing" area
    map_briefing_present = 'map briefing' in ocr_screenshot_region(
        left + 24,
        top + 112,
        115,
        20,
        True
    )

    return map_briefing_present


def check_if_spawn_menu_visible(left: int, top: int) -> bool:
    # Get ocr result of "special forces" class label/name
    ocr_result = ocr_screenshot_region(
        left + 60,
        top + 125,
        140,
        18,
        True
    )

    return 'special forces' in ocr_result


def get_map_name(left: int, top: int) -> str:
    # Screenshot and OCR map name area
    ocr_result = ocr_screenshot_region(
        left + 769,
        top + 114,
        210,
        17,
        True
    )

    # Replace spaces with dashes
    ocr_result = ocr_result.replace(' ', '-')

    map_name = None
    # Make sure map name is valid
    # Also check while replacing first g with q to account for common ocr error
    if ocr_result.lower() in SPAWN_COORDINATES.keys():
        map_name = ocr_result.lower()
    elif re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result.lower()) in SPAWN_COORDINATES.keys():
        map_name = re.sub(r'^([^g]*?)g(.*)$', '\\1q\\2', ocr_result.lower())

    return map_name


def get_map_size(left: int, top: int) -> int:
    # Screenshot and OCR map size region
    ocr_result = ocr_screenshot_region(
        left + 1256,
        top + 570,
        20,
        17,
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
    if team_selection_histograms[0] == HISTOGRAMS['teams']['usmc']['active'] or \
            team_selection_histograms[0] == HISTOGRAMS['teams']['eu']['active']:
        # Player is on USMC/EU team
        team = 0
    elif team_selection_histograms[1] == HISTOGRAMS['teams']['mec']['active'] or \
            team_selection_histograms[1] == HISTOGRAMS['teams']['china']['active']:
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


def get_sever_player_count(left: int, top: int) -> int:
    # Press/hold tab
    press_key(0x0f)
    time.sleep(.5)

    # Take screenshot
    screenshot = pyautogui.screenshot(region=(left + 180, top + 656, 647, 17))
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


def ocr_player_name(left: int, top: int) -> str:
    screenshot = pyautogui.screenshot(region=(left + 875, top + 471, 110, 100))
    orc_results = []
    custom_config = r'--oem 3 --psm 7'
    for i in range(0, screenshot.height, 6):
        cropped = ImageOps.crop(screenshot, (0, i, 0, screenshot.height - (12 + i)))
        inverted = ImageOps.autocontrast(ImageOps.invert(cropped))
        orc_results.append(pytesseract.image_to_string(inverted, config=custom_config))

    return orc_results[-1]


def init_game_instance(bf2_path: str, player_name: str, player_pass: str,
                       server_ip: str = None, server_port: str = None) -> None:
    # Init shell
    shell = win32com.client.Dispatch("WScript.Shell")

    # Prepare command
    command = f'cmd /c start /b /d "{bf2_path}" BF2.exe +restart 1 ' \
              f'+playerName "{player_name}" +playerPassword "{player_pass}" ' \
              f'+szx 1280 +szy 720 +fullscreen 0 +wx 5 +wy 5 ' \
              f'+multi 1 +developer 1 +disableShaderCache 1 +ignoreAsserts 1'

    # Add server details to command if provided
    if server_ip is not None and server_port is not None:
        command += f' +joinServer {server_ip} +port {server_port}'

    # Run command
    shell.Run(command)
    time.sleep(25)


def connect_to_server(left: int, top: int, server_ip: str, server_port: str, server_pass: str = None) -> bool:
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

    check_count = 0
    check_limit = 10
    connect_to_ip_button_present = False
    while not connect_to_ip_button_present and check_count < check_limit:
        connect_to_ip_button_present = 'connect to ip' in ocr_screenshot_region(
            left + 50,
            top + 448,
            110,
            18,
            True
        )
        check_count += 1
        time.sleep(1)

    if not connect_to_ip_button_present:
        return False

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

    return True


def disconnect_from_server(left: int, top: int) -> None:
    # Press ESC
    auto_press_key(0x01)
    time.sleep(5)
    # Move cursor onto disconnect button and click
    pyautogui.moveTo(left + 1210, top + 725)
    time.sleep(.2)
    pyautogui.leftClick()


def close_game_message(left: int, top: int) -> None:
    # Move cursor onto ok button and click
    pyautogui.moveTo(left + 806, top + 412)
    time.sleep(.2)
    pyautogui.leftClick()


def join_game(left: int, top: int) -> None:
    # Move cursor onto join game button and click
    pyautogui.moveTo(left + 1210, top + 725)
    time.sleep(.2)
    pyautogui.leftClick()


def spawn_suicide(map_name: str, map_size: int, team: int, left: int, top: int) -> bool:
    # Make sure spawning on map and size is supported
    if map_name not in SPAWN_COORDINATES.keys() or \
            str(map_size) not in SPAWN_COORDINATES[map_name].keys():
        raise UnsupportedMapException('No coordinates for current map/size')

    # Reset mouse to top left corner
    mouse_reset_legacy()

    # Select default spawn based on current team
    spawn_coordinates = SPAWN_COORDINATES[map_name][str(map_size)][team]
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
    mouse_move_legacy(250, 50)
    time.sleep(0.3)
    mouse_click_legacy()

    # Reset cursor once more
    mouse_reset_legacy()

    suicide_button_present = 'suicide' in ocr_screenshot_region(
        left + 940,
        top + 678,
        75,
        19,
        True
    )

    if suicide_button_present:
        # Click suicide button
        mouse_move_legacy(469, 459)
        time.sleep(.3)
        mouse_click_legacy()
        time.sleep(.5)

    return suicide_button_present


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


def check_if_player_afk(left: int, top: int, right: int, bottom: int) -> bool:
    histograms = []

    # Take 3 screenshots and calculate histograms
    for i in range(0, 3):
        # Take screenshot
        screenshot = pyautogui.screenshot(region=(left + 8, top + 31, right - left - 16, bottom - top - 40))
        # Convert PIL to cv2 image
        cvScreenshot = cv2.cvtColor(np.asarray(screenshot), cv2.COLOR_RGB2BGR)
        # Calculate histogram
        histograms.append(cv2.calcHist([cvScreenshot], [0], None, [256], [0, 256]))

        time.sleep(.75)

    histogram_deltas = []
    # Calculate histogram differences
    for j in range (0, len(histograms) -1):
        histogram_deltas.append(cv2.compareHist(histograms[j], histograms[j+1], cv2.HISTCMP_BHATTACHARYYA))

    # Take average of deltas
    average_delta = np.average(histogram_deltas)

    return average_delta <= .015


parser = argparse.ArgumentParser(description='Launch and control a Battlefield 2 spectator instance')
parser.add_argument('--version', action='version', version='bf2-auto-spectator v0.1.5')
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
bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:', 'BF2')
print_log(f'Found window: {bf2Window}')

# Connect to server if requested/required
if not args.start_game and args.connect or args.start_game and args.server_pass is not None:
    try:
        win32gui.ShowWindow(bf2Window['handle'], win32con.SW_SHOW)
        win32gui.SetForegroundWindow(bf2Window['handle'])

        # Connect to server
        print_log('Connecting to server')
        connected = connect_to_server(
            bf2Window['rect'][0],
            bf2Window['rect'][1],
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

# Start with 4 to switch away from dead spectator right away
iterationsOnPlayer = 4
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
    if gameInstanceState.error_restart_required():
        if bf2Window is not None:
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
            args.player_pass,
            gameInstanceState.get_server_ip(),
            gameInstanceState.get_server_port()
        )
        # Update window dict
        bf2Window = find_window_by_title('BF2 (v1.5.3153-802.0, pid:', 'BF2')
        # Reset state
        gameInstanceState.restart_reset()
        # Unless we are joining a password server, spectator should be on server after restart
        if gameInstanceState.get_server_password() is None:
            gameInstanceState.set_spectator_on_server(True)
        continue

    # Make sure we are still in the game
    gameMessagePresent = check_for_game_message(bf2Window['rect'][0], bf2Window['rect'][1])
    if gameMessagePresent:
        print_log('Game message present, ocr-ing message')
        gameMessage = ocr_game_message(bf2Window['rect'][0], bf2Window['rect'][1])

        # Close game message to enable actions
        close_game_message(bf2Window['rect'][0], bf2Window['rect'][1])

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

    # Player is not on server, check if rejoining is possible and makes sense
    if not gameInstanceState.spectator_on_server():
        # Check number of free slots
        # TODO
        # (Re-)connect to server
        print_log('(Re-)Connecting to server')
        connected = connect_to_server(bf2Window['rect'][0], bf2Window['rect'][1], args.server_ip, args.server_port)
        # Treat re-connecting as map rotation (state wise)
        gameInstanceState.map_rotation_reset()
        time.sleep(5)
        # Update state
        gameInstanceState.set_spectator_on_server(connected)
        continue

    onRoundFinishScreen = check_if_round_ended(bf2Window['rect'][0], bf2Window['rect'][1])
    mapIsLoading = check_if_map_is_loading(bf2Window['rect'][0], bf2Window['rect'][1])
    mapBriefingPresent = check_for_map_briefing(bf2Window['rect'][0], bf2Window['rect'][1])
    if mapIsLoading:
        print_log('Map is loading')
        # Reset state once if it still reflected to be on the (same) map
        if gameInstanceState.rotation_on_map():
            print_log('Performing map rotation reset')
            gameInstanceState.map_rotation_reset()
        iterationsOnPlayer = 4
        time.sleep(3)
    elif mapBriefingPresent:
        print_log('Map briefing present, checking map')
        currentMapName = get_map_name(bf2Window['rect'][0], bf2Window['rect'][1])
        currentMapSize = get_map_size(bf2Window['rect'][0], bf2Window['rect'][1])

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
            joinGameButtonPresent = check_for_join_game_button(bf2Window['rect'][0], bf2Window['rect'][1])

            if joinGameButtonPresent:
                # TODO
                pass

        time.sleep(3)
    elif onRoundFinishScreen:
        print_log('Game is on round finish screen')
        # Reset state
        gameInstanceState.round_end_reset()
        # Set counter to 4 again to skip spectator
        iterationsOnPlayer = 4
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

        spawnMenuVisible = check_if_spawn_menu_visible(bf2Window['rect'][0], bf2Window['rect'][1])
        if not spawnMenuVisible:
            print_log('Spawn menu not visible, opening with enter')
            auto_press_key(0x1c)
            time.sleep(1.5)
            continue

        print_log('Determining team')
        currentTeam = get_player_team_histogram(bf2Window['rect'][0], bf2Window['rect'][1])
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
                    gameInstanceState.get_round_team(),
                    bf2Window['rect'][0],
                    bf2Window['rect'][1]
                )
                print_log('Spawn succeeded' if spawnSucceeded else 'Spawn failed, retrying')
                gameInstanceState.set_round_spawned(spawnSucceeded)
            except UnsupportedMapException as e:
                print_log('Spawning not supported on current map/sizec')
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
            disconnect_from_server(bf2Window['rect'][0], bf2Window['rect'][1])
            time.sleep(3)
            # Update state
            gameInstanceState.set_spectator_on_server(False)
            continue
    elif not onRoundFinishScreen and not gameInstanceState.hud_hidden():
        print_log('Hiding hud')
        toggle_hud(0)
        gameInstanceState.set_hud_hidden(True)
        # Increase round number/counter
        gameInstanceState.increase_round_num()
        # Spectator has "entered" map, update state accordingly
        gameInstanceState.set_rotation_on_map(True)
    elif not onRoundFinishScreen and iterationsOnPlayer < 4:
        # Check if player is afk
        if check_if_player_afk(bf2Window['rect'][0], bf2Window['rect'][1], bf2Window['rect'][2], bf2Window['rect'][3]):
            print_log('Player is afk')
            iterationsOnPlayer = 4
        else:
            print_log('Nothing to do, stay on player')
            iterationsOnPlayer += 1
            time.sleep(4.5)
    elif not onRoundFinishScreen:
        print_log('Rotating to next player')
        auto_press_key(0x2e)
        iterationsOnPlayer = 0

    # serverIsFull = get_sever_player_count(bf2Window['rect'][0], bf2Window['rect'][1]) == 64
    # print_log(f'Server is full {serverIsFull}')
    # if serverIsFull and gameInstanceState.spectator_on_server():
    #     disconnect_from_server(bf2Window['rect'][0], bf2Window['rect'][1])
    #     gameInstanceState.set_spectator_on_server(False)
    #     time.sleep(30)
