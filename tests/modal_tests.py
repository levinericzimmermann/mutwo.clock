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


class SimpleModalEvent0ToClockTree(clock_converters.ModalEvent0ToClockTree):
    def convert(self, _: clock_events.ModalEvent0) -> clock_generators.ClockTree:
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


class SimpleModal0SequentialEventToEventPlacementTuple(
    clock_converters.Modal0SequentialEventToEventPlacementTuple
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
        music_parameters.WesternPitch("c"),
        music_parameters.RepeatingScaleFamily(
            [
                music_parameters.WesternPitchInterval(interval)
                for interval in "p1 m3 p4 p5 M7".split(" ")
            ],
            repetition_interval=music_parameters.WesternPitchInterval("p8"),
        ),
    )


@pytest.fixture(params=[{"rest": False}, {"rest": True}])
def modal_sequential_event(scale: music_parameters.Scale, request):
    scale_position_tuple = ((0, 0), (3, 0), (4, -1), (1, 0))
    sequential_event = core_events.SequentialEvent(
        [
            clock_events.ModalEvent0(
                scale.scale_position_to_pitch(scale_position0),
                scale.scale_position_to_pitch(scale_position1),
                scale,
            )
            for scale_position0, scale_position1 in zip(
                scale_position_tuple, scale_position_tuple[1:]
            )
        ]
    )
    if request.param["rest"]:
        for _ in range(2):
            sequential_event.insert(1, core_events.SimpleEvent(3))
        sequential_event.append(core_events.SimpleEvent(4))
    return sequential_event


def _apply_clock_tree_on_modal_event(
    modal_sequential_event: core_events.SequentialEvent[clock_events.ModalEvent0],
):
    return clock_converters.ApplyClockTreeOnModalEvent0(
        SimpleModalEvent0ToClockTree()
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
    clock_event = clock_converters.Modal0SequentialEventToClockEvent().convert(
        modal_sequential_event_with_clock_tree
    )
    assert clock_event
    assert clock_event[0][0].pitch_list == [music_parameters.JustIntonationPitch("1/1")]
    assert clock_event.duration == modal_sequential_event_with_clock_tree.duration


def test_modal_sequential_event_to_event_placement_tuple(
    modal_sequential_event_with_clock_tree: core_events.SequentialEvent[
        clock_events.ModalEvent
    ],
):
    event_placement_tuple = SimpleModal0SequentialEventToEventPlacementTuple().convert(
        modal_sequential_event_with_clock_tree
    )

    assert event_placement_tuple
    assert len(event_placement_tuple) == 1
    assert isinstance(event_placement_tuple[0], timeline_interfaces.EventPlacement)


def test_modal_sequential_event_to_clock_line(
    modal_sequential_event_with_clock_tree: core_events.SequentialEvent[
        clock_events.ModalEvent0
    ],
):
    clock_line = clock_converters.Modal0SequentialEventToClockLine(
        (SimpleModal0SequentialEventToEventPlacementTuple(),)
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


def test_Modal0SequentialEventToModal1SequentialEventTest(
    # Schwierig das so zu testen, weil es ein event mit pausen gibt und
    # eins ohne pausen..
    modal_sequential_event_with_clock_tree: core_events.SequentialEvent[
        clock_events.ModalEvent0
    ],
):
    pass
