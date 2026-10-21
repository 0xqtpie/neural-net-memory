import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import current_frontier
import project_tools


class WorkingFrontierTests(unittest.TestCase):
    def test_known_results_and_solved_rows_are_inherited(self):
        rows = current_frontier.current_rows()
        self.assertEqual(len(rows), 60)
        self.assertEqual(sum(not r["optimal"] for r in rows), 21)
        target = next(r for r in rows if (r["graph"], r["budget"]) == ("mlp-b8", 34078720))
        self.assertEqual(target["peak_bytes"], 45056)
        self.assertEqual(target["historical_peak_bytes"], 61440)
        self.assertTrue(next(r for r in rows if (r["graph"], r["budget"]) == ("resnet-b2-c32", 37847040))["optimal"])
        # Exercise every eligible bound-track draw, not just one favorable seed.
        drawn = set()
        for i in range(21):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                project_tools.pick(f"{60:08x}{0:08x}{i:08x}{0:08x}")
            row = json.loads(out.getvalue())["row"]
            self.assertFalse(row["optimal"])
            drawn.add((row["graph"], row["budget"]))
        self.assertEqual(drawn, {(r["graph"], r["budget"]) for r in rows if not r["optimal"]})

    def test_incorrect_proposal_metrics_are_rejected(self):
        original = current_frontier.load
        def changed(path):
            data = original(path)
            if Path(path).name == "candidates.json":
                data[0]["peak_bytes"] -= 1
            return data
        with patch.object(current_frontier, "load", changed):
            with self.assertRaisesRegex(ValueError, "metrics mismatch"):
                current_frontier.current_rows()

    def test_bound_contradicting_witness_is_rejected(self):
        original = current_frontier.load
        def changed(path):
            data = original(path)
            if Path(path).name == "bound-results.json":
                data["bounds"][0]["lower_bound"] = 10**15
            return data
        with patch.object(current_frontier, "load", changed):
            with self.assertRaisesRegex(ValueError, "bound contradicts"):
                current_frontier.current_rows()


if __name__ == "__main__":
    unittest.main()
