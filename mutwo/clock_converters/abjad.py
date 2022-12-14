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
        staff_lilypond_type: str = "Staff",
    ):

        if complex_event_to_abjad_container is None:
            complex_event_to_abjad_container = (
                clock_converters.configurations.DEFAULT_COMPLEX_EVENT_TO_ABJAD_CONTAINER
            )
        self._complex_event_to_abjad_container = complex_event_to_abjad_container
        self._staff_count = staff_count
        self._staff_lilypond_type = staff_lilypond_type

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
                [skip],
                name=self._get_abjad_staff_name(tag, abjad_staff_index),
                lilypond_type=self._staff_lilypond_type,
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
        abjad_staff_group = self._complex_event_to_abjad_container.convert(
            event_to_convert
        )
        tag = event_to_convert.tag
        for abjad_staff_index, abjad_staff in enumerate(abjad_staff_group):
            abjad_staff.name = self._get_abjad_staff_name(tag, abjad_staff_index)
            abjad_staff.lilypond_type = self._staff_lilypond_type
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
                                r"\once \undo \omit Staff.Clef",
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
                    before_literal = f"{scale_durations} {{"
                    abjad.detach(abjad.TimeSignature, leaf)
                    abjad.attach(
                        abjad.LilyPondLiteral(
                            before_literal,
                            site="before",
                        ),
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

        # NOTE: limit_denominator is necessary, because Lilypond will complain
        # otherwise and will simply hide notes.
        ratio = (real_duration / written_duration).limit_denominator(10000)

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
                r"\omit Staff.BarLine \omit Score.BarLine "
                r"\omit Staff.TimeSignature "
                r"\once \undo \omit Staff.BarLine "
                r"\once \undo \omit Score.BarLine "
                rf"\magnifyStaff #(magstep {magnification_size})"
                r"\set Score.connectArpeggios = ##t"
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
                        r"\once \undo \omit Staff.BarLine "
                        r"\once \undo \omit Score.BarLine "
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
    def get_abjad_layout_block(
        self,
        moment: int = 4,
        remove_empty_staves: bool = False,
        consist_timing_translator: bool = True,
    ) -> abjad.Block:
        abjad_layout_block = abjad.Block("layout")
        timing_translator = (
            r'\consists "Timing_translator"' if consist_timing_translator else ""
        )
        abjad_layout_block.items.append(
            r"""
ragged-right = ##t
ragged-last = ##t"""
        )
        if remove_empty_staves:
            abjad_layout_block.items.append(r"\context { \Staff \RemoveEmptyStaves }")
        abjad_layout_block.items.append(
            rf"""
\context {{
  \Score
  % DEACTIVATED: Remove all-rest staves also in the first system
  % \override VerticalAxisGroup.remove-first = ##t
  % If only one non-empty staff in a system exists, still print the starting bar
  \override SystemStartBar.collapse-height = #1
  % Avoid bar lines from time signatures of other staff groups
  % (move them to Staff context).
  \remove "Timing_translator"
  \remove "Default_bar_line_engraver"
  % Allow breaks between bar lines
  % (this is important because we have)
  % (only very few bar lines).
  % !forbidBreakBetweenBarLines = ##f
  % !forbidBreakBetweenBarLines doesn't exist yet in 2.22,
  % !it's only available from 2.23. Once migrated to next
  % !stable release I should remove the 'barAlways' and use
  % !forbidBreakBetweenBarLines !
  barAlways = ##t
  % Arpeggi across staves
  \consists "Span_arpeggio_engraver"
}}
\context {{
  \Staff
  {timing_translator}
  \consists "Default_bar_line_engraver"
}}
\context {{
  \Voice
  % Allow line breaks with tied notes
  \remove Forbid_line_break_engraver
}}
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
        self,
        abjad_score_to_convert: abjad.Score,
        remove_empty_staves: bool = False,
        consist_timing_translator: bool = True,
        moment: int = 4,
    ) -> abjad.Block:
        abjad_score_block = abjad.Block("score")
        abjad_score_block.items.append(abjad_score_to_convert)
        abjad_layout_block = self.get_abjad_layout_block(
            moment,
            remove_empty_staves=remove_empty_staves,
            consist_timing_translator=consist_timing_translator,
        )
        abjad_score_block.items.append(abjad_layout_block)
        return abjad_score_block


class AbjadScoreBlockTupleToLilyPondFile(core_converters.abc.Converter):
    def __init__(
        self,
        with_point_and_click: bool = False,
        add_page_break_between_clock: bool = True,
        system_system_padding: float = 4,
        system_system_basic_distance: float = 15,
        score_system_padding: float = 4,
        score_system_basic_distance: float = 15,
        markup_system_padding: float = 4,
        markup_system_basic_distance: float = 15,
        staff_height: float = 20,
    ):
        self._with_point_and_click = with_point_and_click
        self._system_system_padding = system_system_padding
        self._system_system_basic_distance = system_system_basic_distance
        self._score_system_padding = score_system_padding
        self._score_system_basic_distance = score_system_basic_distance
        self._markup_system_padding = markup_system_padding
        self._markup_system_basic_distance = markup_system_basic_distance
        self._staff_height = staff_height
        self._add_page_break_between_clock = add_page_break_between_clock

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
        # paper_block.items.append(r"system-separator-markup = \markup \fill-line { \override #'(span-factor . 1/16) \draw-hline }")
        paper_block.items.append(
            rf"""
system-system-spacing = #'(
    (basic-distance . {self._system_system_basic_distance})
    (padding . {self._system_system_padding})
)
score-system-spacing = #'(
    (basic-distance . {self._score_system_basic_distance})
    (padding . {self._score_system_basic_distance})
)
markup-system-spacing = #'(
    (basic-distance . {self._markup_system_basic_distance})
    (padding . {self._markup_system_basic_distance})
)
"""
        )
        font = "Liberation Mono"
        paper_block.items.append(
            rf"""
    #(define fonts
        (make-pango-font-tree "{font}" "{font}" "{font}"
        (/ staff-height pt {self._staff_height}))
      )
        """
        )
        paper_block.items.append(
            r"""
#(define fonts
    (set-global-fonts
     #:music "beethoven"
     #:brace "beethoven"
    )
)"""
        )
        paper_block.items.append(r"print-first-page-number = ##t")
        return paper_block

    def convert(
        self,
        abjad_score_block_tuple_to_convert: tuple[abjad.Block, ...],
        title: typing.Optional[str] = None,
        composer: typing.Optional[str] = None,
        year: typing.Optional[str] = None,
        tagline: str = '""',
    ) -> abjad.LilyPondFile:
        lilypond_file = abjad.LilyPondFile([])

        header_block = self.get_header_block(
            title=title, composer=composer, year=year, tagline=tagline
        )
        paper_block = self.get_paper_block()

        if not self._with_point_and_click:
            lilypond_file.items.append(r"\pointAndClickOff")
        lilypond_file.items.append(r'#(set-default-paper-size "a4" ' "'landscape)")
        lilypond_file.items.append(header_block)
        lilypond_file.items.append(paper_block)

        for abjad_score_block in abjad_score_block_tuple_to_convert:
            lilypond_file.items.append(abjad_score_block)
            lilypond_file.items.append("\n")
            if self._add_page_break_between_clock:
                lilypond_file.items.append(r"\pageBreak")
                lilypond_file.items.append("\n")

        return lilypond_file
