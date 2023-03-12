"""Make event placements from ModalSequentialEvent."""

import abc
import typing

from mutwo import clock_converters
from mutwo import clock_events
from mutwo import clock_interfaces
from mutwo import clock_generators
from mutwo import clock_parameters  # monkeypatch
from mutwo import core_converters
from mutwo import core_events
from mutwo import core_parameters
from mutwo import core_utilities
from mutwo import timeline_interfaces

__all__ = (
    "ModalEvent0ToClockTree",
    "ApplyClockTreeOnModalEvent0",
    "Modal0SequentialEventToEventPlacementTuple",
    "Modal1SequentialEventToEventPlacementTuple",
    "Modal0SequentialEventToClockLine",
    "Modal0SequentialEventToClockEvent",
    "Modal0SequentialEventToModal1SequentialEvent",
)

Modal0SequentialEvent: typing.TypeAlias = core_events.SequentialEvent[
    clock_events.ModalEvent0 | core_events.SimpleEvent
]

Modal1SequentialEvent: typing.TypeAlias = core_events.SequentialEvent[
    clock_events.ModalEvent1 | core_events.SimpleEvent
]


class ModalEvent0ToClockTree(core_converters.abc.Converter):
    @abc.abstractmethod
    def convert(
        self, modal_event_0_to_convert: clock_events.ModalEvent0
    ) -> clock_generators.ClockTree:
        ...


class ApplyClockTreeOnModalEvent0(core_converters.abc.SymmetricalEventConverter):
    def __init__(
        self,
        modal_event_0_to_clock_tree: ModalEvent0ToClockTree,
    ):
        self._modal_event_0_to_clock_tree = modal_event_0_to_clock_tree

    def _convert_simple_event(
        self,
        event_to_convert: core_events.SimpleEvent,
        absolute_entry_delay: core_parameters.abc.Duration | float | int,
        depth: int = 0,
    ) -> core_events.SimpleEvent:
        e = event_to_convert.copy()
        if isinstance(e, clock_events.ModalEvent):
            clock_tree = self._modal_event_0_to_clock_tree.convert(event_to_convert)
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


class Modal0SequentialEventToEventPlacementTuple(core_converters.abc.Converter):
    @abc.abstractmethod
    def convert(
        self,
        modal_0_sequential_event_to_convert: Modal0SequentialEvent,
    ) -> tuple[timeline_interfaces.EventPlacement, ...]:
        ...


class Modal1SequentialEventToEventPlacementTuple(core_converters.abc.Converter):
    @abc.abstractmethod
    def convert(
        self,
        modal_1_sequential_event_to_convert: Modal1SequentialEvent,
    ) -> tuple[timeline_interfaces.EventPlacement, ...]:
        ...


class Modal0SequentialEventToClockEvent(core_converters.abc.Converter):
    """Create ClockEvent from Modal0SequentialEvent"""

    def convert(
        self,
        modal_0_sequential_event_to_convert: Modal0SequentialEvent,
    ) -> clock_events.ClockEvent:
        clock_event_list = []
        for modal_event_0 in modal_0_sequential_event_to_convert:
            try:
                clock_event = modal_event_0.clock_event
            except AttributeError:
                clock_event = clock_events.ClockEvent()
                if (modal_event_duration := modal_event_0.duration) > 0:
                    clock_event.append(
                        core_events.SequentialEvent(
                            [core_events.SimpleEvent(modal_event_duration)]
                        )
                    )
            clock_event_list.append(clock_event)

        if clock_event_list:
            clock_event = clock_event_list[0].copy()
            for successor in clock_event_list[1:]:
                try:
                    clock_event.concatenate_by_tag(successor)
                except core_utilities.NoTagError:
                    clock_event.concatenate_by_index(successor)

            return clock_event

        return core_events.ClockEvent()


class Modal0SequentialEventToClockLine(core_converters.abc.Converter):
    def __init__(
        self,
        modal_0_sequential_event_to_event_placement_tuple_sequence: typing.Sequence[
            Modal0SequentialEventToEventPlacementTuple
        ],
        modal_1_sequential_event_to_event_placement_tuple_sequence: typing.Sequence[
            Modal1SequentialEventToEventPlacementTuple
        ] = [],
        modal_0_sequential_event_to_clock_event: Modal0SequentialEventToClockEvent = Modal0SequentialEventToClockEvent(),
    ):
        self._maker_tuple_0 = tuple(
            modal_0_sequential_event_to_event_placement_tuple_sequence
        )
        self._maker_tuple_1 = tuple(
            modal_1_sequential_event_to_event_placement_tuple_sequence
        )
        self._modal_0_sequential_event_to_clock_event = (
            modal_0_sequential_event_to_clock_event
        )

        self._m0seq_to_m1seq = Modal0SequentialEventToModal1SequentialEvent()

    def convert(
        self,
        modal_0_sequential_event_to_convert: Modal0SequentialEvent,
    ) -> clock_interfaces.ClockLine:
        m0seq = modal_0_sequential_event_to_convert

        # Only make expensive split in case we do have modal1 maker!
        if self._maker_tuple_1:
            m1seq = self._m0seq_to_m1seq(m0seq)
        else:
            m1seq = []

        event_placement_list = []
        for modal_sequential_event, event_placement_maker_tuple in (
            (m0seq, self._maker_tuple_0),
            (m1seq, self._maker_tuple_1),
        ):
            for event_placement_maker in event_placement_maker_tuple:
                event_placement_list.extend(
                    event_placement_maker.convert(modal_sequential_event)
                )

        clock_event = self._modal_0_sequential_event_to_clock_event(m0seq)
        return clock_interfaces.ClockLine(clock_event, event_placement_list)


# TODO(Improve logic, make code less verbose)
class Modal0SequentialEventToModal1SequentialEvent(core_converters.abc.Converter):
    def convert(
        self, modal_0_sequential_event_to_convert: Modal0SequentialEvent
    ) -> Modal1SequentialEvent:
        m0seq = modal_0_sequential_event_to_convert
        m1seq = core_events.SequentialEvent([])

        clock_event_list, control_event_list = self._m0seq_to_event_lists(m0seq)

        if m0seq:
            if isinstance(m0seq[0], clock_events.ModalEvent0):
                m1seq.append(
                    clock_events.ModalEvent1(
                        scale=m0seq[0].scale,
                        pitch=m0seq[0].start_pitch,
                        control_event=control_event_list[0],
                        clock_event=clock_event_list[0],
                    )
                )
            else:
                m1seq.append(core_events.SimpleEvent(m0seq[0].duration / 2))

        for m0_ev_A, m0_ev_B, clock_event, control_event in zip(
            m0seq, m0seq[1:], clock_event_list[1:], control_event_list[1:]
        ):
            if type(clock_event) is tuple:  # One of modal events is a rest
                clock_p0, clock_p1 = clock_event
                control_p0, control_p1 = control_event
                if clock_p0 is None and clock_p1 is None:
                    m1seq.append(
                        core_events.SimpleEvent(
                            (m0_ev_A.duration / 2) + (m0_ev_B.duration / 2)
                        )
                    )
                elif clock_p0 is None:
                    m1seq.extend(
                        (
                            core_events.SimpleEvent(m0_ev_A.duration / 2),
                            clock_events.ModalEvent1(
                                pitch=m0_ev_B.start_pitch,
                                clock_event=clock_p1,
                                control_event=control_p1,
                                scale=m0_ev_B.scale,
                            ),
                        )
                    )

                elif clock_p1 is None:
                    m1seq.extend(
                        (
                            clock_events.ModalEvent1(
                                pitch=m0_ev_A.end_pitch,
                                clock_event=clock_p0,
                                control_event=control_p0,
                                scale=m0_ev_A.scale,
                            ),
                            core_events.SimpleEvent(m0_ev_B.duration / 2),
                        )
                    )
                else:
                    raise NotImplementedError()
            else:
                modal_event_1 = clock_events.ModalEvent1(
                    pitch=m0_ev_A.end_pitch,
                    clock_event=clock_event,
                    control_event=control_event,
                    scale=m0_ev_A.scale.intersection(m0_ev_B.scale)
                    if hasattr(m0_ev_B, "scale")
                    else m0_ev_A.scale,
                )
                m1seq.append(modal_event_1)

        if m0seq:
            if isinstance(m0seq[-1], clock_events.ModalEvent0):
                m1seq.append(
                    clock_events.ModalEvent1(
                        scale=m0seq[-1].scale,
                        pitch=m0seq[-1].end_pitch,
                        control_event=control_event_list[-1],
                        clock_event=clock_event_list[-1],
                    )
                )
            else:
                m1seq.append(core_events.SimpleEvent(m0seq[-1].duration / 2))

        return m1seq

    @staticmethod
    def _m0seq_to_event_lists(m0seq):
        clock_event_part_list, control_event_part_list = [], []
        for m0_ev in m0seq:
            if not hasattr(m0_ev, "clock_event"):
                clock_event_part_list.append(None)
                control_event_part_list.append(None)
                continue
            for ev, l in (
                (m0_ev.clock_event, clock_event_part_list),
                (m0_ev.control_event, control_event_part_list),
            ):
                l.extend(ev.split_at(ev.duration / 2))

        clock_event_list, control_event_list = [], []
        for part_list, list_ in (
            (clock_event_part_list, clock_event_list),
            (control_event_part_list, control_event_list),
        ):
            list_.append(part_list[0])  # Special case: only start_pitch
            for p0, p1 in zip(part_list[1::2], part_list[2:-1:2]):
                if p0 is None and p1 is None:
                    list_.append((None, None))
                elif p0 is None:
                    list_.append((None, p1))
                elif p1 is None:
                    list_.append((p0, None))
                else:
                    list_.append(p0.concatenate_by_index(p1))
            list_.append(part_list[-1])  # Special case: only end_pitch

        return clock_event_list, control_event_list
