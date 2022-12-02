import abc
import typing

from mutwo import clock_converters
from mutwo import clock_events
from mutwo import clock_interfaces
from mutwo import clock_generators
from mutwo import core_converters
from mutwo import core_events
from mutwo import core_parameters
from mutwo import core_utilities
from mutwo import timeline_interfaces

__all__ = (
    "ModalEventToClockTree",
    "ApplyClockTreeOnModalEvent",
    "ModalSequentialEventToEventPlacementTuple",
    "ModalSequentialEventToClockLine",
    "ModalSequentialEventToClockEvent",
)


class ModalEventToClockTree(core_converters.abc.Converter):
    @abc.abstractmethod
    def convert(
        self, modal_event_to_convert: clock_events.ModalEvent
    ) -> clock_generators.ClockTree:
        ...


class ApplyClockTreeOnModalEvent(core_converters.abc.SymmetricalEventConverter):
    def __init__(
        self,
        modal_event_to_clock_tree: ModalEventToClockTree,
    ):
        self._modal_event_to_clock_tree = modal_event_to_clock_tree

    def _convert_simple_event(
        self,
        event_to_convert: core_events.SimpleEvent,
        absolute_entry_delay: core_parameters.abc.Duration | float | int,
        depth: int = 0,
    ) -> core_events.SimpleEvent:
        e = event_to_convert.copy()
        if isinstance(e, clock_events.ModalEvent):
            clock_tree = self._modal_event_to_clock_tree.convert(event_to_convert)
            (e.clock_event, e.control_event) = clock_tree.get_node(
                clock_tree.root
            ).data.pop_event()
            # FIXME(Because currently a clock tree doesn't return a ClockEvent
            # [which is a SimultaneousEvent] but a SequentialEvent we have
            # to add this hack).
            e.clock_event = clock_events.ClockEvent([e.clock_event])
        return e

    def convert(self, event_to_convert: core_events.abc.Event) -> core_events.abc.Event:
        return self._convert_event(event_to_convert, 0)


class ModalSequentialEventToEventPlacementTuple(core_converters.abc.Converter):
    @abc.abstractmethod
    def convert(
        self,
        modal_sequential_event_to_convert: core_events.SequentialEvent[
            clock_events.ModalEvent
        ],
    ) -> tuple[timeline_interfaces.EventPlacement, ...]:
        ...


class ModalSequentialEventToClockEvent(core_converters.abc.Converter):
    def convert(
        self,
        modal_sequential_event_to_convert: core_events.SequentialEvent[
            clock_events.ModalEvent
        ],
    ) -> clock_events.ClockEvent:
        clock_event_list = [
            modal_event.clock_event for modal_event in modal_sequential_event_to_convert
        ]

        if clock_event_list:
            clock_event = clock_event_list[0].copy()
            for successor in clock_event_list[1:]:
                try:
                    clock_event.concatenate_by_tag(successor)
                except core_utilities.NoTagError:
                    clock_event.concatenate_by_index(successor)

            return clock_event

        return core_events.ClockEvent()


class ModalSequentialEventToClockLine(core_converters.abc.Converter):
    def __init__(
        self,
        modal_sequential_event_to_event_placement_tuple_sequence: typing.Sequence[
            ModalSequentialEventToEventPlacementTuple
        ],
        modal_sequential_event_to_clock_event: ModalSequentialEventToClockEvent = ModalSequentialEventToClockEvent(),
    ):
        self._event_placement_maker_tuple = tuple(
            modal_sequential_event_to_event_placement_tuple_sequence
        )
        self._modal_sequential_event_to_clock_event = (
            modal_sequential_event_to_clock_event
        )

    def convert(
        self,
        modal_sequential_event_to_convert: core_events.SequentialEvent[
            clock_events.ModalEvent
        ],
    ) -> clock_interfaces.ClockLine:
        clock_event = self._modal_sequential_event_to_clock_event(
            modal_sequential_event_to_convert
        )
        event_placement_list = []
        for event_placement_maker in self._event_placement_maker_tuple:
            event_placement_list.extend(
                event_placement_maker.convert(modal_sequential_event_to_convert)
            )

        return clock_interfaces.ClockLine(clock_event, event_placement_list)
