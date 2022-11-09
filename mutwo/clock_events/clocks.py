import typing

from mutwo import core_events
from mutwo import clock_events

__all__ = ("ClockEvent",)


class ClockEvent(core_events.TaggedSimultaneousEvent):
    def __init__(self, *args, tag: typing.Optional[str] = None, **kwargs):
        if tag is None:
            tag = clock_events.configurations.DEFAULT_CLOCK_TAG
        super().__init__(*args, tag=tag, **kwargs)
