import os
from datetime import datetime, timedelta
from typing import Tuple, Optional

from BF2AutoSpectator.common import constants
from BF2AutoSpectator.common.classes import Singleton


class Config(metaclass=Singleton):
    ROOT_DIR: str = os.path.dirname(__file__).replace('\\BF2AutoSpectator\\common', '')
    PWD: str = os.getcwd()
    DEBUG_DIR: str = os.path.join(PWD, f'{constants.APP_NAME}-debug')

    __player_name: str
    __player_pass: str
    __server_ip: str
    __server_port: str
    __server_pass: Optional[str]
    __server_mod: str

    __game_path: str
    __tesseract_path: str
    __limit_rtl: bool
    __instance_rtl: int
    __map_load_delay: int

    __use_controller: bool
    __controller_base_uri: str
    __control_obs: bool
    __obs_url: str
    __obs_source_name: str

    __resolution: str
    __debug_screenshot: bool

    __min_iterations_on_player: int
    __max_iterations_on_player: int
    __max_iterations_on_default_camera_view: int
    __lockup_iterations_on_spawn_menu: int

    __player_rotation_paused: bool = False
    __player_rotation_paused_until: datetime = None

    def set_options(self, player_name: str, player_pass: str, server_ip: str, server_port: str, server_pass: str,
                    server_mod: str, game_path: str, tesseract_path: str, limit_rtl: bool, instance_rtl: int, map_load_delay: int,
                    use_controller: bool, controller_base_uri: str, control_obs: bool, obs_url: str, obs_source_name: str,
                    resolution: str, debug_screenshot: bool,
                    min_iterations_on_player: int, max_iterations_on_player: int,
                    max_iterations_on_default_camera_view: int, lockup_iterations_on_spawn_menu: int):
        self.__player_name = player_name
        self.__player_pass = player_pass
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_pass = server_pass
        self.__server_mod = server_mod

        self.__game_path = game_path
        self.__tesseract_path = tesseract_path
        self.__limit_rtl = limit_rtl
        self.__instance_rtl = instance_rtl
        self.__map_load_delay = map_load_delay

        self.__use_controller = use_controller
        self.__controller_base_uri = controller_base_uri
        self.__control_obs = control_obs
        self.__obs_url = obs_url
        self.__obs_source_name = obs_source_name

        self.__resolution = resolution

        self.__debug_screenshot = debug_screenshot

        self.__min_iterations_on_player = min_iterations_on_player
        self.__max_iterations_on_player = max_iterations_on_player
        self.__max_iterations_on_default_camera_view = max_iterations_on_default_camera_view
        self.__lockup_iterations_on_spawn_menu = lockup_iterations_on_spawn_menu

    def get_player_name(self) -> str:
        return self.__player_name

    def get_player_pass(self) -> str:
        return self.__player_pass

    def set_server(self, server_ip: str, server_port: str, server_pass: Optional[str], server_mod: str) -> None:
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_pass = server_pass
        self.__server_mod = server_mod

    def get_server(self) -> Tuple[str, str, Optional[str], str]:
        return self.__server_ip, self.__server_port, self.__server_pass, self.__server_mod

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

    def set_server_mod(self, server_mod: str) -> None:
        self.__server_mod = server_mod

    def get_server_mod(self) -> str:
        return self.__server_mod

    def get_game_path(self) -> str:
        return self.__game_path

    def get_tesseract_path(self) -> str:
        return self.__tesseract_path

    def limit_rtl(self) -> bool:
        return self.__limit_rtl

    def get_instance_trl(self) -> int:
        return self.__instance_rtl

    def get_map_load_delay(self) -> int:
        return self.__map_load_delay

    def use_controller(self) -> bool:
        return self.__use_controller

    def get_controller_base_uri(self) -> str:
        return self.__controller_base_uri

    def control_obs(self) -> bool:
        return self.__control_obs

    def get_obs_url(self) -> str:
        return self.__obs_url

    def get_obs_source_name(self) -> str:
        return self.__obs_source_name

    def get_resolution(self) -> str:
        return self.__resolution

    def debug_screenshot(self) -> bool:
        return self.__debug_screenshot

    def set_debug_screenshot(self, debug_screenshot: bool) -> None:
        self.__debug_screenshot = debug_screenshot

    def get_min_iterations_on_player(self) -> int:
        return self.__min_iterations_on_player

    def get_max_iterations_on_player(self) -> int:
        return self.__max_iterations_on_player

    def get_max_iterations_on_default_camera_view(self) -> int:
        return self.__max_iterations_on_default_camera_view

    def get_lockup_iterations_on_spawn_menu(self) -> int:
        return self.__lockup_iterations_on_spawn_menu

    def player_rotation_paused(self) -> bool:
        return self.__player_rotation_paused

    def get_player_rotation_paused_until(self) -> datetime:
        return self.__player_rotation_paused_until

    def pause_player_rotation(self, pause_for_minutes: int) -> None:
        self.__player_rotation_paused = True
        self.__player_rotation_paused_until = datetime.now() + timedelta(minutes=pause_for_minutes)

    def unpause_player_rotation(self) -> None:
        self.__player_rotation_paused = False
