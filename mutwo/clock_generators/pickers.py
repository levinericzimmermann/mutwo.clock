import abc
import functools
import itertools
import typing

import numpy as np

from mutwo import core_utilities

__all__ = ("PickSample", "PickSampleByCycle", "PickSampleByChoice")


class PickSample(abc.ABC):
    def __init__(self, item_tuple: tuple[typing.Any, ...] = tuple([])):
        self.reset(item_tuple)

    @functools.cached_property
    def _item_tuple_hash(self) -> int:
        return hash(self._item_tuple)

    def reset(self, item_tuple: tuple[typing.Any, ...]):
        try:
            del self._item_tuple_hash
        except AttributeError:
            pass
        self._item_tuple = item_tuple

    def refresh(self, item_tuple: tuple[typing.Any, ...]):
        if hash(item_tuple) != hash(self._item_tuple_hash):
            self.reset(item_tuple)

    @abc.abstractmethod
    def __call__(self) -> typing.Any:
        ...


class PickSampleByCycle(PickSample):
    def reset(self, item_tuple: tuple[typing.Any, ...]):
        super().reset(item_tuple)
        self._item_cycle = itertools.cycle(self._item_tuple)

    def __eq__(self, other: typing.Any) -> bool:
        return core_utilities.test_if_objects_are_equal_by_parameter_tuple(
            self, other, ("_item_cycle",)
        )

    def __call__(self) -> typing.Any:
        try:
            return next(self._item_cycle)
        except StopIteration:
            return None


class PickSampleByChoice(PickSample):
    def __init__(self, *args, random_seed: int = 100, **kwargs):
        self._random = np.random.default_rng(random_seed)
        super().__init__(*args, **kwargs)

    def __eq__(self, other: typing.Any) -> bool:
        return core_utilities.test_if_objects_are_equal_by_parameter_tuple(
            self, other, ("_item_tuple", "_random")
        )

    def __call__(self) -> typing.Any:
        try:
            return self._random.choice(self._item_tuple)
        except ValueError:
            return None
