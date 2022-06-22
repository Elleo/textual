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
from ._tree_node import TreeNode, NodeID, NodeDataType


class TreeControl(Generic[NodeDataType], Widget):
    def __init__(
        self,
        label: TextType,
        data: NodeDataType,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        padding: PaddingDimensions = (1, 1),
    ) -> None:
        self.data = data

        self.node_id = NodeID(0)
        self.nodes: dict[NodeID, TreeNode[NodeDataType]] = {}
        self._tree = Tree(label)
        self.root: TreeNode[NodeDataType] = TreeNode(
            None, self.node_id, self, self._tree, label, data
        )

        self._tree.label = self.root
        self.nodes[NodeID(self.node_id)] = self.root
        super().__init__(name=name, id=id, classes=classes)
        self.padding = padding

    hover_node: Reactive[NodeID | None] = Reactive(None)
    cursor: Reactive[NodeID] = Reactive(NodeID(0), layout=True)
    cursor_line: Reactive[int] = Reactive(0, repaint=False)
    show_cursor: Reactive[bool] = Reactive(False, layout=True)

    def watch_show_cursor(self, value: bool) -> None:
        self.emit_no_wait(CursorMove(self, self.cursor_line))

    def watch_cursor_line(self, value: int) -> None:
        if self.show_cursor:
            self.emit_no_wait(CursorMove(self, value))

    async def add(
        self,
        node_id: NodeID,
        label: TextType,
        data: NodeDataType,
    ) -> None:
        parent = self.nodes[node_id]
        self.node_id = NodeID(self.node_id + 1)
        child_tree = parent._tree.add(label)
        child_node: TreeNode[NodeDataType] = TreeNode(
            parent, self.node_id, self, child_tree, label, data
        )
        parent.children.append(child_node)
        child_tree.label = child_node
        self.nodes[self.node_id] = child_node

        self.refresh(layout=True)

    def find_cursor(self) -> int | None:
        """Find the line location for the cursor node."""

        node_id = self.cursor
        line = 0

        stack: list[Iterator[TreeNode[NodeDataType]]]
        stack = [iter([self.root])]

        pop = stack.pop
        push = stack.append
        while stack:
            iter_children = pop()
            try:
                node = next(iter_children)
            except StopIteration:
                continue
            else:
                if node.node_id == node_id:
                    return line
                line += 1
                push(iter_children)
                if node.children and node.expanded:
                    push(iter(node.children))
        return None

    def render(self) -> RenderableType:
        return self._tree

    def render_node(self, node: TreeNode[NodeDataType]) -> RenderableType:
        label = (
            Text(node.label, no_wrap=True, overflow="ellipsis")
            if isinstance(node.label, str)
            else node.label
        )
        if node.node_id == self.hover_node:
            label.stylize("underline")
        label.apply_meta({"@click": f"click_label({node.node_id})", "tree_node": node.node_id})
        return label

    async def action_click_label(self, node_id: NodeID) -> None:
        node = self.nodes[node_id]
        self.cursor = node.node_id
        self.cursor_line = self.find_cursor() or 0
        self.show_cursor = False
        await self.post_message(TreeClick(self, node))

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        self.hover_node = event.style.meta.get("tree_node")

    async def on_key(self, event: events.Key) -> None:
        await self.dispatch_key(event)

    async def key_down(self, event: events.Key) -> None:
        event.stop()
        await self.cursor_down()

    async def key_up(self, event: events.Key) -> None:
        event.stop()
        await self.cursor_up()

    async def key_enter(self, event: events.Key) -> None:
        cursor_node = self.nodes[self.cursor]
        event.stop()
        await self.post_message(TreeClick(self, cursor_node))

    async def cursor_down(self) -> None:
        if not self.show_cursor:
            self.show_cursor = True
            return
        cursor_node = self.nodes[self.cursor]
        next_node = cursor_node.next_node
        if next_node is not None:
            self.cursor_line += 1
            self.cursor = next_node.node_id

    async def cursor_up(self) -> None:
        if not self.show_cursor:
            self.show_cursor = True
            return
        cursor_node = self.nodes[self.cursor]
        previous_node = cursor_node.previous_node
        if previous_node is not None:
            self.cursor_line -= 1
            self.cursor = previous_node.node_id


if __name__ == "__main__":

    from textual import events
    from textual.app import App

    class TreeApp(App):
        async def on_mount(self, event: events.Mount) -> None:
            await self.screen.dock(TreeControl("Tree Root", data="foo"))

        async def handle_tree_click(self, message: TreeClick) -> None:
            if message.node.empty:
                await message.node.add("foo")
                await message.node.add("bar")
                await message.node.add("baz")
                await message.node.expand()
            else:
                await message.node.toggle()

    TreeApp(log_path="textual.log").run()
