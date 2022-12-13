import typing

from mutwo import clock_generators
from mutwo import core_converters
from mutwo import core_events
from mutwo import core_parameters

__all__ = ("ClockTreeToEvent", "EventToSilencedEvent", "SplitEventBy", "SplitEventByTag")


class ClockTreeToEvent(core_converters.abc.Converter):
    def convert(
        self, clock_tree_to_convert: clock_generators.ClockTree, cycle_count: int = 1
    ) -> core_events.SequentialEvent:
        root_layer = clock_tree_to_convert.root.data
        sequential_event = core_events.SequentialEvent([])
        for _ in range(cycle_count):
            sequential_event.extend(root_layer.pop_event())
        return sequential_event


class EventToSilencedEvent(core_converters.abc.SymmetricalEventConverter):
    """Convert all events to rests where function returns ``True``.

    Helpful to extract only relevant events.
    This is particularly useful for clock trees, which often have plenty of different
    layers depending on their tags.
    """

    def __init__(
        self, force_event_to_rest: typing.Callable[[core_events.SimpleEvent], bool]
    ):
        self._force_event_to_rest = force_event_to_rest

    def _convert_simple_event(
        self,
        event_to_convert: core_events.SimpleEvent,
        absolute_entry_delay: typing.Union[core_parameters.abc.Duration, float, int],
        depth: int = 0,
    ) -> core_events.SimpleEvent:
        if self._force_event_to_rest(event_to_convert):
            return core_events.SimpleEvent(event_to_convert.duration)
        return event_to_convert.copy()

    def convert(self, event_to_convert):
        return self._convert_event(event_to_convert, core_parameters.DirectDuration(0))


class SplitEventBy(core_converters.abc.Converter):
    def __init__(self, event_to_silenced_event_tuple: tuple[EventToSilencedEvent, ...]):
        self._event_to_silenced_event_tuple = event_to_silenced_event_tuple

    def convert(self, event_to_convert) -> core_events.SimultaneousEvent:
        simultaneous_event = core_events.SimultaneousEvent([])
        for event_to_silenced_event in self._event_to_silenced_event_tuple:
            solo_layer = event_to_silenced_event.convert(event_to_convert)
            simultaneous_event.append(solo_layer)
        return simultaneous_event


class SplitEventByTag(SplitEventBy):
    def __init__(self, tag_tuple: tuple[str, ...]):
        event_to_silenced_event_list = []
        for tag in tag_tuple:
            event_to_silenced_event = EventToSilencedEvent(
                lambda event: getattr(event, "tag", None) not in (tag,)
            )
            event_to_silenced_event_convert = event_to_silenced_event.convert

            def _event_to_silenced_event_convert(self, event):
                converted_event = event_to_silenced_event_convert(event)
                converted_event.tag = tag
                return converted_event

            event_to_silenced_event.convert = _event_to_silenced_event_convert
            event_to_silenced_event_list.append(event_to_silenced_event)
        super().__init__(tuple(event_to_silenced_event_list))
