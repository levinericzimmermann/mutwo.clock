"""Construct clock events from context-free grammars

We use abbreviations for Terminal, NonTerminal, Node and
ContextFreeGrammarRule, because we often use them directly in
our project code.
"""

from __future__ import annotations

import dataclasses
import functools
import operator
import typing
import warnings

import numpy as np
import ranges
import treelib

from mutwo import clock_events
from mutwo import core_events
from mutwo import core_parameters
from mutwo import core_utilities
from mutwo import common_generators

__all__ = ("T", "NT", "SymT", "R", "N", "Tree", "ContextFreeGrammar")

Entry: typing.TypeAlias = typing.Callable
"""Diary entry"""

Weight: typing.TypeAlias = float


class _T(object):
    """Base class for terminal and non terminal in clock grammar"""

    def __init__(self, entry: Entry, *args, **kwargs):
        self.entry = entry
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other: typing.Any) -> bool:
        try:
            return (
                self.entry == other.entry
                and self.args == other.args
                and self.kwargs == other.kwargs
            )
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash(
            (
                self.entry,
                self.args,
                tuple(self.kwargs.keys()),
                tuple(self.kwargs.values()),
            )
        )

    def render(self):
        return self.entry(*self.args, **self.kwargs)


class T(_T, common_generators.Terminal):
    """Terminal of clock grammar"""


class NT(_T, common_generators.NonTerminal):
    """Non-terminal of clock grammar"""


class SymT(common_generators.NonTerminal):
    """Non-terminal which MUST be resolved.

    This is to represent abstract musical structures which don't
    own any concrete musical data yet (e.g. something like "start"
    or "end" of middle part of a composition).
    """

    def __init__(self, name: str, duration_range: typing.Optional[ranges.Range] = None):
        self.name = name
        self.duration_range = duration_range

    def __eq__(self, other: typing.Any):
        try:
            return self.name == other.name
        except AttributeError:
            return False

    def __str__(self) -> str:
        return f"SymT({self.name}, {self.duration_range}"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(self.name)

    def __lt__(self, other) -> bool:
        try:
            return hash(self) < hash(other)
        except Exception:
            return False


@dataclasses.dataclass
class R(common_generators.ContextFreeGrammarRule):
    """Rule for clock chomsky

    Extends basic rule by adding a weight attribute.
    """

    weight: Weight = 1


class N(treelib.Node):
    """Extended tree node"""

    def __init__(self, *args, count: int = 0, weight: Weight = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = count
        self.weight = weight

    @functools.cached_property
    def duration_range(self) -> ranges.Range:
        minima, maxima = (core_parameters.DirectDuration(0) for _ in range(2))
        for t in self.data:
            r = t.entry.duration_range
            minima += r.start
            maxima += r.end
        return ranges.Range(minima, maxima)

    @functools.cached_property
    def is_symbolic(self) -> bool:
        """Return ``True`` if any terminal is only of symbolic nature"""

        for t in self.data:
            if isinstance(t, SymT):
                return True
        return False

    def get_child_weight(self, r_weight: Weight) -> Weight:
        count = self.count + 1
        return (self.weight * self.count / count) + (r_weight * 1 / count)

    def render(self):
        clock_event = clock_events.ClockEvent()
        for t in self.data:
            ev = t.render()
            try:
                clock_event.concatenate_by_tag(ev)
            except core_utilities.NoTagError:
                clock_event.concatenate_by_index(ev)
        return clock_event


class Tree(treelib.Tree):
    def __init__(
        self, *args, random_seed: int = 100, candidate_count: int = 5, **kwargs
    ):
        self._random_seed = random_seed
        self._candidate_count = candidate_count
        super().__init__(*args, **kwargs)

    @functools.cached_property
    def random(self):
        return np.random.default_rng(self._random_seed)

    @functools.cached_property
    def node_tuple(self):
        return tuple(self.nodes.values())

    @functools.cached_property
    def real_node_tuple(self):
        return tuple(
            sorted(
                (n for n in self.node_tuple if not n.is_symbolic),
                key=lambda n: n.duration_range.start,
            )
        )

    def symt_to_n(self, symt: SymT) -> N:
        if dur_range := symt.duration_range:
            valid_node_list = []
            for n in self.real_node_tuple:
                diff_start, diff_end = (
                    abs(
                        core_events.configurations.UNKNOWN_OBJECT_TO_DURATION(
                            getattr(dur_range, p) - getattr(n.duration_range, p)
                        ).duration
                    )
                    if getattr(n.duration_range, p) not in dur_range
                    else 0
                    for p in "start end".split(" ")
                )
                valid_node_list.append((diff_start + diff_end, n))
            min_fitness = min(valid_node_list, key=operator.itemgetter(0))[0]
            valid_node_list = [n for f, n in valid_node_list if f == min_fitness]
        else:
            valid_node_list = self.real_node_tuple

        weight_list = [n.weight for n in valid_node_list]
        return self.random.choice(
            valid_node_list, p=core_utilities.scale_sequence_to_sum(weight_list, 1)
        )


class ContextFreeGrammar(common_generators.ContextFreeGrammar):
    """Adjusted context-free grammar for clock grammar usage"""

    node_class = N

    def __init__(
        self,
        context_free_grammar_rule_sequence: typing.Sequence[R],
    ):
        # XXX: Mostly the same like upstresm ContextFreeGrammar.__init__, with
        # the difference that we use 'set' instead of 'uniqify_iterable'.
        non_terminal_list = []
        for context_free_grammar_rule in context_free_grammar_rule_sequence:
            non_terminal_list.append(context_free_grammar_rule.left_side)
            for terminal_or_non_terminal in context_free_grammar_rule.right_side:
                if isinstance(terminal_or_non_terminal, common_generators.NonTerminal):
                    non_terminal_list.append(terminal_or_non_terminal)
        self._non_terminal_tuple = tuple(set(non_terminal_list))
        self._terminal_tuple = tuple(
            set(
                item
                for item in functools.reduce(
                    operator.add,
                    tuple(
                        context_free_grammar_rule.right_side
                        for context_free_grammar_rule in context_free_grammar_rule_sequence
                    ),
                )
                if isinstance(item, common_generators.Terminal)
            )
        )
        divided_context_free_grammar_rule_list = [[] for _ in self._non_terminal_tuple]
        for context_free_grammar_rule in context_free_grammar_rule_sequence:
            index = self._non_terminal_tuple.index(  # type: ignore
                context_free_grammar_rule.left_side
            )
            divided_context_free_grammar_rule_list[index].append(
                context_free_grammar_rule
            )
        self._divided_context_free_grammar_rule_tuple = tuple(
            tuple(context_free_grammar_rule_list)
            for context_free_grammar_rule_list in divided_context_free_grammar_rule_list
        )
        self._context_free_grammar_rule_tuple = tuple(
            context_free_grammar_rule_sequence
        )

    def _add_node(
        self,
        tree: treelib.Tree,
        data: tuple[Weight, tuple[NT | T, ...]],
        parent: typing.Optional[N] = None,
    ):
        r_weight, d = data
        weight = parent.get_child_weight(r_weight) if parent else 1
        count = parent.count + 1 if parent else 0
        tag = self._data_to_tag(d)
        node = self.node_class(tag=tag, data=d, weight=weight, count=count)
        tree.add_node(node, parent)
        return node

    def _resolve_content(
        self, content: tuple[T | NT, ...]
    ) -> tuple[tuple[T | NT, ...], ...]:
        new_data_list = []
        for i, element in enumerate(content):
            if isinstance(element, common_generators.NonTerminal):
                context_free_grammar_rule_tuple = (
                    self.get_context_free_grammar_rule_tuple(element)
                )
                for context_free_grammar_rule in context_free_grammar_rule_tuple:
                    data = (
                        context_free_grammar_rule.weight,
                        (
                            content[:i]
                            + context_free_grammar_rule.right_side
                            + content[i + 1 :]
                        ),
                    )
                    new_data_list.append(data)
        return tuple(new_data_list)

    def resolve(
        self,
        start: common_generators.NonTerminal,
        limit: typing.Optional[int] = None,
        random_seed: int = 100,
    ) -> Tree:
        """Resolve until only :class:`Terminal` are left or the limit is reached.

        :param start: The start value.
        :type start: NonTerminal
        :param limit: The maximum node levels until the function returns a tree.
            If it is set to `None` it will only stop once all nodes are
            :class:`Terminal`.
        :type limit: typing.Optional[int]
        """

        # XXX: Mostly the same like 'common_generators.resolve', with the
        # difference that we don't use 'treelib.Tree', but our own tree class
        # which has additional methods to easily filter a useable node for a
        # specific condition.
        # This should finally be removed once
        # 'common_generators.ContextFreeGrammar' has a `tree_class` argument
        # or class attribute.

        def is_limit_reached() -> bool:
            if limit is None:
                return False
            else:
                return limit <= counter

        tree = Tree(random_seed=random_seed)
        self._add_node(tree, (1, (start,)))
        is_not_resolved = True
        counter = 0
        while is_not_resolved and not is_limit_reached():
            is_not_resolved = self.resolve_one_layer(tree)
            counter += 1
        return tree
