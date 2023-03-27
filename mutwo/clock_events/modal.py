import typing

from mutwo import clock_events
from mutwo import core_events
from mutwo import core_parameters
from mutwo import music_parameters

__all__ = ("ModalEvent", "ModalEvent0", "ModalEvent1")


class ModalEvent(core_events.SimpleEvent):
    def __init__(
        self,
        scale: music_parameters.Scale,
        clock_event: typing.Optional[clock_events.ClockEvent] = None,
        control_event: typing.Optional[core_events.SimultaneousEvent] = None,
        energy: int = 0,
    ):
        self.scale = scale
        self.clock_event = clock_event
        self.control_event = control_event
        self.energy = energy
        super().__init__(0)  # Duration is defined by clock event duration!

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


class ModalEvent0(ModalEvent):
    def __init__(
        self,
        start_pitch: music_parameters.abc.Pitch,
        end_pitch: music_parameters.abc.Pitch,
        *args,
        **kwargs
    ):
        self.start_pitch = start_pitch
        self.end_pitch = end_pitch
        super().__init__(*args, **kwargs)


class ModalEvent1(ModalEvent):
    def __init__(self, pitch: music_parameters.abc.Pitch, *args, **kwargs):
        self.pitch = pitch
        super().__init__(*args, **kwargs)
