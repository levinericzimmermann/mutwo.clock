import abjad
import ranges

from mutwo import abjad_converters
from mutwo import core_events

__all__ = ("make_complex_event_to_abjad_container",)


def make_complex_event_to_abjad_container(
    nested_complex_event_to_abjad_container_kwargs={},
    sequential_event_to_abjad_staff_kwargs={},
    sequential_event_to_quantized_abjad_container_kwargs={},
    sequential_event_to_abjad_staff_class=None,
    sequential_event_to_quantized_abjad_container_class=abjad_converters.LeafMakerSequentialEventToDurationLineBasedQuantizedAbjadContainer,
    duration_line: bool = False,
):
    """Create standard abjad converter for clock lines.

    This function provides various parameters to adjust converter
    definition without rewriting everything.
    """

    from mutwo import clock_converters

    class AddRepetition(abjad_converters.ProcessAbjadContainerRoutine):
        def __call__(
            self,
            complex_event_to_convert: core_events.abc.ComplexEvent,
            container_to_process: abjad.Container,
        ):
            # why don't we get the outer simultaneous event, but an inner one?
            repetition_count_range = getattr(
                complex_event_to_convert, "repetition_count_range", ranges.Range(1, 2)
            )
            if repetition_count_range.end > 2:
                leaves = abjad.select.leaves(container_to_process)
                first_leaf = leaves[0]
                last_leaf = leaves[-1]
                abjad.attach(
                    abjad.LilyPondLiteral(
                        "{}{}".format(
                            clock_converters.show_barline(),
                            clock_converters.override_barline(".|:"),
                        ),
                        site="before",
                    ),
                    first_leaf,
                )
                abjad.attach(
                    abjad.LilyPondLiteral(
                        "{}{}".format(
                            clock_converters.show_barline(),
                            clock_converters.override_barline(":|."),
                        ),
                        site="after",
                    ),
                    last_leaf,
                )

    class _SequentialEventToAbjadStaff(abjad_converters.SequentialEventToAbjadVoice):
        import abjad as _abjad

        def convert(self, *args, **kwargs) -> abjad.Staff:
            voice = super().convert(*args, **kwargs)
            if not duration_line:
                voice._consists_commands = []
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
    nested_complex_event_to_abjad_container_kwargs.setdefault(
        "post_process_abjad_container_routine_sequence", [AddRepetition()]
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
