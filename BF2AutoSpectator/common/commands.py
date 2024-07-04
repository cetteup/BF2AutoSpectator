from typing import Dict, Optional, Union

from BF2AutoSpectator.common.classes import Singleton


class CommandStore(metaclass=Singleton):
    commands: Dict[str, Union[bool, dict]]

    def __init__(self):
        self.commands = {}

    def set(self, key: str, value: Union[bool, dict]):
        self.commands[key] = value

    def get(self, key: str) -> Optional[Union[bool, dict]]:
        return self.commands.get(key)

    def pop(self, key: str) -> Optional[Union[bool, dict]]:
        if key not in self.commands:
            return None

        return self.commands.pop(key)
