import unittest

import abjad

from mutwo import clock_converters
from mutwo import clock_events
from mutwo import clock_interfaces
from mutwo import core_events
from mutwo import music_events
from mutwo import timeline_interfaces


class ClockToAbjadScoreTest(unittest.TestCase):
    def setUp(self):
        self.tag_1 = "instr1"
        self.tag_2 = "instr2"
        self.tag_to_abjad_staff_group_converter = {
            self.tag_1: clock_converters.EventPlacementToAbjadStaffGroup(staff_count=2),
            self.tag_2: clock_converters.EventPlacementToAbjadStaffGroup(),
        }
        self.clock_to_abjad_score = clock_converters.ClockToAbjadScore(
            self.tag_to_abjad_staff_group_converter
        )

        import random

        random.seed(10)

        self.start_clock_event = clock_events.ClockEvent(
            [
                core_events.SequentialEvent(
                    [
                        music_events.NoteLike(
                            random.choice("ag"), random.choice([1, 0.5])
                        )
                        for _ in range(10)
                    ]
                )
            ]
        )
        self.clock_event = clock_events.ClockEvent(
            [
                core_events.SequentialEvent(
                    [
                        music_events.NoteLike(
                            random.choice("cde"), random.choice([1, 1.5, 0.5])
                        )
                        for _ in range(30)
                    ]
                )
            ]
        )
        self.start_event_placement_list = [
            timeline_interfaces.EventPlacement(
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSimultaneousEvent(
                            [
                                core_events.SequentialEvent(
                                    [
                                        music_events.NoteLike("d", 1),
                                    ]
                                )
                            ],
                            tag=self.tag_2,
                        )
                    ]
                ),
                0,
                1,
            ),
        ]
        self.event_placement_list = [
            timeline_interfaces.EventPlacement(
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSimultaneousEvent(
                            [
                                core_events.SequentialEvent(
                                    [
                                        music_events.NoteLike("d", 1),
                                    ]
                                )
                            ],
                            tag=self.tag_2,
                        )
                    ]
                ),
                0,
                1,
            ),
            timeline_interfaces.EventPlacement(
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSimultaneousEvent(
                            [
                                core_events.SequentialEvent(
                                    [
                                        music_events.NoteLike("d", 1),
                                        music_events.NoteLike("df", 0.5),
                                    ]
                                )
                            ],
                            tag=self.tag_2,
                        )
                    ]
                ),
                2,
                4,
            ),
            timeline_interfaces.EventPlacement(
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSimultaneousEvent(
                            [
                                core_events.SequentialEvent(
                                    [
                                        music_events.NoteLike("a", 0.5),
                                        music_events.NoteLike("a", 0.5),
                                    ]
                                )
                            ],
                            tag=self.tag_2,
                        ),
                        core_events.TaggedSimultaneousEvent(
                            [
                                core_events.SequentialEvent(
                                    [
                                        music_events.NoteLike("c", 0.5),
                                        music_events.NoteLike("f", 0.5),
                                    ]
                                ),
                                core_events.SequentialEvent(
                                    [
                                        music_events.NoteLike("c", 0.5),
                                        music_events.NoteLike("d", 0.5),
                                    ]
                                ),
                            ],
                            tag=self.tag_1,
                        ),
                    ]
                ),
                20.75,
                25.75,
            ),
        ]
        self.start_clockline = clock_interfaces.ClockLine(
            self.start_clock_event, self.start_event_placement_list
        )
        self.clockline = clock_interfaces.ClockLine(
            self.clock_event, self.event_placement_list
        )
        self.clock = clock_interfaces.Clock(
            self.clockline, self.start_clockline, self.start_clockline
        )

    def test_convert(self):
        abjad_score = self.clock_to_abjad_score.convert(self.clock, (self.tag_2,))

        # Add sample text to check font
        leaf0 = abjad.select.leaves(abjad_score)[1]
        abjad.attach(abjad.Markup("\markup { this is some sample text }"), leaf0)

        abjad_score_block = clock_converters.AbjadScoreToAbjadScoreBlock().convert(
            abjad_score
        )
        lilypond_file = clock_converters.AbjadScoreBlockTupleToLilyPondFile().convert(
            [abjad_score_block]
        )
        abjad.persist.as_pdf(lilypond_file, "test.pdf")
