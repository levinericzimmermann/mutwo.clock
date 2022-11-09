from mutwo import core_converters
from mutwo import core_events
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

    # TODO(Should be moved to an external converter, because it's generally
    # useful. Perhaps it could even move to somewhere like `mutwo.core`
    # or `mutwo.music`. It is generally helpful when one wants to concatenate
    # two simultaneous events based on tags.
    # This methods is also in some parts very similar to what happens in
    # timeline_converters.TimeLineToSimultaneousEvent.)
    def _extend_simultaneous_event(
        self,
        simultaneous_event_to_extend: core_events.SimultaneousEvent,
        clock_line: clock_interfaces.ClockLine,
    ):
        new_simultaneous_event = self._clock_line_to_simultaneous_event.convert(
            clock_line
        )
        tag_to_event_index = {
            event.tag: index for index, event in enumerate(simultaneous_event_to_extend)
        }
        simultaneous_event_to_extend_duration = simultaneous_event_to_extend.duration
        for simultaneous_event_to_add in new_simultaneous_event:
            assert isinstance(
                simultaneous_event_to_add, core_events.SimultaneousEvent
            ), "Unexpected event '{simultaneous_event_to_add}'!"
            tag = simultaneous_event_to_add.tag
            try:
                tagged_simultaneous_event_to_extend = simultaneous_event_to_extend[
                    tag_to_event_index[tag]
                ]
            except KeyError:
                if simultaneous_event_to_extend_duration > 0:
                    for sequential_event in simultaneous_event_to_add:
                        assert isinstance(
                            sequential_event, core_events.SequentialEvent
                        ), "Unexpected event '{sequential_event}'!"
                        sequential_event.insert(
                            0,
                            core_events.SimpleEvent(
                                simultaneous_event_to_extend_duration
                            ),
                        )
                simultaneous_event_to_extend.append(simultaneous_event_to_add)
            else:
                sequential_event_to_add_count = len(simultaneous_event_to_add) - len(
                    tagged_simultaneous_event_to_extend
                )
                for _ in range(sequential_event_to_add_count):
                    tagged_simultaneous_event_to_extend.append(
                        core_events.SequentialEvent([])
                    )
                for sequential_event_to_append_to, sequential_event_to_append in zip(
                    tagged_simultaneous_event_to_extend, new_simultaneous_event
                ):
                    difference = (
                        simultaneous_event_to_extend_duration
                        - sequential_event_to_append_to.duration
                    )
                    if difference > 0:
                        sequential_event_to_append_to.append(
                            core_events.SimpleEvent(difference)
                        )
                    sequential_event_to_append_to.extend(sequential_event_to_append)

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
                    self._extend_simultaneous_event(simultaneous_event, clock_line)
        return simultaneous_event
