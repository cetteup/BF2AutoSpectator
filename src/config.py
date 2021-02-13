import os
from typing import Tuple

import constants


class Config:
    ROOT_DIR: str = os.path.dirname(__file__).replace('\\src', '')
    PWD: str = os.getcwd()
    DEBUG_DIR: str = os.path.join(PWD, f'{constants.APP_NAME}-debug')

    __player_name: str
    __player_pass: str
    __server_ip: str
    __server_port: str
    __server_pass: str

    __game_path: str
    __limit_rtl: bool
    __instance_rtl: int

    __use_controller: bool
    __controller_base_uri: str
    __controller_app_key: str

    __resolution: str
    __window_size: Tuple[int, int]
    __debug_screenshot: bool

    __iterations_on_player: int
    __max_iterations_on_player: int

    def __init__(self, player_name: str, player_pass: str, server_ip: str, server_port: str, server_pass: str,
                 game_path: str, limit_rtl: bool, instance_rtl: int, use_controller: bool, controller_base_uri: str,
                 controller_app_key: str, resolution: str, debug_screenshot: bool, max_iterations_on_player: int):
        self.__player_name = player_name
        self.__player_pass = player_pass
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_pass = server_pass

        self.__game_path = game_path
        self.__limit_rtl = limit_rtl
        self.__instance_rtl = instance_rtl

        self.__use_controller = use_controller
        self.__controller_base_uri = controller_base_uri
        self.__controller_app_key = controller_app_key

        self.__resolution = resolution
        # Set window size based on resolution
        if self.__resolution == '720p':
            self.__window_size = (1280, 720)
        elif self.__resolution == '900p':
            self.__window_size = (1600, 900)

        self.__debug_screenshot = debug_screenshot

        self.__max_iterations_on_player = max_iterations_on_player

    def get_player_name(self) -> str:
        return self.__player_name

    def get_player_pass(self) -> str:
        return self.__player_pass

    def set_server(self, server_ip: str, server_port: str, server_pass: str) -> None:
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_pass = server_pass

    def get_server(self) -> Tuple[str, str, str]:
        return self.__server_ip, self.__server_port, self.__server_pass

    def set_server_ip(self, server_ip: str) -> None:
        self.__server_ip = server_ip

    def get_server_ip(self) -> str:
        return self.__server_ip

    def set_server_port(self, server_port: str) -> None:
        self.__server_port = server_port

    def get_server_port(self) -> str:
        return self.__server_port

    def set_server_pass(self, server_pass: str) -> None:
        self.__server_pass = server_pass

    def get_server_pass(self) -> str:
        return self.__server_pass

    def get_game_path(self) -> str:
        return self.__game_path

    def limit_rtl(self) -> bool:
        return self.__limit_rtl

    def get_instance_trl(self) -> int:
        return self.__instance_rtl

    def use_controller(self) -> bool:
        return self.__use_controller

    def get_controller_base_uri(self) -> str:
        return self.__controller_base_uri

    def get_controller_app_key(self) -> str:
        return self.__controller_app_key

    def get_resolution(self) -> str:
        return self.__resolution

    def get_window_size(self) -> Tuple[int, int]:
        return self.__window_size

    def debug_screenshot(self) -> bool:
        return self.__debug_screenshot

    def get_max_iterations_on_player(self) -> int:
        return self.__max_iterations_on_player
