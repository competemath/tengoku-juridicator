import json
import os
import tempfile
import unittest

from juridicator.ledger import GENESIS, Ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "ledger.jsonl")
        self.ledger = Ledger(self.path)
        for i in range(4):
            self.ledger.append("evidence", {"id": f"e{i}", "n": i})

    def tearDown(self):
        self.dir.cleanup()

    def rewrite(self, fn):
        entries = self.ledger.entries()
        fn(entries)
        with open(self.path, "w") as fh:
            for e in entries:
                fh.write(json.dumps(e, sort_keys=True) + "\n")

    def test_intact_chain_verifies(self):
        self.assertEqual(self.ledger.verify(), (True, None))
        self.assertEqual(Ledger(os.path.join(self.dir.name, "none.jsonl")).head(), GENESIS)

    def test_editing_a_past_entry_is_found_at_that_entry(self):
        self.rewrite(lambda es: es[1]["body"].update(n=99))
        self.assertEqual(self.ledger.verify(), (False, 1))

    def test_deleting_an_entry_is_found(self):
        self.rewrite(lambda es: es.pop(1))
        self.assertFalse(self.ledger.verify()[0])

    def test_reordering_is_found(self):
        self.rewrite(lambda es: es.reverse())
        self.assertFalse(self.ledger.verify()[0])

    def test_truncating_the_tail_needs_the_published_head(self):
        published = self.ledger.head()
        self.rewrite(lambda es: es.pop())
        self.assertEqual(self.ledger.verify(), (True, None))  # internally consistent...
        self.assertEqual(self.ledger.verify(published), (False, 3))  # ...but not the head we published

    def test_rewriting_the_whole_tail_consistently_still_changes_the_head(self):
        published = self.ledger.head()
        other = Ledger(os.path.join(self.dir.name, "other.jsonl"))
        for i in range(4):
            other.append("evidence", {"id": f"e{i}", "n": i + 100})
        self.assertNotEqual(other.head(), published)


if __name__ == "__main__":
    unittest.main()
