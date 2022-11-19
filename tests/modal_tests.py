import ranges
import pytest

from mutwo import clock_converters
from mutwo import clock_events
from mutwo import clock_generators
from mutwo import clock_interfaces
from mutwo import core_events
from mutwo import music_events
from mutwo import music_parameters
from mutwo import timeline_interfaces


class SimpleModalEventToClockTree(clock_converters.ModalEventToClockTree):
    def convert(self, _: clock_events.ModalEvent) -> clock_generators.ClockTree:
        clock_tree = clock_generators.ClockTree()
        clock_tree.create_layer(
            "root",
            None,
            # clock_generators.PickSampleByCycle((music_events.NoteLike("c", 1),)),
            clock_generators.PickSampleByCycle((music_events.NoteLike("1/1", 1),)),
            clock_generators.PickSampleByCycle(),
        )
        clock_tree.create_layer(
            "leaf",
            "root",
            # clock_generators.PickSampleByCycle((music_events.NoteLike("e", 0.25),)),
            clock_generators.PickSampleByCycle((music_events.NoteLike("5/4", 0.25),)),
            clock_generators.PickSampleByCycle(),
            event_count_range=ranges.Range(3, 4),
        )
        return clock_tree


class SimpleModalSequentialEventToEventPlacementTuple(
    clock_converters.ModalSequentialEventToEventPlacementTuple
):
    """Dummy converter which returns only one event placement"""

    def convert(
        self,
        modal_sequential_event_to_convert: core_events.SequentialEvent[
            clock_events.ModalEvent
        ],
    ) -> tuple[timeline_interfaces.EventPlacement, ...]:
        duration = modal_sequential_event_to_convert.duration
        return (
            timeline_interfaces.EventPlacement(
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSimultaneousEvent(
                            [
                                core_events.SequentialEvent(
                                    [music_events.NoteLike("1/4", 1)]
                                )
                            ],
                            tag="violin",
                        )
                    ]
                ),
                0,
                duration,
            ),
        )


@pytest.fixture
def scale():
    return music_parameters.Scale(
        # TODO(https://github.com/mutwo-org/mutwo.music/issues/1)
        # music_parameters.WesternPitch("c"),
        # music_parameters.RepeatingScaleFamily(
        #     [
        #         music_parameters.WesternPitchInterval(interval)
        #         for interval in "p1 m3 p4 p5 M7".split(" ")
        #     ],
        #     repetition_interval=music_parameters.WesternPitchInterval("p8"),
        # ),
        music_parameters.JustIntonationPitch("1/1"),
        music_parameters.RepeatingScaleFamily(
            [
                music_parameters.JustIntonationPitch(interval)
                for interval in "1/1 9/8 5/4 3/2 7/4".split(" ")
            ],
            repetition_interval=music_parameters.JustIntonationPitch("2/1"),
            min_pitch_interval=music_parameters.JustIntonationPitch("1/2"),
            max_pitch_interval=music_parameters.JustIntonationPitch("4/1"),
        ),
    )


@pytest.fixture
def modal_sequential_event(scale: music_parameters.Scale):
    scale_position_tuple = ((0, 0), (3, 0), (4, -1), (1, 0))
    return core_events.SequentialEvent(
        [
            clock_events.ModalEvent(
                scale.scale_position_to_pitch(scale_position0),
                scale.scale_position_to_pitch(scale_position1),
                scale,
            )
            for scale_position0, scale_position1 in zip(
                scale_position_tuple, scale_position_tuple[1:]
            )
        ]
    )


def _apply_clock_tree_on_modal_event(
    modal_sequential_event: core_events.SequentialEvent[clock_events.ModalEvent],
):
    return clock_converters.ApplyClockTreeOnModalEvent(
        SimpleModalEventToClockTree()
    ).convert(modal_sequential_event)


@pytest.fixture
def modal_sequential_event_with_clock_tree(
    modal_sequential_event: core_events.SequentialEvent[clock_events.ModalEvent],
):
    return _apply_clock_tree_on_modal_event(modal_sequential_event)


def test_apply_clock_tree_on_modal_event(
    modal_sequential_event: core_events.SequentialEvent[clock_events.ModalEvent],
):
    assert modal_sequential_event[0].clock_event is None
    assert modal_sequential_event[0].control_event is None

    modal_sequential_event = _apply_clock_tree_on_modal_event(modal_sequential_event)

    assert modal_sequential_event

    assert modal_sequential_event[0].clock_event is not None
    assert modal_sequential_event[0].control_event is not None

    assert isinstance(modal_sequential_event[0].clock_event, clock_events.ClockEvent)
    assert isinstance(
        modal_sequential_event[0].control_event, core_events.SimultaneousEvent
    )


def test_modal_sequential_event_to_clock_event(
    modal_sequential_event_with_clock_tree: core_events.SequentialEvent[
        clock_events.ModalEvent
    ],
):
    clock_event = clock_converters.ModalSequentialEventToClockEvent().convert(
        modal_sequential_event_with_clock_tree
    )
    assert clock_event

    assert clock_event[0][0].pitch_list == [music_parameters.JustIntonationPitch("1/1")]


def test_modal_sequential_event_to_event_placement_tuple(
    modal_sequential_event_with_clock_tree: core_events.SequentialEvent[
        clock_events.ModalEvent
    ],
):
    event_placement_tuple = SimpleModalSequentialEventToEventPlacementTuple().convert(
        modal_sequential_event_with_clock_tree
    )

    assert event_placement_tuple
    assert len(event_placement_tuple) == 1
    assert isinstance(event_placement_tuple[0], timeline_interfaces.EventPlacement)


def test_modal_sequential_event_to_clock_line(
    modal_sequential_event_with_clock_tree: core_events.SequentialEvent[
        clock_events.ModalEvent
    ],
):
    clock_line = clock_converters.ModalSequentialEventToClockLine(
        (SimpleModalSequentialEventToEventPlacementTuple(),)
    ).convert(modal_sequential_event_with_clock_tree)

    assert clock_line
    assert isinstance(clock_line, clock_interfaces.ClockLine)

    assert clock_line.clock_event
    assert isinstance(clock_line.clock_event, clock_events.ClockEvent)

    assert clock_line.event_placement_tuple
    assert len(clock_line.event_placement_tuple) == 1

    violin_event_placement = clock_line.get_event_placement("violin", 0)
    assert violin_event_placement
    assert violin_event_placement.event[0].tag == "violin"
