import socketio

from BF2AutoSpectator.common.commands import CommandStore
from BF2AutoSpectator.common.config import Config
from BF2AutoSpectator.common.logger import logger


class ControllerClient:
    base_uri: str

    sio: socketio.Client

    def __init__(self, base_uri: str):
        self.base_uri = base_uri

        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            logger.info('Connected to controller')

        @self.sio.event
        def disconnect():
            logger.warning('Disconnected from controller')

        @self.sio.on('join', namespace='/server')
        def on_join_server(join_server):
            logger.info(f'Controller sent a server to join ({join_server["ip"]}:{join_server["port"]})')
            config = Config()
            config.set_server(join_server['ip'], join_server['port'], join_server.get('password'), 'bf2')

        @self.sio.on('command')
        def on_command(command):
            logger.debug(f'Controller set command {command["key"]} to {command["value"]}')
            cs = CommandStore()
            cs.set(command['key'], command['value'])

    def connect(self) -> None:
        self.sio.connect(self.base_uri, namespaces=['/', '/server'])

    def disconnect(self) -> None:
        self.sio.disconnect()

    def __del__(self):
        self.sio.disconnect()

    def update_current_server(self, server_ip: str, server_port: str, server_pass: str = None) -> None:
        try:
            self.sio.emit('current', {
                'ip': server_ip,
                'port': server_port,
                'password': server_pass
            }, namespace='/server')
        except socketio.client.exceptions.SocketIOError as e:
            logger.error(f'Failed to send current server to controller ({e})')
