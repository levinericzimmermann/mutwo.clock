from __future__ import annotations
import dataclasses
import typing

from mutwo import core_parameters
from mutwo import clock_events
from mutwo import timeline_interfaces


__all__ = ("ClockLine", "Clock")


class ClockLine(timeline_interfaces.TimeLine):
    def __init__(self, clock_event: clock_events.ClockEvent, *args, **kwargs):
        self._clock_event = clock_event
        super().__init__(*args, **kwargs)

    @property
    def clock_event(self) -> clock_events.ClockEvent:
        return self._clock_event

    @property
    def duration(self) -> core_parameters.abc.Duration:
        return self.clock_event.duration


@dataclasses.dataclass(frozen=True)
class Clock(object):
    main_clock_line: ClockLine
    start_clock_line: typing.Optional[ClockLine] = None
    end_clock_line: typing.Optional[ClockLine] = None

    def __iter__(self) -> typing.Iterable[ClockLine | None]:
        return iter((self.start_clock_line, self.main_clock_line, self.end_clock_line))

    @property
    def clock_line_tuple(self) -> tuple[ClockLine, ClockLine, ClockLine]:
        return (self.start_clock_line, self.main_clock_line, self.end_clock_line)

    @property
    def duration(self) -> core_parameters.abc.Duration:
        return core_parameters.DirectDuration(
            sum(
                [
                    clock_line.duration.duration if clock_line is not None else 0
                    for clock_line in self.clock_line_tuple
                ]
            )
        )
