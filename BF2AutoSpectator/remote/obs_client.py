from typing import Optional
from urllib.parse import urlparse

import obsws_python as obs

from BF2AutoSpectator.common.exceptions import ClientNotConnectedException


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

    def __ensure_connected(self) -> None:
        if not hasattr(self, 'obs'):
            raise ClientNotConnectedException('OBSClient is not connected')
