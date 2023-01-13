import typing

from mutwo import clock_events
from mutwo import clock_generators
from mutwo import core_converters


__all__ = ("SymTSequenceToClockEventTuple",)


class SymTSequenceToClockEventTuple(core_converters.abc.Converter):
    def __init__(self, context_free_grammar: clock_generators.ContextFreeGrammar):
        self._context_free_grammar = context_free_grammar

    def convert(
        self,
        symt_sequence: typing.Sequence[clock_generators.SymT],
        limit: typing.Optional[int] = 4,
    ) -> tuple[clock_events.ClockEvent, ...]:
        symt_to_tree = {
            symt: self._context_free_grammar.resolve(symt, limit)
            for symt in set(symt_sequence)
        }
        clock_event_list = []
        for symt in symt_sequence:
            n = symt_to_tree[symt].symt_to_n(symt)
            clock_event_list.append(n.render())
        return tuple(clock_event_list)
