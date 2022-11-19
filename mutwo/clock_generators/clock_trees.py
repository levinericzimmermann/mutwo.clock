from __future__ import annotations
import abc
import dataclasses
import typing

import ranges
import treelib

from mutwo import clock_generators
from mutwo import core_events
from mutwo import core_parameters


__all__ = ("ClockLayer", "ClockTree")


@dataclasses.dataclass(frozen=True)
class ClockLayer(abc.ABC):
    """Define layer in a :class:`ClockTree`.

    :param tree: The tree in which the layer exists.
    :param node: The node to which the layer is assigned via the
        data attribute.
    :param fetch_event: Any callable object which returns an event.
    :param fetch_child: An instance of any child of
        `clock_generators.PickSample`
    :param event_count_range: Describes how many events min and
        how many event max are created at each `pop_event` call
        (e.g. how often :class:`ClockLayer` alternately calls
        `fetch_event` and `fetch_child().data.pop_event()`).
    :param pick_event_count: callable object which picks a
        valid value from the `event_count_range` for the
        current call. Gets as an input
        `tuple(range(event_count_range.start, event_count_range.end))`.
    """

    tree: treelib.Tree
    node: treelib.Node
    fetch_event: typing.Callable[[], core_events.abc.Event]
    fetch_child: clock_generators.PickSample
    event_count_range: ranges.Range = ranges.Range(1, 2)
    pick_event_count: typing.Callable[
        [tuple[int, ...]], int
    ] = lambda event_count_tuple: event_count_tuple[0]

    # It is necessary to differentiate between SimpleEvent inside
    # a TaggedSequentialEvent inside the control event returned by
    # pop event which are active (e.g. when there is the cycle running)
    # and which are inactive (e.g. when there is no cycle running).
    # Because: a layer can have multiple children and usually only one
    # of the children is selected. So it means there are other children,
    # who actually need event to fill out the space, but those events need
    # to tell: Here my layer is not active. And this communication is done
    # via the "is_active_parameter_name" parameter. The parameter is
    # assigned on-the-fly to plain `SimpleEvent` objects.
    is_active_parameter_name = "is_active"

    @property
    def child_tuple(self) -> tuple[treelib.Node, ...]:
        return tuple(
            self.tree[key] for key in self.node.successors(self.tree.identifier)
        )

    def pop_event(
        self,
    ) -> tuple[
        core_events.SequentialEvent,
        core_events.SimultaneousEvent[
            core_events.TaggedSequentialEvent[core_events.SimpleEvent]
        ],
    ]:
        """Pop event from layer and children.

        Each pop event call returns a tuple with two different events.

        The first event is the actual clock event layer, it represents
        the detailed musical content of a clock.

        The second event functions as a control event. It shows the formal
        colotomic structure of the clock event. Each layer of the
        tree is one tagged sequential event inside this control event.
        Each repeating call of `pop_event` is a new `SimpleEvent` inside
        the `TaggedSequentialEvent`. So in this way it is possible to see
        how long each cycle of each layer lasts. This is helpful to assign
        specific musical meanings to each layer. The tag of each
        `TaggedSequentialEvent` is the identifier of the layer node.
        """

        # We don't necessarily know all children during initialization time,
        # so the function may need to update its internal set.
        self.fetch_child.refresh(self.child_tuple)

        sequential_event = core_events.SequentialEvent([])
        control_event = core_events.SimultaneousEvent(
            [core_events.TaggedSequentialEvent([], tag=self.node.identifier)]
        )
        event_count = self.pick_event_count(  # type: ignore
            tuple(range(self.event_count_range.start, self.event_count_range.end))
        )

        offset = core_parameters.DirectDuration(0)

        for _ in range(event_count):

            if (event := self.fetch_event()) is not None:  # type: ignore
                sequential_event.append(event)

            if (child_node := self.fetch_child()) is not None:
                child_clock_event, child_control_event = child_node.data.pop_event()

                sequential_event.extend(child_clock_event)

                for child_sequential_control_event in child_control_event:
                    try:
                        control_event[child_sequential_control_event.tag].extend(
                            child_sequential_control_event
                        )
                    except KeyError:
                        delay = offset + event.duration
                        if delay > 0:
                            child_sequential_control_event.insert(
                                0,
                                core_events.SimpleEvent(delay).set(
                                    self.is_active_parameter_name, False
                                ),
                            )
                        control_event.append(child_sequential_control_event)

            sequential_event_duration = sequential_event.duration

            for child_sequential_control_event in control_event[1:]:
                difference = (
                    sequential_event_duration - child_sequential_control_event.duration
                )
                if difference > 0:
                    child_sequential_control_event.append(
                        core_events.SimpleEvent(difference).set(
                            self.is_active_parameter_name, False
                        )
                    )

            cycle_duration = sequential_event_duration - offset
            control_simple_event = core_events.SimpleEvent(cycle_duration).set(
                self.is_active_parameter_name, True
            )

            control_event[0].append(control_simple_event)

            offset = sequential_event_duration

        control_event.tie_by(
            lambda event0, event1: (not event0.is_active) and (not event1.is_active),
            event_type_to_examine=core_events.SimpleEvent,
        )

        return sequential_event, control_event


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
        event_count_range: ranges.Range = ranges.Range(1, 2),
        pick_event_count: typing.Callable[
            [tuple[int, ...]], int
        ] = lambda event_count_tuple: event_count_tuple[0],
    ):
        if parent_identifier is None:
            parent = None
        else:
            parent = self[parent_identifier]
        node = self.create_node(identifier=identifier, parent=parent)
        node.data = ClockLayer(
            self, node, fetch_event, fetch_child, event_count_range, pick_event_count
        )
