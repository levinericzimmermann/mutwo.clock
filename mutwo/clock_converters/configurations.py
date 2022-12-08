import abjad

from mutwo import abjad_converters
from mutwo import core_converters
from mutwo import core_events


def _event_to_time_signature_tuple(
    event: core_events.abc.Event,
) -> tuple[abjad.TimeSignature, ...]:
    return getattr(event, "time_signature_tuple", None)


class _SequentialEventToAbjadStaff(abjad_converters.SequentialEventToAbjadVoice):
    import abjad as _abjad

    def convert(self, *args, **kwargs) -> abjad.Staff:
        voice = super().convert(*args, **kwargs)
        voice._consists_commands = []
        first_leaf = self._abjad.select.leaves(voice)[0]
        self._abjad.attach(
            self._abjad.LilyPondLiteral(
                r"\omit Stem \omit Flag"
                r"\omit Beam \override NoteHead.duration-log = 2"
            ),
            first_leaf,
        )
        return self._abjad.Staff([voice])


DEFAULT_COMPLEX_EVENT_TO_ABJAD_CONTAINER = (
    abjad_converters.NestedComplexEventToAbjadContainer(
        abjad_converters.CycleBasedNestedComplexEventToComplexEventToAbjadContainers(
            (
                _SequentialEventToAbjadStaff(
                    abjad_converters.LeafMakerSequentialEventToDurationLineBasedQuantizedAbjadContainer(
                        event_to_time_signature_tuple=_event_to_time_signature_tuple
                    ),
                    # Default case: we don't print any tempo
                    tempo_envelope_to_abjad_attachment_tempo=None,
                ),
            )
        ),
        abjad_container_class=abjad.StaffGroup,
        lilypond_type_of_abjad_container="StaffGroup",
    )
)

del abjad, abjad_converters, core_events, core_converters, _SequentialEventToAbjadStaff
