"""finalize_candidates applies the offline confidence floors unconditionally."""
import unittest

from models import Candidate
from pipeline import OFFLINE_MIN_CONFIDENCE, finalize_candidates


def cand(cid, etype, conf, **evidence):
    return Candidate(candidate_id=cid, entity_type=etype,
                     bbox=(10.0, 10.0, 50.0, 50.0), confidence=conf,
                     evidence=dict(evidence))


class TestFinalizeCandidates(unittest.TestCase):
    def test_candidate_above_threshold_becomes_an_entity(self):
        entities, rejected = finalize_candidates([cand("door_0001", "door", 0.80)])
        self.assertEqual([e.entity_id for e in entities], ["door_0001"])
        self.assertEqual(rejected, [])

    def test_candidate_below_threshold_is_rejected(self):
        entities, rejected = finalize_candidates([cand("door_0001", "door", 0.40)])
        self.assertEqual(entities, [])
        self.assertEqual(rejected[0]["candidate_id"], "door_0001")
        self.assertEqual(rejected[0]["source"], "offline_filter")

    def test_thresholds_are_per_type(self):
        # 0.52 clears window (0.50) but not door (0.55)
        entities, _ = finalize_candidates(
            [cand("door_0001", "door", 0.52), cand("window_0001", "window", 0.52)])
        self.assertEqual([e.entity_id for e in entities], ["window_0001"])

    def test_all_entities_are_sourced_heuristic(self):
        entities, _ = finalize_candidates([cand("door_0001", "door", 0.80)])
        self.assertEqual(entities[0].source, "heuristic")

    def test_rooms_bypass_the_thresholds(self):
        room = cand("room_0001", "room", 0.10, polygon=[[0, 0], [10, 0], [10, 10]])
        entities, rejected = finalize_candidates([room])
        self.assertEqual([e.entity_id for e in entities], ["room_0001"])
        self.assertEqual(rejected, [])

    def test_room_polygon_reaches_entity_attributes(self):
        room = cand("room_0001", "room", 0.85, polygon=[[0, 0], [10, 0], [10, 10]],
                    area_px2=50.0)
        entities, _ = finalize_candidates([room])
        self.assertEqual(entities[0].attributes["polygon"], [[0, 0], [10, 0], [10, 10]])
        self.assertEqual(entities[0].attributes["area_px2"], 50.0)

    def test_door_subtype_evidence_reaches_entity_attributes(self):
        d = cand("door_0001", "door", 0.80, assembly_type="sliding", swing_layout="garden")
        entities, _ = finalize_candidates([d])
        self.assertEqual(entities[0].attributes["assembly_type"], "sliding")
        self.assertEqual(entities[0].attributes["swing_layout"], "garden")

    def test_label_is_taken_from_evidence(self):
        d = cand("door_0001", "door", 0.80, nearby_label="D01")
        entities, _ = finalize_candidates([d])
        self.assertEqual(entities[0].label, "D01")

    def test_offline_thresholds_are_unchanged(self):
        self.assertEqual(OFFLINE_MIN_CONFIDENCE,
                         {"door": 0.55, "window": 0.50, "label": 0.65, "schedule": 0.50})


class TestValidationPathIsGone(unittest.TestCase):
    def test_gemini_client_no_longer_exposes_the_validation_helpers(self):
        from gemini import client
        for name in ("SYSTEM_PROMPT", "REQUIRED_KEYS", "build_user_message",
                     "_validate_response", "call_gemini", "_candidate_to_dict"):
            self.assertFalse(hasattr(client, name), f"{name} should be deleted")

    def test_pipeline_no_longer_exposes_the_merge_function(self):
        import pipeline
        self.assertFalse(hasattr(pipeline, "merge_gemini_and_heuristics"))


if __name__ == "__main__":
    unittest.main()
