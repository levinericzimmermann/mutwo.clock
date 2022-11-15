from __future__ import annotations
import abc
import dataclasses
import typing

import treelib

from mutwo import clock_generators
from mutwo import core_events


__all__ = ("ClockLayer", "ClockTree")


@dataclasses.dataclass(frozen=True)
class ClockLayer(abc.ABC):
    """Define layer in a :class:`ClockTree`."""

    tree: treelib.Tree
    node: treelib.Node
    fetch_event: typing.Callable[[], core_events.abc.Event]
    fetch_child: clock_generators.PickSample

    @property
    def child_tuple(self) -> tuple[treelib.Node, ...]:
        return tuple(
            self.tree[key] for key in self.node.successors(self.tree.identifier)
        )

    def pop_event(
        self,
    ) -> core_events.SequentialEvent:
        sequential_event = core_events.SequentialEvent([])

        if (event := self.fetch_event()) is not None:
            sequential_event.append(event)

        # We don't necessarily know all children during initialization time,
        # so the function may need to update its internal set.
        self.fetch_child.refresh(self.child_tuple)
        if (child_node := self.fetch_child()) is not None:
            sequential_event.extend(child_node.data.pop_event())

        return sequential_event


class ClockTree(treelib.Tree):
    """Create rhythmic layers.

    The basic API for this class is the `create_layer` method.
    """

    def create_layer(
        self,
        identifier: str,
        parent_identifier: typing.Optional[str],
        fetch_event: typing.Callable[[], core_events.abc.Event],
        fetch_child: clock_generators.PickSample,
    ):
        if parent_identifier is None:
            parent = None
        else:
            parent = self[parent_identifier]
        node = self.create_node(identifier=identifier, parent=parent)
        node.data = ClockLayer(self, node, fetch_event, fetch_child)
