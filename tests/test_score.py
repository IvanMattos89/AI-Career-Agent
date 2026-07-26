import unittest

from app.utils.score import classify_score


class ScoreClassificationTest(unittest.TestCase):
    def test_classifies_score_ranges(self):
        self.assertEqual(classify_score(80).code, "excellent")
        self.assertEqual(classify_score(60).code, "good")
        self.assertEqual(classify_score(40).code, "regular")
        self.assertEqual(classify_score(-1).code, "needs_improvement")
        self.assertEqual(classify_score(101).code, "excellent")
