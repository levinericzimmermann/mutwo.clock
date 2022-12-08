"""Build western notation from :class:`mutwo.clock_interfaces.Clock` and friends.

See abjad_notes.txt for more information regarding internal structure.
"""

import typing
import warnings

import abjad
import quicktions as fractions

from mutwo import abjad_converters
from mutwo import clock_converters
from mutwo import clock_events
from mutwo import clock_interfaces
from mutwo import clock_utilities
from mutwo import core_converters
from mutwo import core_events
from mutwo import core_parameters
from mutwo import timeline_converters
from mutwo import timeline_interfaces

__all__ = (
    "EventPlacementToAbjadStaffGroup",
    "ClockEventToAbjadStaffGroup",
    "ClockToAbjadScore",
    "AbjadScoreToAbjadScoreBlock",
    "AbjadScoreBlockTupleToLilyPondFile",
)

Tag: typing.TypeAlias = "str"
TagToAbjadStaffGroup: typing.TypeAlias = "dict[Tag, abjad.StaffGroup]"

# TODO(Explicitly add repetition bar lines)
# TODO(Add indicators for start and end ranges!)
# TODO(Add instrument names before each appearing event placement.)


class EventPlacementToAbjadStaffGroup(core_converters.abc.Converter):
    """Converts each tagged event into one :class:`abjad.StaffGroup`

    So each instrument has its own `abjad.StaffGroup`.
    """

    def __init__(
        self,
        complex_event_to_abjad_container: typing.Optional[
            abjad_converters.ComplexEventToAbjadContainer
        ] = None,
        staff_count: int = 1,
    ):

        if complex_event_to_abjad_container is None:
            complex_event_to_abjad_container = (
                clock_converters.configurations.DEFAULT_COMPLEX_EVENT_TO_ABJAD_CONTAINER
            )
        self._complex_event_to_abjad_container = complex_event_to_abjad_container
        self._staff_count = staff_count

    def _convert_rest(
        self,
        tag: str,
        written_duration: fractions.Fraction,
        scale_durations: str,
    ) -> abjad.StaffGroup:
        staff_group = abjad.StaffGroup([], name=tag)
        for abjad_staff_index in range(self._staff_count):
            skip = abjad.Skip(written_duration)
            abjad.attach(
                abjad.LilyPondLiteral(
                    r"\override Score.BarNumber.break-visibility = #all-invisible"
                    "\n"
                    r"\omit Staff.BarLine \omit StaffGroup.BarLine "
                    r"\omit Staff.Clef "
                    r"\omit Staff.TimeSignature \stopStaff "
                    f"{scale_durations}",
                    site="before",
                ),
                skip,
            )
            staff = abjad.Staff(
                [skip], name=self._get_abjad_staff_name(tag, abjad_staff_index)
            )
            staff_group.append(staff)
        return staff_group

    def _get_abjad_staff_name(self, tag: str, index: int) -> str:
        return f"staff-{tag}-{index}"

    def _convert_event(
        self,
        scale_durations: str,
        event_to_convert: core_events.TaggedSimultaneousEvent,
    ):
        event_duration = event_to_convert.duration.duration
        time_signature = abjad.TimeSignature(
            (event_duration.numerator, event_duration.denominator)
        )
        time_signature_tuple = (time_signature, time_signature)
        for sequential_event in event_to_convert:
            sequential_event.time_signature_tuple = time_signature_tuple

        abjad_staff_group = self._complex_event_to_abjad_container.convert(
            event_to_convert
        )
        tag = event_to_convert.tag
        for abjad_staff_index, abjad_staff in enumerate(abjad_staff_group):
            abjad_staff.name = self._get_abjad_staff_name(tag, abjad_staff_index)
            for abjad_voice_index, abjad_voice in enumerate(abjad_staff):
                abjad_voice.name = f"{abjad_staff.name}-{abjad_voice_index}"
                leaf_selection = abjad.select.leaves(abjad_voice)
                first_leaf = leaf_selection[0]
                abjad.attach(
                    abjad.LilyPondLiteral(
                        "\n".join(
                            (
                                r"\startStaff",
                                r"\override Score.BarNumber.break-visibility = #all-invisible",
                                r"\undo \omit Staff.Clef",
                                r"\omit Staff.BarLine",
                                r"\override Staff.BarLine.allow-span-bar = ##f",
                                r"\override Staff.Clef.break-visibility = #all-invisible",
                                r"\override Staff.ClefModifier.break-visibility = #all-invisible",
                                r"\omit Staff.TimeSignature",
                                r"\set Staff.forceClef = ##t",
                            )
                        ),
                        site="absolute_before",
                    ),
                    first_leaf,
                )
                for leaf in leaf_selection:
                    abjad.attach(
                        abjad.LilyPondLiteral(f"{scale_durations} {{", site="before"),
                        leaf,
                    )
                    abjad.attach(abjad.LilyPondLiteral("}", site="after"), leaf)
        return abjad_staff_group

    def convert(
        self,
        event_placement_to_convert: timeline_interfaces.EventPlacement,
    ) -> abjad.StaffGroup:
        simultaneous_event = event_placement_to_convert.event
        real_duration = event_placement_to_convert.duration.duration
        written_duration = simultaneous_event.duration.duration

        if is_rest := (written_duration == 0):
            written_duration = 1

        ratio = real_duration / written_duration

        scale_durations = rf"\scaleDurations {ratio.numerator}/{ratio.denominator}"

        if is_rest:
            tag, *_ = event_placement_to_convert.tag_tuple
            return self._convert_rest(tag, written_duration, scale_durations)
        return self._convert_event(scale_durations, simultaneous_event[0])


class ClockEventToAbjadStaffGroup(core_converters.abc.Converter):
    def __init__(
        self,
        complex_event_to_abjad_container: typing.Optional[
            abjad_converters.ComplexEventToAbjadContainer
        ] = None,
    ):
        if complex_event_to_abjad_container is None:
            complex_event_to_abjad_container = (
                clock_converters.configurations.DEFAULT_COMPLEX_EVENT_TO_ABJAD_CONTAINER
            )
        self._complex_event_to_abjad_container = complex_event_to_abjad_container

    def convert(
        self,
        clock_event_to_convert: clock_events.ClockEvent,
        is_repeating: bool,
        magnification_size: int = -2,
    ) -> abjad.StaffGroup:
        clock_event_to_convert_duration = clock_event_to_convert.duration.duration
        time_signature_tuple = (
            abjad.TimeSignature(
                (
                    clock_event_to_convert_duration.numerator,
                    clock_event_to_convert_duration.denominator,
                )
            ),
        )
        for sequential_event in clock_event_to_convert:
            sequential_event.time_signature_tuple = time_signature_tuple
        abjad_staff_group = self._complex_event_to_abjad_container.convert(
            clock_event_to_convert
        )

        abjad_staff_group_name = abjad_staff_group.name

        for staff_index, abjad_staff in enumerate(abjad_staff_group):
            abjad_staff.name = f"{abjad_staff_group_name}-staff-{staff_index}"
            leaf_selection = abjad.select.leaves(abjad_staff_group)
            first_leaf, last_leaf = leaf_selection[0], leaf_selection[-1]
            first_leaf_before = (
                r"\omit Staff.TimeSignature "
                r"\undo \omit Staff.BarLine "
                r"\undo \omit Score.BarLine "
                rf"\magnifyStaff #(magstep {magnification_size})"
            )
            if is_repeating:
                first_leaf_before = rf'{first_leaf_before} \bar ".|:"'

            abjad.attach(
                abjad.LilyPondLiteral(
                    first_leaf_before,
                    site="absolute_before",
                ),
                first_leaf,
            )
            abjad.attach(
                abjad.LilyPondLiteral(
                    r"\omit Staff.BarLine " r"\omit Score.BarLine ",
                    site="absolute_after",
                ),
                first_leaf,
            )
            if is_repeating:
                abjad.attach(
                    abjad.LilyPondLiteral(
                        r"\undo \omit Staff.BarLine "
                        r"\undo \omit Score.BarLine "
                        r'\bar  ":|."',
                        site="after",
                    ),
                    last_leaf,
                )
        return abjad_staff_group


class ClockToAbjadScore(core_converters.abc.Converter):
    """Convert :class:`mutwo.clock_interfaces.Clock` to :class:`abjad.Block`."""

    def __init__(
        self,
        # XXX: It looks tempting to move 'tag_to_abjad_staff_group_converter'
        # to a `convert` parameter and to remove 'tag_tuple'. But their function
        # is completely different:
        #
        #   (a) tag_to_abjad_staff_group_converter should map each tag which
        #       appears in the complete composition to a
        #       EventPlacementToAbjadStaffGroupDict instance.
        #
        #   (b) tag_tuple, on the other hand, is provided to specify which
        #       voices are mandatory in the returned score (aka partbook).
        tag_to_abjad_staff_group_converter: dict[Tag, EventPlacementToAbjadStaffGroup],
        clock_event_to_abjad_staff_group: ClockEventToAbjadStaffGroup = ClockEventToAbjadStaffGroup(),
        timeline_to_event_placement_tuple: timeline_converters.TimeLineToEventPlacementTuple = timeline_converters.TimeLineToEventPlacementTuple(),
        event_placement_tuple_to_split_event_placement_dict: timeline_converters.EventPlacementTupleToSplitEventPlacementDict = timeline_converters.EventPlacementTupleToSplitEventPlacementDict(),
        event_placement_tuple_to_gapless_event_placement_tuple: timeline_converters.EventPlacementTupleToGaplessEventPlacementTuple = timeline_converters.EventPlacementTupleToGaplessEventPlacementTuple(),
    ):
        self._clock_event_to_abjad_staff_group = clock_event_to_abjad_staff_group
        self._tag_to_abjad_staff_group_converter = tag_to_abjad_staff_group_converter
        self._timeline_to_event_placement_tuple = timeline_to_event_placement_tuple
        self._event_placement_tuple_to_split_event_placement_dict = (
            event_placement_tuple_to_split_event_placement_dict
        )
        self._event_placement_tuple_to_gapless_event_placement_tuple = (
            event_placement_tuple_to_gapless_event_placement_tuple
        )

    def _add_clock_events_to_abjad_score(
        self,
        clock_to_convert: clock_interfaces.Clock,
        abjad_score: abjad.Score,
    ):
        abjad_container = abjad.Container([])
        for is_repeating, clock_line in zip(
            (False, True, False), clock_to_convert.clock_line_tuple
        ):
            if clock_line:
                clock_event = clock_line.clock_event
                abjad_staff_group = self._clock_event_to_abjad_staff_group.convert(
                    clock_event, is_repeating
                )
                abjad_container.append(abjad_staff_group)
        abjad_score.append(abjad_container)

    def _add_event_placements_to_abjad_score(
        self,
        clock_to_convert: clock_interfaces.Clock,
        tag_tuple: tuple[Tag, ...],
        abjad_score: abjad.Score,
    ):
        event_placement_list: list[timeline_interfaces.EventPlacement] = []
        delay = core_parameters.DirectDuration(0)
        for clock_line in clock_to_convert.clock_line_tuple:
            if clock_line:
                clock_line_event_placement_tuple = (
                    self._timeline_to_event_placement_tuple.convert(
                        clock_line, tag_tuple
                    )
                )
                if delay > 0:
                    for event_placement in clock_line_event_placement_tuple:
                        event_placement.move_by(delay)
                event_placement_list.extend(clock_line_event_placement_tuple)
                delay += clock_line.duration

        tag_to_event_placement_tuple = (
            self._event_placement_tuple_to_split_event_placement_dict.convert(
                tuple(event_placement_list)
            )
        )

        clock_duration = clock_to_convert.duration
        for tag, event_placement_tuple in tag_to_event_placement_tuple.items():
            gapless_event_placement_tuple = (
                self._event_placement_tuple_to_gapless_event_placement_tuple.convert(
                    event_placement_tuple, clock_duration
                )
            )
            try:
                event_placement_to_abjad_staff_group = (
                    self._tag_to_abjad_staff_group_converter[tag]
                )
            except KeyError:
                warnings.warn(clock_utilities.UndefinedConverterForTagWarning(tag))
            else:
                abjad_container = abjad.Container([])
                for event_placement in gapless_event_placement_tuple:
                    abjad_staff_group = event_placement_to_abjad_staff_group.convert(
                        event_placement
                    )
                    abjad_container.append(abjad_staff_group)
                abjad_score.append(abjad_container)

    def convert(
        self,
        clock_to_convert: clock_interfaces.Clock,
        tag_tuple: tuple[Tag, ...],
    ) -> abjad.Score:
        abjad_score = abjad.Score([])
        abjad_score.remove_commands.append("System_start_delimiter_engraver")
        self._add_clock_events_to_abjad_score(clock_to_convert, abjad_score)
        self._add_event_placements_to_abjad_score(
            clock_to_convert, tag_tuple, abjad_score
        )
        return abjad_score


class AbjadScoreToAbjadScoreBlock(core_converters.abc.Converter):
    def get_abjad_layout_block(self, moment: int = 4) -> abjad.Block:
        abjad_layout_block = abjad.Block("layout")
        abjad_layout_block.items.append(r"\context { \Staff \RemoveEmptyStaves }")
        abjad_layout_block.items.append(
            r"""
\context {
  \Score
  % Remove all-rest staves also in the first system
  \override VerticalAxisGroup.remove-first = ##t
  % If only one non-empty staff in a system exists, still print the starting bar
  \override SystemStartBar.collapse-height = #1
  % Avoid bar lines from time signatures of other staff groups
  % (move them to Staff context).
  \consists "Timing_translator"
  \consists "Default_bar_line_engraver"
}
\context {
  \Staff
  \consists "Timing_translator"
  \consists "Default_bar_line_engraver"
}
"""
        )
        abjad_layout_block.items.append(
            rf"""
% PROPORTIONAL NOTATION!!
\context {{
  \Score
  proportionalNotationDuration = #(ly:make-moment 1/{moment})
  \override SpacingSpanner.uniform-stretching = ##t
  \override SpacingSpanner.strict-grace-spacing = ##t
  \override Beam.breakable = ##t
  \override Glissando.breakable = ##t
  \override TextSpanner.breakable = ##t
}}
"""
        )
        abjad_layout_block.items.append("indent = 0")
        return abjad_layout_block

    def convert(
        self, abjad_score_to_convert: abjad.Score, moment: int = 4
    ) -> abjad.Block:
        abjad_score_block = abjad.Block("score")
        abjad_score_block.items.append(abjad_score_to_convert)
        abjad_layout_block = self.get_abjad_layout_block(moment)
        abjad_score_block.items.append(abjad_layout_block)
        return abjad_score_block


class AbjadScoreBlockTupleToLilyPondFile(core_converters.abc.Converter):
    def get_header_block(
        self,
        title: typing.Optional[str] = None,
        composer: typing.Optional[str] = None,
        year: typing.Optional[str] = None,
        tagline: str = '""',
    ) -> abjad.Block:
        header_block = abjad.Block("header")
        if title is not None:
            header_block.items.append(rf"title = {title}")
        if year is not None:
            header_block.items.append(rf"year = {year}")
        if composer is not None:
            header_block.items.append(rf"composer = {composer}")
        header_block.items.append(rf"tagline = {tagline}")
        return header_block

    def get_paper_block(self) -> abjad.Block:
        paper_block = abjad.Block("paper")
        paper_block.items.append(r"system-separator-markup = \slashSeparator")
        paper_block.items.append(
            r"system-system-spacing = #'((basic-distance . 25.1) (padding . 10))"
        )
        paper_block.items.append(
            r"""
    #(define fonts
        (make-pango-font-tree "EB Garamond" "Nimbus Sans" "Luxi Mono" (/ staff-height pt 20)))
        """
        )
        return paper_block

    def convert(
        self, abjad_score_block_tuple_to_convert: tuple[abjad.Block, ...]
    ) -> abjad.LilyPondFile:
        lilypond_file = abjad.LilyPondFile([])

        header_block = self.get_header_block()
        paper_block = self.get_paper_block()

        lilypond_file.items.append(r'#(set-default-paper-size "a4" ' "'landscape)")
        lilypond_file.items.append(header_block)
        lilypond_file.items.append(paper_block)
        lilypond_file.items.extend(abjad_score_block_tuple_to_convert)

        return lilypond_file
