from __future__ import annotations


from typing import Generic, Iterator, NewType, TypeVar

import rich.repr
from rich.console import RenderableType
from rich.style import Style
from rich.text import Text, TextType
from rich.tree import Tree
from rich.padding import PaddingDimensions

from ..reactive import Reactive
from .._types import MessageTarget
from ..widget import Widget
from ..message import Message
from ..messages import CursorMove


NodeID = NewType("NodeID", int)


NodeDataType = TypeVar("NodeDataType")


@rich.repr.auto
class TreeNode(Generic[NodeDataType]):
    def __init__(
        self,
        parent: TreeNode[NodeDataType] | None,
        node_id: NodeID,
        control: TreeControl,
        tree: Tree,
        label: TextType,
        data: NodeDataType,
    ) -> None:
        self.parent = parent
        self.node_id = node_id
        self._control = control
        self._tree = tree
        self.label = label
        self.data = data
        self.loaded = False
        self._expanded = False
        self._empty = False
        self._tree.expanded = False
        self.children: list[TreeNode] = []

    def __rich_repr__(self) -> rich.repr.Result:
        yield "node_id", self.node_id
        yield "label", self.label
        yield "data", self.data

    @property
    def control(self) -> TreeControl:
        return self._control

    @property
    def empty(self) -> bool:
        return self._empty

    @property
    def expanded(self) -> bool:
        return self._expanded

    @property
    def is_cursor(self) -> bool:
        return self.control.cursor == self.node_id and self.control.show_cursor

    @property
    def tree(self) -> Tree:
        return self._tree

    @property
    def next_node(self) -> TreeNode[NodeDataType] | None:
        """The next node in the tree, or None if at the end."""

        if self.expanded and self.children:
            return self.children[0]
        else:

            sibling = self.next_sibling
            if sibling is not None:
                return sibling

            node = self
            while True:
                if node.parent is None:
                    return None
                sibling = node.parent.next_sibling
                if sibling is not None:
                    return sibling
                else:
                    node = node.parent

    @property
    def previous_node(self) -> TreeNode[NodeDataType] | None:
        """The previous node in the tree, or None if at the end."""

        sibling = self.previous_sibling
        if sibling is not None:

            def last_sibling(node) -> TreeNode[NodeDataType]:
                if node.expanded and node.children:
                    return last_sibling(node.children[-1])
                else:
                    return (
                        node.children[-1] if (node.children and node.expanded) else node
                    )

            return last_sibling(sibling)

        if self.parent is None:
            return None
        return self.parent

    @property
    def next_sibling(self) -> TreeNode[NodeDataType] | None:
        """The next sibling, or None if last sibling."""
        if self.parent is None:
            return None
        iter_siblings = iter(self.parent.children)
        try:
            for node in iter_siblings:
                if node is self:
                    return next(iter_siblings)
        except StopIteration:
            pass
        return None

    @property
    def previous_sibling(self) -> TreeNode[NodeDataType] | None:
        """Previous sibling or None if first sibling."""
        if self.parent is None:
            return None
        iter_siblings = iter(self.parent.children)
        sibling: TreeNode[NodeDataType] | None = None

        for node in iter_siblings:
            if node is self:
                return sibling
            sibling = node
        return None

    async def expand(self, expanded: bool = True) -> None:
        self._expanded = expanded
        self._tree.expanded = expanded
        self._control.refresh(layout=True)

    async def toggle(self) -> None:
        await self.expand(not self._expanded)

    async def add(self, label: TextType, data: NodeDataType) -> None:
        await self._control.add(self.node_id, label, data=data)
        self._control.refresh(layout=True)
        self._empty = False

    def __rich__(self) -> RenderableType:
        return self._control.render_node(self)
