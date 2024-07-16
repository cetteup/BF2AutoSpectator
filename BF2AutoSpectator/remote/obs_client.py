from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import obsws_python as obs

from BF2AutoSpectator.common.exceptions import ClientNotConnectedException
from BF2AutoSpectator.common.logger import logger


class OBSClient:
    host: str
    port: int
    password: str

    obs: Optional[obs.ReqClient]

    def __init__(self, url: str):
        pr = urlparse(url)
        self.host = pr.hostname
        self.port = pr.port
        self.password = pr.password

    def connect(self) -> None:
        self.obs = obs.ReqClient(host=self.host, port=self.port, password=self.password)

    def disconnect(self) -> None:
        if hasattr(self, 'obs'):
            self.obs.base_client.ws.close()

    def __del__(self):
        self.disconnect()

    def is_stream_active(self) -> bool:
        self.__ensure_connected()

        status = self.obs.get_stream_status()

        return status.output_active or status.output_reconnecting

    def start_stream(self) -> None:
        self.__ensure_connected()

        self.obs.start_stream()

    def stop_stream(self) -> None:
        self.__ensure_connected()

        self.obs.stop_stream()

    def set_capture_window(self, input_name: str, executable: str, title: str) -> None:
        self.__ensure_connected()

        resp = self.__try_get_input_settings(input_name)
        if resp is not None and resp.input_settings.get('capture_mode') == 'window':
            self.obs.set_input_settings(input_name, {
                'window': self.__format_window_title(executable, title)
            }, True)

    def __try_get_input_settings(self, input_name: str) -> Optional[dataclass]:
        try:
            return self.obs.get_input_settings(input_name)
        except obs.reqs.OBSSDKRequestError as e:
            logger.error(f'Failed to get input settings: {e}')

    def __ensure_connected(self) -> None:
        if not hasattr(self, 'obs'):
            raise ClientNotConnectedException('OBSClient is not connected')

    @staticmethod
    def __format_window_title(executable: str, title: str) -> str:
        escaped = title.replace(':', '#3A')
        return f'{escaped}:{escaped}:{executable}'
