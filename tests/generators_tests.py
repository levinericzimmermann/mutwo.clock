import unittest

import treelib

from mutwo import clock_generators
from mutwo import core_events


class PickSampleTest(unittest.TestCase):
    class PickSampleExample(clock_generators.PickSample):
        def __call__(self):
            try:
                return self._item_tuple[0]
            except IndexError:
                return None

    def get_pick_sample_test_class(self):
        return self.PickSampleExample

    def get_kwargs(self):
        return {}

    def setUp(self):
        self.test_data = tuple("abcdefg")
        self.pick_sample = self.get_pick_sample_test_class()(
            self.test_data, **self.get_kwargs()
        )

    def test_call(self):
        self.assertTrue(self.pick_sample() in self.test_data)

    def test_reset(self):
        new_test_data = (1, 2, 3)
        self.pick_sample.reset(new_test_data)
        self.assertTrue(self.pick_sample() in new_test_data)

    def test_refresh(self):
        self.pick_sample.refresh(self.test_data)
        self.assertTrue(self.pick_sample() in self.test_data)
        new_test_data = (1, 2, 3)
        self.pick_sample.refresh(new_test_data)
        self.assertTrue(self.pick_sample() in new_test_data)


class PickSampleByCycleTest(PickSampleTest):
    def get_pick_sample_test_class(self):
        return clock_generators.PickSampleByCycle

    def test_cycle_call(self):
        self.assertEqual(self.pick_sample(), self.test_data[0])
        self.assertEqual(self.pick_sample(), self.test_data[1])
        self.assertEqual(self.pick_sample(), self.test_data[2])


class PickSampleByChoiceTest(PickSampleTest):
    def get_pick_sample_test_class(self):
        return clock_generators.PickSampleByChoice


class ClockTreeTest(unittest.TestCase):
    def setUp(self):
        self.fetch_event = clock_generators.PickSampleByCycle(
            (core_events.SimpleEvent(1),)
        )
        self.fetch_child = clock_generators.PickSampleByCycle()
        self.clock_tree = clock_generators.ClockTree()

    def test_create_layer(self):
        self.clock_tree.create_layer("root", None, self.fetch_event, self.fetch_child)
        expected_node = treelib.Node(identifier="root")
        expected_node.data = clock_generators.ClockLayer(
            self.clock_tree, expected_node, self.fetch_event, self.fetch_child
        )
        created_node = self.clock_tree["root"]
        self.assertEqual(created_node.identifier, expected_node.identifier)
        self.assertEqual(created_node.data.tree, expected_node.data.tree)
        self.assertEqual(
            created_node.data.node.identifier, expected_node.data.node.identifier
        )
        self.assertEqual(created_node.data.fetch_event, expected_node.data.fetch_event)
        self.assertEqual(created_node.data.fetch_child, expected_node.data.fetch_child)

        self.clock_tree.create_layer(
            "child", "root", self.fetch_event, self.fetch_child
        )
        child_node = self.clock_tree["child"]
        self.assertEqual("root", child_node.predecessor(self.clock_tree.identifier))


class ClockLayerTest(unittest.TestCase):
    def setUp(self):
        self.fetch_event_root = clock_generators.PickSampleByCycle(
            (core_events.SimpleEvent(10),)
        )
        self.fetch_event_leaf = clock_generators.PickSampleByCycle(
            (core_events.SimpleEvent(1),)
        )
        self.fetch_child = clock_generators.PickSampleByCycle()
        self.clock_tree = clock_generators.ClockTree()

        self.root_node = treelib.Node(identifier="root")
        self.root_node.data = clock_generators.ClockLayer(
            self.clock_tree, self.root_node, self.fetch_event_root, self.fetch_child
        )

        self.leaf_node = treelib.Node(identifier="leaf")
        self.leaf_node.data = clock_generators.ClockLayer(
            self.clock_tree, self.leaf_node, self.fetch_event_leaf, self.fetch_child
        )

        self.clock_tree.add_node(self.root_node)
        self.clock_tree.add_node(self.leaf_node, parent=self.root_node)

    def test_child_tuple(self):
        self.assertEqual(self.root_node.data.child_tuple, (self.leaf_node,))

    def test_pop_event(self):
        self.assertEqual(
            self.leaf_node.data.pop_event(),
            (
                core_events.SequentialEvent([core_events.SimpleEvent(1)]),
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSequentialEvent(
                            [core_events.SimpleEvent(1).set("is_active", True)],
                            tag="leaf",
                        )
                    ]
                ),
            ),
        )
        self.assertEqual(
            self.root_node.data.pop_event(),
            (
                core_events.SequentialEvent(
                    [core_events.SimpleEvent(10), core_events.SimpleEvent(1)]
                ),
                core_events.SimultaneousEvent(
                    [
                        core_events.TaggedSequentialEvent(
                            [core_events.SimpleEvent(11).set("is_active", True)],
                            tag="root",
                        ),
                        core_events.TaggedSequentialEvent(
                            [
                                core_events.SimpleEvent(10).set("is_active", False),
                                core_events.SimpleEvent(1).set("is_active", True),
                            ],
                            tag="leaf",
                        ),
                    ]
                ),
            ),
        )
