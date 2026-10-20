import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

from generate import graph, node, synthetic
from search import baseline_candidates, certificate, exact, optimize
from verifier import Invalid, digest, load, simulate, validate_graph, verify


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.g = graph("chain3", [node("a", ["x"], 2), node("b", ["a"], 3),
                                  node("c", ["b"], 4)], 1, "synthetic", {})
        self.actions = [
            {"op": "forward", "node": "a"}, {"op": "forward", "node": "b"},
            {"op": "forward", "node": "c"}, {"op": "loss"},
            {"op": "backward", "node": "c"}, {"op": "drop", "node": "c"},
            {"op": "backward", "node": "b"}, {"op": "drop", "node": "b"},
            {"op": "backward", "node": "a"}]
        self.c = certificate(self.g, self.actions, 0, "hand-worked")

    def test_hand_accounting(self):
        self.assertEqual(verify(self.g, self.c), {
            "peak_bytes": 10, "recompute_cost": 0, "forward_cost": 3, "backward_cost": 6})

    def test_claim_peak_and_cost(self):
        for key in self.c["claims"]:
            with self.subTest(key=key):
                c = copy.deepcopy(self.c)
                c["claims"][key] += 1
                with self.assertRaisesRegex(Invalid, "incorrect claims"):
                    verify(self.g, c)

    def test_simultaneous_input_output(self):
        g = graph("one", [node("a", ["x"], 7)], 5, "synthetic", {})
        a = [{"op": "forward", "node": "a"}, {"op": "loss"}, {"op": "backward", "node": "a"}]
        self.assertEqual(simulate(g, a, 0)["peak_bytes"], 12)

    def test_missing_forward_dependency(self):
        with self.assertRaisesRegex(Invalid, "missing forward dependency"):
            simulate(self.g, self.actions[1:], 0)

    def test_missing_backward_dependency(self):
        a = self.actions[:4] + [{"op": "drop", "node": "b"}] + self.actions[4:]
        with self.assertRaisesRegex(Invalid, "missing backward activation"):
            simulate(self.g, a, 0)

    def test_backward_order(self):
        a = self.actions[:4] + [{"op": "backward", "node": "a"}]
        with self.assertRaisesRegex(Invalid, "missing downstream gradient"):
            simulate(self.g, a, 0)

    def test_recompute_budget_and_cost(self):
        a = self.actions[:4] + [{"op": "drop", "node": "b"}, {"op": "forward", "node": "b"}] + self.actions[4:]
        with self.assertRaisesRegex(Invalid, "budget exceeded"):
            simulate(self.g, a, 0)
        self.assertEqual(simulate(self.g, a, 1)["recompute_cost"], 1)
        self.assertEqual(simulate(self.g, a, 1)["forward_cost"], 4)

    def test_forbidden_recompute(self):
        g = copy.deepcopy(self.g)
        g["nodes"][1]["recomputable"] = False
        a = self.actions[:4] + [{"op": "drop", "node": "b"}, {"op": "forward", "node": "b"}] + self.actions[4:]
        with self.assertRaisesRegex(Invalid, "illegal recomputation"):
            simulate(g, a, 10)

    def test_hash_binding_and_budget_binding(self):
        c = copy.deepcopy(self.c)
        c["graph_sha256"] = "0" * 64
        with self.assertRaisesRegex(Invalid, "hash mismatch"):
            verify(self.g, c)
        with self.assertRaisesRegex(Invalid, "budget mismatch"):
            verify(self.g, self.c, 1)

    def test_invalid_actions(self):
        cases = [
            ([{"op": "loss"}], "incomplete"),
            ([{"op": "drop", "node": "x"}], "immutable"),
            ([{"op": "drop", "node": "a"}], "absent"),
            ([{"op": "backward", "node": "a"}], "before loss"),
            ([{"op": "magic"}], "unknown"),
            (self.actions[:1] * 2, "overwrite"),
            (self.actions[:4] + [{"op": "loss"}], "repeated"),
            (self.actions + [{"op": "backward", "node": "a"}], "duplicate"),
            (self.actions[:-1], "incomplete"),
            (self.actions[:3] + [{"op": "drop", "node": "c"}, {"op": "loss"}], "output missing"),
        ]
        for a, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(Invalid, message):
                simulate(self.g, a, 0)

    def test_bad_graphs(self):
        for field, value in [("bytes", -1), ("bytes", True), ("cost", 0), ("cost", 1.2),
                             ("deps", ["c"]), ("backward_requires", ["c"]), ("recomputable", 1)]:
            g = copy.deepcopy(self.g)
            g["nodes"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(Invalid):
                validate_graph(g)

    def test_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "bad.json"
            p.write_text('{"budget":0,"budget":1}')
            with self.assertRaisesRegex(Invalid, "duplicate JSON"):
                load(p)

    def test_no_bool_metric_or_budget(self):
        c = copy.deepcopy(self.c)
        c["claims"]["recompute_cost"] = False
        with self.assertRaises(Invalid):
            verify(self.g, c)
        with self.assertRaises(Invalid):
            simulate(self.g, self.actions, True)

    def test_exact_hand_optimum(self):
        # x=1,a=2,b=3,c=4; executing c needs b+c+x = 8.
        # Drop a before c, then recompute it after B(c), achieving this bound.
        self.assertEqual(exact(self.g, 0)["claims"]["peak_bytes"], 10)
        self.assertEqual(exact(self.g, 1)["claims"]["peak_bytes"], 8)

    def test_exact_limit_never_claims_optimum(self):
        with self.assertRaisesRegex(RuntimeError, "NO optimality"):
            exact(self.g, 0, max_states=1)

    def test_seed_reproducibility(self):
        self.assertEqual(optimize(self.g, [0, 1, 3], 42, 40),
                         optimize(self.g, [0, 1, 3], 42, 40))

    def test_multiple_sinks_required_at_loss(self):
        g = graph("fork", [node("a", ["x"], 3), node("b", ["x"], 4)], 2, "synthetic", {})
        legal = [{"op": "forward", "node": "b"}, {"op": "forward", "node": "a"},
                 {"op": "loss"}, {"op": "backward", "node": "a"}, {"op": "backward", "node": "b"}]
        self.assertEqual(simulate(g, legal, 0)["peak_bytes"], 9)
        illegal = legal[:2] + [{"op": "drop", "node": "a"}] + legal[2:]
        with self.assertRaisesRegex(Invalid, "output missing"):
            simulate(g, illegal, 0)

    def test_all_baselines_legal(self):
        for g in synthetic():
            for name, actions in baseline_candidates(g):
                with self.subTest(graph=g["id"], baseline=name):
                    verify(g, certificate(g, actions, 1000, name))

    def test_random_small_dags_exact_vs_certificates(self):
        rng = random.Random(714)
        for i in range(12):
            ns = []
            for j in range(4):
                options = ["x"] + [n["id"] for n in ns]
                deps = rng.sample(options, min(len(options), rng.randint(1, 2)))
                ns.append(node(f"n{j}", deps, rng.randint(1, 5), rng.randint(1, 3)))
            g = graph(f"fuzz{i}", ns, 1, "synthetic", {})
            optimum = exact(g, 4)
            verify(g, optimum, 4)
            for name, actions in baseline_candidates(g):
                c = certificate(g, actions, 1000, name)
                if c["claims"]["recompute_cost"] <= 4:
                    self.assertLessEqual(optimum["claims"]["peak_bytes"], c["claims"]["peak_bytes"])


if __name__ == "__main__":
    unittest.main()
