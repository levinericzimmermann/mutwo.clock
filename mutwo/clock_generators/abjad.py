import abjad

from mutwo import abjad_converters
from mutwo import core_events

__all__ = ("make_complex_event_to_abjad_container",)


def make_complex_event_to_abjad_container(
    nested_complex_event_to_abjad_container_kwargs={},
    sequential_event_to_abjad_staff_kwargs={},
    sequential_event_to_quantized_abjad_container_kwargs={},
    sequential_event_to_abjad_staff_class=None,
    sequential_event_to_quantized_abjad_container_class=abjad_converters.LeafMakerSequentialEventToDurationLineBasedQuantizedAbjadContainer,
):
    """Create standard abjad converter for clock lines.

    This function provides various parameters to adjust converter
    definition without rewriting everything.
    """
    class _SequentialEventToAbjadStaff(abjad_converters.SequentialEventToAbjadVoice):
        import abjad as _abjad

        def convert(self, *args, **kwargs) -> abjad.Staff:
            voice = super().convert(*args, **kwargs)
            voice._consists_commands = []
            first_leaf = self._abjad.select.leaves(voice)[0]
            self._abjad.attach(
                self._abjad.LilyPondLiteral(
                    r"\omit Stem \omit Flag "
                    r"\omit Beam \override NoteHead.duration-log = 2"
                ),
                first_leaf,
            )
            return self._abjad.Staff([voice])

    if sequential_event_to_abjad_staff_class is None:
        sequential_event_to_abjad_staff_class = _SequentialEventToAbjadStaff

    def event_to_time_signature_tuple(
        event: core_events.abc.Event,
    ) -> tuple[abjad.TimeSignature, ...]:
        return getattr(event, "time_signature_tuple", None)

    nested_complex_event_to_abjad_container_kwargs.setdefault(
        "abjad_container_class", abjad.StaffGroup
    )
    nested_complex_event_to_abjad_container_kwargs.setdefault(
        "lilypond_type_of_abjad_container", "StaffGroup"
    )

    # Default case: we don't print any tempo
    sequential_event_to_abjad_staff_kwargs.setdefault(
        "tempo_envelope_to_abjad_attachment_tempo", None
    )

    sequential_event_to_quantized_abjad_container_kwargs.setdefault(
        "event_to_time_signature_tuple", event_to_time_signature_tuple
    )

    return abjad_converters.NestedComplexEventToAbjadContainer(
        abjad_converters.CycleBasedNestedComplexEventToComplexEventToAbjadContainers(
            (
                sequential_event_to_abjad_staff_class(
                    sequential_event_to_quantized_abjad_container_class(
                        **sequential_event_to_quantized_abjad_container_kwargs
                    ),
                    **sequential_event_to_abjad_staff_kwargs
                ),
            )
        ),
        **nested_complex_event_to_abjad_container_kwargs
    )
