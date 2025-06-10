from typing import Optional

class CustomCommandManager:
    def __init__(self):
        self.user_defined_cmds: dict[str, str] = {}

    def add_command(self, name: str, code: str) -> None:
        self.user_defined_cmds[name] = code

    def remove_command(self, name: str) -> None:
        if name in self.user_defined_cmds:
            del self.user_defined_cmds[name]

    def get_command(self, name: str) -> Optional[str]:
        return self.user_defined_cmds.get(name)
