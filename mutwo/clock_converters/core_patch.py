import typing

from mutwo import core_events
from mutwo import core_parameters
from mutwo import core_utilities


class NoTagError(Exception):
    ...


def patch_simultaneous_event():
    @core_utilities.add_copy_option
    def extend_until(
        self, duration: typing.Optional[core_parameters.abc.Duration] = None
    ):
        if duration is None:
            duration = self.duration
        else:
            duration = core_events.configurations.UNKNOWN_OBJECT_TO_DURATION(duration)

        for event in self:
            event.extend_until(duration)

        # TODO(Remove when tests are available)
        assert self.duration == duration

    @core_utilities.add_copy_option
    def concatenate_by_index(self, other: core_events.SimultaneousEvent):
        self_duration = self.duration
        for index, event in enumerate(other.extend_until(mutate=False)):
            try:
                ancestor = self[index]
            except IndexError:
                event.squash_in(0, core_events.SimpleEvent(self_duration))
                self.append(event)
            else:
                match ancestor:
                    case core_events.SequentialEvent():
                        ancestor.extend(event)
                    case core_events.SimultaneousEvent():
                        try:
                            ancestor.concatenate_by_tag(event)
                        except NoTagError:
                            ancestor.concatenate_by_index(event)
                    case _:
                        raise

        self.extend_until()

    @core_utilities.add_copy_option
    def concatenate_by_tag(
        self, other: core_events.SimultaneousEvent
    ) -> core_events.SimultaneousEvent:
        self_duration = self.duration
        for tagged_event in other.extend_until(mutate=False):
            if not hasattr(tagged_event, "tag"):
                raise NoTagError("Can only concatenate tagged events!")
            tag = tagged_event.tag
            try:
                ancestor = self[tag]
            except KeyError:
                tagged_event.squash_in(0, core_events.SimpleEvent(self_duration))
                self.append(tagged_event)
            else:
                match ancestor:
                    case core_events.SequentialEvent():
                        ancestor.extend(tagged_event)
                    case core_events.SimultaneousEvent():
                        try:
                            ancestor.concatenate_by_tag(tagged_event)
                        except NoTagError:
                            ancestor.concatenate_by_index(tagged_event)
                    case _:
                        raise

        self.extend_until()

    core_events.SimultaneousEvent.extend_until = extend_until
    core_events.SimultaneousEvent.concatenate_by_tag = concatenate_by_tag
    core_events.SimultaneousEvent.concatenate_by_index = concatenate_by_index


def patch_sequential_event():
    @core_utilities.add_copy_option
    def extend_until(
        self, duration: typing.Optional[core_parameters.abc.Duration] = None
    ):
        if duration is None:
            duration = self.duration
        else:
            duration = core_events.configurations.UNKNOWN_OBJECT_TO_DURATION(duration)

        difference = duration - self.duration
        if difference > 0:
            self.append(core_events.SimpleEvent(difference))

        # TODO(Remove when tests are available)
        assert self.duration == duration

    core_events.SequentialEvent.extend_until = extend_until


def patch_simple_event():
    @core_utilities.add_copy_option
    def extend_until(
        self, duration: typing.Optional[core_parameters.abc.Duration] = None
    ):
        if duration is None:
            duration = self.duration
        else:
            duration = core_events.configurations.UNKNOWN_OBJECT_TO_DURATION(duration)

        difference = duration - self.duration
        if difference > 0:
            self.duration += difference

        # TODO(Remove when tests are available)
        assert self.duration == duration

    core_events.SimpleEvent.extend_until = extend_until


patch_simultaneous_event()
patch_sequential_event()
patch_simple_event()
