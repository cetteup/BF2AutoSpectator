import os
import constants

ROOT_DIR = os.path.dirname(__file__).replace('\\src', '')
PWD = os.getcwd()
DEBUG_DIR = os.path.join(PWD, f'{constants.APP_NAME}-debug')
