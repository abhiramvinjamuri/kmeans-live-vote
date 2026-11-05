import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import model
import storage


class PollTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        storage.DATABASE = str(Path(self.temp.name) / "test.sqlite3")
        self.choices = {n: "Blue" for n in model.POINTS}
        storage.setting("round", "1")

    def tearDown(self):
        self.temp.cleanup()

    def test_kmeans_steps_and_convergence(self):
        stages = model.STAGES
        self.assertEqual(len(stages), 6)
        self.assertEqual(stages[1][1]["C"], 1)
        self.assertEqual(stages[3][1]["C"], 0)
        labels, centers = stages[-1][1:3]
        self.assertEqual(labels, model.assign(centers))
        self.assertEqual(centers, model.move(labels, centers))
        self.assertAlmostEqual(centers[0], 10.4333333333)
        self.assertAlmostEqual(centers[1], 12.0333333333)
        self.assertEqual(model.move({n: 0 for n in model.POINTS}, model.INITIAL)[1], model.INITIAL[1])

    def test_duplicate_and_closed_votes(self):
        self.assertEqual(storage.vote_once(1, self.choices, 1), "recorded")
        self.assertEqual(storage.vote_once(1, self.choices, 1), "duplicate")
        storage.change_setting("voting", "closed")
        self.assertEqual(storage.vote_once(2, self.choices, 1), "closed")
        self.assertEqual(storage.votes()[1], 1)

    def test_new_round_and_stale_form(self):
        storage.vote_once(1, self.choices, 1)
        storage.new_round()
        storage.change_setting("voting", "open")
        self.assertEqual(storage.votes()[1], 0)
        self.assertEqual(storage.vote_once(2, self.choices, 1), "stale")
        self.assertEqual(storage.vote_once(1, self.choices, 2), "recorded")

    def test_concurrent_class(self):
        with ThreadPoolExecutor(max_workers=15) as pool:
            results = list(pool.map(lambda seat: storage.vote_once(seat, self.choices, 1), range(1, 61)))
        self.assertEqual(results.count("recorded"), 60)
        counts, total = storage.votes()
        self.assertEqual(total, 60)
        self.assertTrue(all(pair == [60, 0] for pair in counts.values()))

    def test_invalid_ballot(self):
        self.assertEqual(storage.vote_once(61, self.choices, 1), "invalid")
        self.assertEqual(storage.vote_once(1, {"A": "Blue"}, 1), "invalid")


if __name__ == "__main__":
    unittest.main()
