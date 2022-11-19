import typing

from mutwo import clock_events
from mutwo import core_events
from mutwo import core_parameters
from mutwo import music_parameters

__all__ = ("ModalEvent",)


class ModalEvent(core_events.SimpleEvent):
    def __init__(
        self,
        start_pitch: music_parameters.abc.Pitch,
        end_pitch: music_parameters.abc.Pitch,
        scale: music_parameters.Scale,
        clock_event: typing.Optional[clock_events.ClockEvent] = None,
        control_event: typing.Optional[core_events.SimultaneousEvent] = None,
    ):
        self.start_pitch = start_pitch
        self.end_pitch = end_pitch
        self.scale = scale
        self.clock_event = clock_event
        self.control_event = control_event
        super().__init__(0)

    @property
    def duration(self):
        try:
            return self.clock_event.duration
        except AttributeError:
            return 0

    @duration.setter
    def duration(self, duration: core_parameters.abc.Duration):
        duration = core_events.configurations.UNKNOWN_OBJECT_TO_DURATION(duration)
        if duration > 0:
            try:
                self.clock_event.duration = duration
            except AttributeError:
                pass
