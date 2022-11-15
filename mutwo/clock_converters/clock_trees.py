from mutwo import clock_generators
from mutwo import core_events
from mutwo import core_converters

__all__ = ("ClockTreeToEvent",)


class ClockTreeToEvent(core_converters.abc.Converter):
    def convert(
        self, clock_tree_to_convert: clock_generators.ClockTree, cycle_count: int = 1
    ) -> core_events.SequentialEvent:
        root_layer = clock_tree_to_convert.root.data
        sequential_event = core_events.SequentialEvent([])
        for _ in range(cycle_count):
            sequential_event.extend(root_layer.pop_event())
        return sequential_event
