import dataclasses
import functools

import ranges
import pytest

from mutwo import clock_converters
from mutwo import clock_events
from mutwo import clock_generators
from mutwo import core_events
from mutwo import core_parameters
from mutwo import music_events

d = core_parameters.DirectDuration

tSymT_A = clock_generators.SymT("A")
tSymT_A0 = clock_generators.SymT("A", ranges.Range(d(4), d(8)))
tSymT_A1 = clock_generators.SymT("A", ranges.Range(d(6), d(10)))

tSymT_B = clock_generators.SymT("B")
tSymT_B0 = tSymT_B


@dataclasses.dataclass
class t:
    note_like: music_events.NoteLike

    @functools.cached_property
    def duration_range(self) -> ranges.Range:
        return ranges.Range(self.note_like.duration, self.note_like.duration)

    def __call__(self):
        return clock_events.ClockEvent(
            [core_events.TaggedSequentialEvent([self.note_like], tag="0")]
        )

    def __hash__(self):
        return hash(self.note_like.duration.duration)


t0 = t(music_events.NoteLike("c", 1))
t1 = t(music_events.NoteLike("d", 2))
t2 = t(music_events.NoteLike("e", 3))


context_free_grammar = clock_generators.ContextFreeGrammar(
    (
        # Symbolic
        clock_generators.R(
            tSymT_A,
            (clock_generators.NT(t0),),
            weight=1,
        ),
        clock_generators.R(
            tSymT_B,
            (clock_generators.NT(t1),),
            weight=1,
        ),
        clock_generators.R(
            tSymT_B,
            (clock_generators.NT(t2),),
            weight=1,
        ),
        # Real
        clock_generators.R(
            clock_generators.NT(t0),
            (clock_generators.NT(t0), clock_generators.NT(t1)),
            weight=1,
        ),
        clock_generators.R(
            clock_generators.NT(t0),
            (clock_generators.NT(t0), clock_generators.NT(t2)),
            weight=0.5,
        ),
        clock_generators.R(
            clock_generators.NT(t1),
            (clock_generators.NT(t1), clock_generators.NT(t1)),
            weight=0.6,
        ),
        clock_generators.R(
            clock_generators.NT(t1),
            (clock_generators.NT(t1), clock_generators.NT(t2)),
            weight=0.6,
        ),
        clock_generators.R(
            clock_generators.NT(t2),
            (clock_generators.NT(t0), clock_generators.NT(t2), clock_generators.NT(t1)),
        ),
    )
)


def test_resolve():
    resolution = context_free_grammar.resolve(tSymT_A, limit=3)
    assert resolution
    assert resolution.leaves()
    assert resolution.nodes


def test_SymTSequenceToClockEventTuple():
    c = clock_converters.SymTSequenceToClockEventTuple(context_free_grammar)
    clock_event_tuple = c.convert((tSymT_A0, tSymT_A1, tSymT_B0))
    assert clock_event_tuple
    assert len(clock_event_tuple) == 3
