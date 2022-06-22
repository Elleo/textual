import rich.repr
from ..message import Message
from .._types import MessageTarget

@rich.repr.auto
class FileClick(Message, bubble=True):
    def __init__(self, sender: MessageTarget, path: str) -> None:
        self.path = path
        super().__init__(sender)
