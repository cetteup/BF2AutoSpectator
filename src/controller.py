import logging

import requests

from typing import Optional


class Controller:
    __base_uri: str
    __app_key: str
    __timeout: int

    def __init__(self, base_uri: str, app_key: str, timeout: int):
        self.__base_uri = base_uri
        self.__app_key = app_key
        self.__timeout = timeout

    def post_current_server(self, server_ip: str, server_port: str, server_pass: str = None,
                            in_rotation: bool = False) -> bool:
        request_ok = False
        try:
            response = requests.post(
                f'{self.__base_uri}/servers/current',
                data={
                    'app_key': self.__app_key,
                    'ip': server_ip,
                    'port': server_port,
                    'password': server_pass,
                    'in_rotation': str(in_rotation).lower()
                },
                timeout=self.__timeout
            )

            if response.status_code == 200:
                request_ok = True
        except Exception as e:
            logging.error(e)

        return request_ok

    def get_join_server(self) -> Optional[dict]:
        join_sever = None
        try:
            response = requests.get(f'{self.__base_uri}/servers/join', timeout=self.__timeout)

            if response.status_code == 200:
                join_sever = response.json()
        except Exception as e:
            logging.error(e)

        return join_sever

    def get_commands(self) -> dict:
        commands = {}
        try:
            response = requests.get(
                f'{self.__base_uri}/commands',
                params={'app_key': self.__app_key},
                timeout=self.__timeout
            )

            if response.status_code == 200:
                commands = response.json()
        except Exception as e:
            logging.error(e)

        return commands

    def post_commands(self, commands: dict) -> bool:
        request_ok = False
        try:
            response = requests.post(
                f'{self.__base_uri}/commands',
                data={
                    'app_key': self.__app_key,
                    **commands
                },
                timeout=self.__timeout
            )

            if response.status_code == 200:
                request_ok = True
        except Exception as e:
            logging.error(e)

        return request_ok
