import logging

import requests

from typing import Optional, Dict


class Controller:
    __base_uri: str
    __app_key: str
    __timeout: int

    def __init__(self, base_uri: str, app_key: str, timeout: int):
        self.__base_uri = base_uri
        self.__app_key = app_key
        self.__timeout = timeout

    def request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict] = None,
            data: Optional[Dict] = None
    ) -> requests.Response:
        return requests.request(
            method,
            f'{self.__base_uri}/{endpoint}',
            params=params,
            data=data,
            headers={'APP_KEY': self.__app_key},
            timeout=self.__timeout
        )

    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        return self.request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        return self.request('POST', endpoint, data=data)

    def post_current_server(self, server_ip: str, server_port: str, server_pass: str = None,
                            in_rotation: bool = False) -> bool:
        request_ok = False
        try:
            response = self.post(
                'servers/current',
                data={
                    'ip': server_ip,
                    'port': server_port,
                    'password': server_pass,
                    'in_rotation': str(in_rotation).lower()
                }
            )

            if response.status_code == 200:
                request_ok = True
        except Exception as e:
            logging.error(e)

        return request_ok

    def get_join_server(self) -> Optional[dict]:
        join_sever = None
        try:
            response = self.get('servers/join')

            if response.status_code == 200:
                join_sever = response.json()
        except Exception as e:
            logging.error(e)

        return join_sever

    def get_commands(self) -> dict:
        commands = {}
        try:
            response = self.get('commands')

            if response.status_code == 200:
                commands = response.json()
        except Exception as e:
            logging.error(e)

        return commands

    def post_commands(self, commands: dict) -> bool:
        request_ok = False
        try:
            response = self.post('commands', data=commands)

            if response.status_code == 200:
                request_ok = True
        except Exception as e:
            logging.error(e)

        return request_ok
