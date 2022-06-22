import rich.repr
from typing import Generic
from ._tree_node import NodeDataType, TreeNode
from ..message import Message
from ..reactive import Reactive
from .._types import MessageTarget

@rich.repr.auto
class TreeClick(Generic[NodeDataType], Message, bubble=True):
    def __init__(self, sender: MessageTarget, node: TreeNode[NodeDataType]) -> None:
        self.node = node
        super().__init__(sender)
        
        def __rich_repr__(self) -> rich.repr.Result:
            yield "node", self.node

