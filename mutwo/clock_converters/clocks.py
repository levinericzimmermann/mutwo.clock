from mutwo import core_converters
from mutwo import core_events
from mutwo import core_utilities
from mutwo import clock_interfaces
from mutwo import timeline_converters


__all__ = (
    "ClockLineToSimultaneousEvent",
    "ClockToSimultaneousEvent",
)


class ClockLineToSimultaneousEvent(timeline_converters.TimeLineToSimultaneousEvent):
    def convert(
        self, clock_line_to_convert: clock_interfaces.ClockLine
    ) -> core_events.SimultaneousEvent:
        simultaneous_event = super().convert(clock_line_to_convert)
        simultaneous_event.insert(0, clock_line_to_convert.clock_event.copy())
        return simultaneous_event


class ClockToSimultaneousEvent(core_converters.abc.Converter):
    def __init__(
        self,
        clock_line_to_simultaneous_event: ClockLineToSimultaneousEvent = ClockLineToSimultaneousEvent(),
    ):
        self._clock_line_to_simultaneous_event = clock_line_to_simultaneous_event

    def convert(
        self, clock_to_convert: clock_interfaces.Clock, repetition_count: int = 1
    ) -> core_events.SimultaneousEvent:
        simultaneous_event = core_events.SimultaneousEvent()
        for repetition_count, clock_line in (
            (1, clock_to_convert.start_clock_line),
            (repetition_count, clock_to_convert.main_clock_line),
            (1, clock_to_convert.end_clock_line),
        ):
            if clock_line is not None:
                for _ in range(repetition_count):
                    new_simultaneous_event = (
                        self._clock_line_to_simultaneous_event.convert(clock_line)
                    )
                    try:
                        simultaneous_event.concatenate_by_tag(new_simultaneous_event)
                    except core_utilities.NoTagError:
                        simultaneous_event.concatenate_by_index(new_simultaneous_event)
        return simultaneous_event
