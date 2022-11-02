from typing import Dict

from BF2AutoSpectator.common.classes import Singleton


class CommandStore(metaclass=Singleton):
    commands: Dict[str, bool]

    def __init__(self):
        self.commands = {}

    def set(self, key: str, value: bool):
        self.commands[key] = value

    def get(self, key: str) -> bool:
        return self.commands.get(key, False)

    def pop(self, key: str) -> bool:
        if key not in self.commands:
            return False

        return self.commands.pop(key)
