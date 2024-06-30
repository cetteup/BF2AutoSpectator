from datetime import datetime, timedelta
from typing import Tuple, Optional


class GameInstanceState:
    # Global details
    __current_mod: str = None
    __spectator_on_server: bool = False
    __hud_hidden: bool = False
    __map_loading: bool = False
    __active_join_possible_after: datetime = None

    # TTL details
    __round_num: int = 0
    __rtl_restart_required: bool = False

    # Server details
    __server_ip: str = None
    __server_port: str = None
    __server_password: str = None

    # Map details (map is as in one entry in the map rotation)
    __rotation_map_load_delayed: bool = False
    __rotation_map_name: str = None
    __rotation_map_size: int = -1
    __rotation_game_mode: str = None
    __round_spawned: bool = False
    __round_spawn_randomize_coordinates: bool = False
    __round_freecam_toggle_spawn_attempted: bool = False
    __round_entered: bool = False

    # Round details
    __round_team: int = -1

    # Counters
    __iterations_on_spawn_menu: int = 0
    __iterations_on_default_camera_view: int = 0
    __iterations_on_player: int = 0

    # Error details
    __error_unresponsive_count = 0
    __error_restart_required: bool = False
    __halted_since: Optional[datetime] = None

    # Global getter/setter functions
    def set_spectator_on_server(self, spectator_on_server: bool):
        self.__spectator_on_server = spectator_on_server

    def spectator_on_server(self) -> bool:
        return self.__spectator_on_server

    def set_hud_hidden(self, hud_hidden: bool):
        self.__hud_hidden = hud_hidden

    def hud_hidden(self) -> bool:
        return self.__hud_hidden

    def set_map_loading(self, map_loading: bool):
        self.__map_loading = map_loading

    def map_loading(self) -> bool:
        return self.__map_loading

    def set_active_join_possible(self, after: float):
        self.__active_join_possible_after = datetime.now() + timedelta(seconds=after)

    def active_join_pending(self) -> bool:
        return self.__active_join_possible_after is not None

    def active_join_possible(self) -> bool:
        return self.__active_join_possible_after is not None and datetime.now() > self.__active_join_possible_after

    def increment_round_num(self):
        self.__round_num += 1

    def decrement_round_num(self):
        self.__round_num -= 1

    def get_round_num(self) -> int:
        return self.__round_num

    def set_rtl_restart_required(self, restart_required: bool):
        self.__rtl_restart_required = restart_required

    def rtl_restart_required(self) -> bool:
        return self.__rtl_restart_required

    # Server getter/setter functions
    def set_server(self, server_ip: str, server_port: str, server_password: str):
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_password = server_password

    def get_server(self) -> Tuple[str, str, str]:
        return self.__server_ip, self.__server_port, self.__server_password

    def set_server_ip(self, server_ip: str):
        self.__server_ip = server_ip

    def get_server_ip(self) -> str:
        return self.__server_ip

    def set_server_port(self, server_port: str):
        self.__server_port = server_port

    def get_server_port(self) -> str:
        return self.__server_port

    def set_server_password(self, server_password: str):
        self.__server_password = server_password

    def get_server_password(self) -> str:
        return self.__server_password

    def set_rotation_map_load_delayed(self, delayed: bool):
        self.__rotation_map_load_delayed = delayed

    def rotation_map_load_delayed(self) -> bool:
        return self.__rotation_map_load_delayed

    def set_rotation_map_name(self, map_name: str):
        self.__rotation_map_name = map_name

    def get_rotation_map_name(self) -> str:
        return self.__rotation_map_name

    def set_rotation_map_size(self, map_size: int):
        self.__rotation_map_size = map_size

    def get_rotation_map_size(self) -> int:
        return self.__rotation_map_size

    def set_rotation_game_mode(self, game_mode: str):
        self.__rotation_game_mode = game_mode

    def get_rotation_game_mode(self) -> str:
        return self.__rotation_game_mode

    def set_round_entered(self, entered: bool):
        self.__round_entered = entered

    def round_entered(self) -> bool:
        return self.__round_entered

    def set_round_team(self, team: int):
        self.__round_team = team

    def get_round_team(self) -> int:
        return self.__round_team

    def set_round_spawned(self, spawned: bool):
        self.__round_spawned = spawned

    def round_spawned(self) -> bool:
        return self.__round_spawned

    def set_round_spawn_randomize_coordinates(self, randomize: bool):
        self.__round_spawn_randomize_coordinates = randomize

    def get_round_spawn_randomize_coordinates(self) -> bool:
        return self.__round_spawn_randomize_coordinates

    def set_round_freecam_toggle_spawn_attempted(self, attempted: bool):
        self.__round_freecam_toggle_spawn_attempted = attempted

    def round_freecam_toggle_spawn_attempted(self) -> bool:
        return self.__round_freecam_toggle_spawn_attempted

    def increment_iterations_on_spawn_menu(self):
        self.__iterations_on_spawn_menu += 1

    def get_iterations_on_spawn_menu(self) -> int:
        return self.__iterations_on_spawn_menu

    def increment_iterations_on_default_camera_view(self):
        self.__iterations_on_default_camera_view += 1

    def get_iterations_on_default_camera_view(self) -> int:
        return self.__iterations_on_default_camera_view

    def set_iterations_on_player(self, iterations: int):
        self.__iterations_on_player = iterations

    def increment_iterations_on_player(self):
        self.__iterations_on_player += 1

    def get_iterations_on_player(self) -> int:
        return self.__iterations_on_player

    def increment_error_unresponsive_count(self):
        self.__error_unresponsive_count += 1

    def get_error_unresponsive_count(self) -> int:
        return self.__error_unresponsive_count

    def set_error_restart_required(self, restart_required: bool):
        self.__error_restart_required = restart_required

    def error_restart_required(self) -> bool:
        return self.__error_restart_required

    def set_halted(self, halted: bool):
        # Don't overwrite any existing timestamp
        if self.__halted_since is not None:
            return
        self.__halted_since = datetime.now() if halted else None

    def halted(self, grace_period: float = 0.0) -> bool:
        if self.__halted_since is None:
            return False
        return datetime.now() >= self.__halted_since + timedelta(seconds=grace_period)

    # Reset relevant fields after map rotation
    def map_rotation_reset(self):
        self.__active_join_possible_after = None
        self.__rotation_map_load_delayed = False
        self.__rotation_map_name = None
        self.__rotation_map_size = -1
        self.__rotation_game_mode = None
        self.__round_entered = False
        self.__round_team = -1
        self.__round_spawned = False
        self.__round_spawn_randomize_coordinates = False
        self.__round_freecam_toggle_spawn_attempted = False
        self.__iterations_on_spawn_menu = 0
        self.__iterations_on_default_camera_view = 0
        self.__iterations_on_player = 0

    # Reset relevant fields when round ended
    def round_end_reset(self):
        self.__active_join_possible_after = None
        self.__round_entered = False
        self.__round_team = -1
        self.__round_spawned = False
        self.__round_spawn_randomize_coordinates = False
        self.__round_freecam_toggle_spawn_attempted = False
        self.__iterations_on_spawn_menu = 0
        self.__iterations_on_default_camera_view = 0
        self.__iterations_on_player = 0

    def reset_iterations_on_spawn_menu(self):
        self.__iterations_on_spawn_menu = 0

    def reset_iterations_on_default_camera_view(self):
        self.__iterations_on_default_camera_view = 0

    def reset_iterations_on_player(self):
        self.__iterations_on_player = 0

    def reset_error_unresponsive_count(self):
        self.__error_unresponsive_count = 0

    # Reset relevant fields after/on game restart
    def restart_reset(self):
        self.__spectator_on_server = False
        self.__hud_hidden = False
        self.__map_loading = False
        self.__active_join_possible_after = None
        self.__round_num = 0
        self.__rotation_map_load_delayed = False
        self.__rotation_map_name = None
        self.__rotation_map_size = -1
        self.__rotation_game_mode = None
        self.__round_entered = False
        self.__round_team = -1
        self.__round_spawned = False
        self.__round_spawn_randomize_coordinates = False
        self.__round_freecam_toggle_spawn_attempted = False
        self.__iterations_on_spawn_menu = 0
        self.__iterations_on_default_camera_view = 0
        self.__iterations_on_player = 0
        self.__error_unresponsive_count = 0
        self.__error_restart_required = False
        self.__halted_since = None
