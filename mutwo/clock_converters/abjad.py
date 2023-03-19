"""Build western notation from :class:`mutwo.clock_interfaces.Clock` and friends.

See abjad_notes.txt for more information regarding internal structure.
"""

import os
import typing
import warnings

import abjad
import quicktions as fractions
import jinja2

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
    "show_barline",
    "override_barline",
)

Tag: typing.TypeAlias = "str"
TagToAbjadStaffGroup: typing.TypeAlias = "dict[Tag, abjad.StaffGroup]"

# TODO(Explicitly add repetition bar lines)
# TODO(Add indicators for start and end ranges!)
# TODO(Add instrument names before each appearing event placement.)

TEMPLATE_PATH = "{}/{}".format(
    "/".join(os.path.abspath(__file__).split("/")[:-1]), "/templates"
)
J2ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_PATH))


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
        placement_mode: typing.Literal["fixed", "floating"] = "fixed",
    ):

        if complex_event_to_abjad_container is None:
            complex_event_to_abjad_container = (
                clock_converters.configurations.DEFAULT_COMPLEX_EVENT_TO_ABJAD_CONTAINER
            )
        self._complex_event_to_abjad_container = complex_event_to_abjad_container
        self._staff_count = staff_count
        self._staff_lilypond_type = staff_lilypond_type
        self._placement_mode = placement_mode

    def _convert_rest(
        self,
        tag: str,
        written_duration: fractions.Fraction,
        scale_durations: str,
    ) -> abjad.StaffGroup:
        staff_group = abjad.StaffGroup([], name=tag)
        for abjad_staff_index in range(self._staff_count):
            skip = abjad.Skip(written_duration)
            match self._placement_mode:
                case "fixed":
                    content = (
                        r"\stopStaff "
                        r"\override Staff.StaffSymbol.line-count = #0 "
                        r"\startStaff "
                        r"\omit Staff.Clef \omit Staff.NoteHead "
                        r"\omit Staff.BarLine "
                    )
                case "floating":
                    content = r"\omit Staff.Clef " "\n" r"\stopStaff "
                case _:
                    raise NotImplementedError(self.mode)
            content = f"{content}\n{scale_durations}"
            abjad.attach(
                abjad.LilyPondLiteral(content, site="before"),
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
        # We need to attach time signatures here. We don't need them
        # for the notation itself, but for the quantizer. If we don't
        # specify them here, the quantizer assumes that we have a time
        # signature of 4/4. And if our events doesn't take 4/4 the
        # quantizer adds a rest at the end of our event, which completely
        # breaks the notation synchronization.
        durationf = event_to_convert.duration.duration
        time_signature = abjad.TimeSignature(
            (durationf.numerator, durationf.denominator)
        )
        for sequential_event in event_to_convert:
            sequential_event.time_signature_tuple = (time_signature,)
        abjad_staff_group = self._complex_event_to_abjad_container.convert(
            event_to_convert
        )
        tag = event_to_convert.tag
        if (real_staff_count := len(abjad_staff_group)) != self._staff_count:
            warnings.warn(
                clock_utilities.BadStaffCountWarning(
                    real_staff_count, self._staff_count, tag
                )
            )
        for abjad_staff_index, abjad_staff in enumerate(abjad_staff_group):
            abjad_staff.name = self._get_abjad_staff_name(tag, abjad_staff_index)
            abjad_staff.lilypond_type = self._staff_lilypond_type
            for abjad_voice_index, abjad_voice in enumerate(abjad_staff):
                abjad_voice.name = f"{abjad_staff.name}-{abjad_voice_index}"
                leaf_selection = abjad.select.leaves(abjad_voice)
                first_leaf = leaf_selection[0]
                match self._placement_mode:
                    case "fixed":
                        content = "\n".join(
                            (
                                r"\stopStaff",
                                r"\revert Staff.StaffSymbol.line-count",
                                r"\startStaff",
                                r"\undo \omit Staff.Clef \undo \omit Staff.NoteHead",
                                r"\undo \hide Staff.BarLine ",
                            )
                        )
                    case "floating":
                        content = r"\startStaff"
                    case _:
                        raise NotImplementedError(self._placement_mode)
                abjad.attach(
                    abjad.LilyPondLiteral(
                        "\n".join(
                            (
                                content,
                                r"\once \undo \omit Staff.Clef",
                                r"\set Staff.forceClef = ##t",
                                show_barline(),
                            )
                        ),
                        site="absolute_before",
                    ),
                    first_leaf,
                )
                for leaf in leaf_selection:
                    abjad.detach(abjad.TimeSignature, leaf)
                    before_literal = f"{scale_durations} {{"
                    abjad.attach(
                        abjad.LilyPondLiteral(
                            before_literal,
                            site="before",
                        ),
                        leaf,
                    )
                    abjad.attach(abjad.LilyPondLiteral("}", site="after"), leaf)
                last_leaf = leaf
                abjad.attach(
                    abjad.LilyPondLiteral(show_barline(), site="after"), last_leaf
                )
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
            first_leaf_before = "\n".join(
                (
                    show_barline(),
                    rf"\magnifyStaff #(magstep {magnification_size})",
                )
            )
            if is_repeating:
                bar_line = ".|:"
                first_leaf_before = (
                    f"{first_leaf_before}\n{override_barline(bar_line)}\n"
                    rf'\bar "{bar_line}"'
                )

            abjad.attach(
                abjad.LilyPondLiteral(
                    first_leaf_before,
                    site="absolute_before",
                ),
                first_leaf,
            )
            if is_repeating:
                abjad.attach(
                    abjad.LilyPondLiteral(
                        "\n".join(
                            (
                                show_barline(),
                                override_barline(":|."),
                            )
                        ),
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
        clock_event_to_abjad_staff_group: typing.Optional[
            ClockEventToAbjadStaffGroup
        ] = ClockEventToAbjadStaffGroup(),
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
        if self._clock_event_to_abjad_staff_group is not None:
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
        abjad_layout_block.items.append(
            str2block(
                J2ENVIRONMENT.get_template("layout.j2").render(
                    moment=moment,
                    remove_empty_staves=remove_empty_staves,
                    move_timing_translator=not consist_timing_translator,
                )
            )
        )
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
        subtitle: typing.Optional[str] = None,
        composer: typing.Optional[str] = None,
        year: typing.Optional[str] = None,
        tagline: str = '""',
    ) -> abjad.Block:
        header_block = abjad.Block("header")
        if title is not None:
            header_block.items.append(rf"title = {title}")
        if subtitle is not None:
            header_block.items.append(rf"subtitle = {subtitle}")
        if year is not None:
            header_block.items.append(rf"year = {year}")
        if composer is not None:
            header_block.items.append(rf"composer = {composer}")
        header_block.items.append(rf"tagline = {tagline}")
        return header_block

    def get_paper_block(self) -> abjad.Block:
        paper_block = abjad.Block("paper")
        paper_block.items.append(
            str2block(
                J2ENVIRONMENT.get_template("paper.j2").render(
                    system_system_padding=self._system_system_padding,
                    system_system_basic_distance=self._system_system_basic_distance,
                    score_system_basic_distance=self._score_system_basic_distance,
                    score_system_padding=self._score_system_padding,
                    markup_system_padding=self._markup_system_padding,
                    markup_system_basic_distance=self._markup_system_basic_distance,
                    font="Liberation Mono",
                    staff_height=self._staff_height,
                )
            )
        )
        return paper_block

    def convert(
        self,
        abjad_score_block_tuple_to_convert: tuple[abjad.Block, ...],
        title: typing.Optional[str] = None,
        subtitle: typing.Optional[str] = None,
        composer: typing.Optional[str] = None,
        year: typing.Optional[str] = None,
        tagline: str = '""',
    ) -> abjad.LilyPondFile:
        lilypond_file = abjad.LilyPondFile([])

        header_block = self.get_header_block(
            title=title,
            subtitle=subtitle,
            composer=composer,
            year=year,
            tagline=tagline,
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


def str2block(content: str) -> str:
    return "\n".join(f"\t{s}" for s in content.strip().splitlines())


def show_barline() -> str:
    def undo(context):
        return rf"\once \undo \omit {context}.BarLine "

    return "\n".join([undo(c) for c in "Staff StaffGroup Score".split(" ")])


def override_barline(symbol) -> str:
    # Lilyponds '\bar "symbol"' is insufficient here.
    # I don't know why, but it doesn't work / doesn't change the
    # bar symbol (maybe it's a bug).
    # When explicitly overridding the glyph name, it works.
    #
    # It's 'glyph-name' and not (as written in ly doc) 'glyph':
    # https://github.com/lilypond/lilypond/blob/c4a9cd742/scm/bar-line.scm#L673
    return rf'\once \override Staff.BarLine.glyph-name = "{symbol}"'
