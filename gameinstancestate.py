class GameInstanceState:
    # Global details
    __spectator_on_server: bool = False
    __hud_hidden: bool = False
    __active_join_possible: bool = False

    # TTL details
    __round_num: int = 0
    __rtl_restart_required: bool = False

    # Server details
    __server_ip: str = None
    __server_port: str = None
    __server_password: str = None
    __server_player_count: int = -1

    # Map details (map is as in one entry in the map rotation)
    __rotation_map_name: str = None
    __rotation_map_size: int = -1
    __round_spawned: bool = False
    __rotation_on_map: bool = False

    # Round details
    __round_team: int = -1
    __round_started_spectation: bool = False

    # Error details
    __error_unresponsive_count = 0
    __error_restart_required: bool = False

    def __init__(self, server_ip: str, server_port: str, server_password: str):
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__server_password = server_password

    # Global getter/setter functions
    def set_spectator_on_server(self, spectator_on_server: bool):
        self.__spectator_on_server = spectator_on_server

    def spectator_on_server(self) -> bool:
        return self.__spectator_on_server

    def set_hud_hidden(self, hud_hidden: bool):
        self.__hud_hidden = hud_hidden

    def hud_hidden(self) -> bool:
        return self.__hud_hidden

    def set_active_join_possible(self, active_join_possible: bool):
        self.__active_join_possible = active_join_possible

    def active_join_possible(self) -> bool:
        return self.__active_join_possible

    def increase_round_num(self):
        self.__round_num += 1

    def get_round_num(self) -> int:
        return self.__round_num

    def set_rtl_restart_required(self, restart_required: bool):
        self.__rtl_restart_required = restart_required

    def rtl_restart_required(self) -> bool:
        return self.__rtl_restart_required

    # Server getter/setter functions
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

    def set_server_player_count(self, player_count: int):
        self.__server_player_count = player_count

    def get_server_player_count(self) -> int:
        return self.__server_player_count

    def set_rotation_map_name(self, map_name: str):
        self.__rotation_map_name = map_name

    def get_rotation_map_name(self) -> str:
        return self.__rotation_map_name

    def set_rotation_map_size(self, map_size: int):
        self.__rotation_map_size = map_size

    def get_rotation_map_size(self) -> int:
        return self.__rotation_map_size

    def set_rotation_on_map(self, on_map: bool):
        self.__rotation_on_map = on_map

    def rotation_on_map(self) -> bool:
        return self.__rotation_on_map

    def set_round_team(self, team: int):
        self.__round_team = team

    def get_round_team(self) -> int:
        return self.__round_team

    def set_round_spawned(self, spawned: bool):
        self.__round_spawned = spawned

    def round_spawned(self) -> bool:
        return self.__round_spawned

    def set_round_started_spectation(self, startet_spectation: bool):
        self.__round_started_spectation = startet_spectation

    def round_started_spectation(self) -> bool:
        return self.__round_started_spectation

    def increase_error_unresponsive_count(self):
        self.__error_unresponsive_count += 1

    def get_error_unresponsive_count(self) -> int:
        return self.__error_unresponsive_count

    def set_error_restart_required(self, restart_required: bool):
        self.__error_restart_required = restart_required

    def error_restart_required(self) -> bool:
        return self.__error_restart_required

    # Reset relevant fields after map rotation
    def map_rotation_reset(self):
        self.__active_join_possible = False
        self.__rotation_map_name = None
        self.__rotation_map_size = -1
        self.__rotation_on_map = False
        self.__round_team = -1
        self.__round_spawned = False
        self.__round_started_spectation = False

    # Reset relevant fields when round ended
    def round_end_reset(self):
        self.__active_join_possible = False
        self.__round_team = -1
        self.__round_spawned = False
        self.__round_started_spectation = False

    def reset_error_unresponsive_count(self):
        self.__error_unresponsive_count = 0

    # Reset relevant fields after/on game restart
    def restart_reset(self):
        self.__spectator_on_server = False
        self.__hud_hidden = False
        self.__round_num = 0
        self.__active_join_possible = False
        self.__rotation_map_name = None
        self.__rotation_map_size = -1
        self.__rotation_on_map = False
        self.__round_team = -1
        self.__round_spawned = False
        self.__round_started_spectation = False
        self.__error_unresponsive_count = 0
        self.__error_restart_required = False
