"""
tests/test_hasher.py — Unit tests for core/hasher.py
"""

import os
import tempfile
import unittest
from pathlib import Path

from core.hasher import partial_hash, full_hash


class TestHasher(unittest.TestCase):

    def _make_temp_file(self, content: bytes) -> Path:
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        return Path(path)

    def tearDown(self):
        pass  # temp files cleaned up per test

    def test_identical_files_produce_same_partial_hash(self):
        content = b"Hello HS2 " * 10000
        f1 = self._make_temp_file(content)
        f2 = self._make_temp_file(content)
        try:
            self.assertEqual(partial_hash(f1), partial_hash(f2))
        finally:
            f1.unlink(); f2.unlink()

    def test_different_files_produce_different_full_hash(self):
        f1 = self._make_temp_file(b"mod_A content " * 5000)
        f2 = self._make_temp_file(b"mod_B content " * 5000)
        try:
            self.assertNotEqual(full_hash(f1), full_hash(f2))
        finally:
            f1.unlink(); f2.unlink()

    def test_full_hash_is_consistent(self):
        content = b"stable content " * 20000
        f = self._make_temp_file(content)
        try:
            self.assertEqual(full_hash(f), full_hash(f))
        finally:
            f.unlink()

    def test_empty_file(self):
        f = self._make_temp_file(b"")
        try:
            h = partial_hash(f)
            self.assertIsInstance(h, str)  # Should not crash
        finally:
            f.unlink()

    def test_missing_file_returns_empty(self):
        p = Path("nonexistent_file_xyz.bin")
        self.assertEqual(partial_hash(p), "")
        self.assertEqual(full_hash(p), "")


if __name__ == "__main__":
    unittest.main()
