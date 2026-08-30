import unittest

from takeoff_fn import config, records
from takeoff_fn.errors import FailedPrecondition, NotFound

NOW = 1_700_000_000_000


class FakeDoc:
    def __init__(self, data):
        self._data = data
        self.updates = []

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data)

    def get(self):
        return self

    def update(self, patch):
        self.updates.append(patch)
        if self._data is not None:
            self._data.update(patch)


class FakeCollection:
    def __init__(self, doc):
        self._doc = doc
        self.name = None

    def document(self, _id):
        return self._doc


class FakeDb:
    def __init__(self, data):
        self.doc = FakeDoc(data)
        self.collections = []

    def collection(self, name):
        self.collections.append(name)
        return FakeCollection(self.doc)


def _record_data(**overrides):
    data = {
        "customerId": "cus-1",
        "status": "queued",
        "estimateId": "est-1",
        "updatedAt": NOW - 1000,
        "sourceFiles": [
            {"fileName": "a.pdf", "storageUrl": "gs://b/estimate_images/cus-1/est-1/a.pdf"},
            {"fileName": "b.pdf", "storageUrl": "gs://b/estimate_images/cus-1/est-1/b.pdf"},
        ],
    }
    data.update(overrides)
    return data


class TestLoadRecord(unittest.TestCase):
    def test_a_queued_record_loads_with_indexed_source_files(self):
        db = FakeDb(_record_data())
        rec = records.load_record(db, "t1", "cus-1", NOW)
        self.assertEqual(db.collections, [config.TAKEOFF_COLLECTION])
        self.assertEqual(rec.customer_id, "cus-1")
        self.assertEqual(rec.estimate_id, "est-1")
        self.assertEqual([s.index for s in rec.source_files], [0, 1])
        self.assertEqual([s.file_name for s in rec.source_files], ["a.pdf", "b.pdf"])

    def test_a_missing_document_is_not_found(self):
        with self.assertRaises(NotFound):
            records.load_record(FakeDb(None), "t1", "cus-1", NOW)

    def test_another_tenants_record_is_indistinguishable_from_a_missing_one(self):
        # The exception type is the callable error code, so a different type
        # here would let a caller probe which takeoff ids exist.
        db = FakeDb(_record_data(customerId="cus-2"))
        with self.assertRaises(NotFound) as mismatch:
            records.load_record(db, "t1", "cus-1", NOW)
        with self.assertRaises(NotFound) as missing:
            records.load_record(FakeDb(None), "t1", "cus-1", NOW)
        self.assertEqual(str(mismatch.exception), str(missing.exception))

    def test_a_live_processing_run_is_refused(self):
        db = FakeDb(_record_data(status="processing", updatedAt=NOW - 1000))
        with self.assertRaises(FailedPrecondition):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_stale_processing_run_may_be_restarted(self):
        stale = NOW - (config.STALE_PROCESSING_SECONDS * 1000) - 1
        db = FakeDb(_record_data(status="processing", updatedAt=stale))
        rec = records.load_record(db, "t1", "cus-1", NOW)
        self.assertEqual(rec.status, "processing")

    def test_an_approved_record_is_refused(self):
        db = FakeDb(_record_data(status="approved"))
        with self.assertRaises(FailedPrecondition):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_record_with_no_source_files_is_a_failed_precondition(self):
        db = FakeDb(_record_data(sourceFiles=[]))
        with self.assertRaises(FailedPrecondition):
            records.load_record(db, "t1", "cus-1", NOW)

    def test_a_source_file_without_a_storage_url_is_skipped(self):
        db = FakeDb(_record_data(sourceFiles=[
            {"fileName": "a.pdf"},
            {"fileName": "b.pdf", "storageUrl": "gs://b/estimate_images/cus-1/e/b.pdf"},
        ]))
        rec = records.load_record(db, "t1", "cus-1", NOW)
        self.assertEqual([s.file_name for s in rec.source_files], ["b.pdf"])
        self.assertEqual([s.index for s in rec.source_files], [0])

    def test_a_missing_estimate_id_is_none_not_an_error(self):
        db = FakeDb(_record_data(estimateId=None))
        self.assertIsNone(records.load_record(db, "t1", "cus-1", NOW).estimate_id)


class TestStatusTransitions(unittest.TestCase):
    def test_mark_processing_writes_status_and_timestamps(self):
        db = FakeDb(_record_data())
        records.mark_processing(db, "t1", NOW)
        self.assertEqual(db.doc.updates, [{
            "status": config.STATUS_PROCESSING,
            "startedAt": NOW, "updatedAt": NOW, "error": None}])

    def test_mark_awaiting_review_writes_the_document_and_clears_error(self):
        db = FakeDb(_record_data())
        records.mark_awaiting_review(db, "t1", '{"schemaVersion":1}', NOW)
        self.assertEqual(db.doc.updates, [{
            "status": config.STATUS_AWAITING_REVIEW,
            "document": '{"schemaVersion":1}',
            "error": None, "updatedAt": NOW}])

    def test_mark_failed_writes_the_message(self):
        db = FakeDb(_record_data())
        records.mark_failed(db, "t1", "boom", NOW)
        self.assertEqual(db.doc.updates, [{
            "status": config.STATUS_FAILED, "error": "boom", "updatedAt": NOW}])

    def test_mark_failed_truncates_a_very_long_message(self):
        db = FakeDb(_record_data())
        records.mark_failed(db, "t1", "x" * 5000, NOW)
        self.assertEqual(len(db.doc.updates[0]["error"]), records.MAX_ERROR_CHARS)


if __name__ == "__main__":
    unittest.main()
