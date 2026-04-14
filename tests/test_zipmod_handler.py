"""
tests/test_zipmod_handler.py — Tests for zipmod metadata parsing.
"""

import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from handlers.zipmod_handler import parse_zipmod


_SAMPLE_MANIFEST = b"""<?xml version="1.0" encoding="UTF-8"?>
<manifest schema-ver="1">
    <guid>com.test.author.testmod</guid>
    <name>Test Mod</name>
    <version>1.5.0</version>
    <author>TestAuthor</author>
    <game>HS2</game>
    <description>A unit test mod.</description>
</manifest>
"""


def make_zipmod(manifest_content: bytes = _SAMPLE_MANIFEST) -> Path:
    fd, path = tempfile.mkstemp(suffix=".zipmod")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        if manifest_content is not None:
            zf.writestr("manifest.xml", manifest_content)
        zf.writestr("abdata/test.unity3d", b"\x00" * 64)
    return Path(path)


class TestZipmodHandler(unittest.TestCase):

    def test_parses_correct_metadata(self):
        zp = make_zipmod()
        try:
            info = parse_zipmod(zp)
            self.assertTrue(info.has_manifest)
            self.assertEqual(info.guid, "com.test.author.testmod")
            self.assertEqual(info.name, "Test Mod")
            self.assertEqual(info.version, "1.5.0")
            self.assertEqual(info.author, "TestAuthor")
            self.assertEqual(info.game, "HS2")
            self.assertFalse(info.is_corrupt)
        finally:
            zp.unlink()

    def test_handles_missing_manifest(self):
        fd, path = tempfile.mkstemp(suffix=".zipmod")
        os.close(fd)
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("somefile.unity3d", b"\x00" * 64)
        try:
            info = parse_zipmod(Path(path))
            self.assertFalse(info.has_manifest)
            self.assertFalse(info.is_corrupt)
            self.assertTrue(info.unknown)
        finally:
            Path(path).unlink()

    def test_handles_corrupt_zipmod(self):
        fd, path = tempfile.mkstemp(suffix=".zipmod")
        with os.fdopen(fd, "wb") as f:
            f.write(b"this is not a zip file at all")
        try:
            info = parse_zipmod(Path(path))
            self.assertTrue(info.is_corrupt)
        finally:
            Path(path).unlink()

    def test_empty_fields_produce_unknown(self):
        manifest = b"<manifest><guid></guid><version></version></manifest>"
        zp = make_zipmod(manifest)
        try:
            info = parse_zipmod(zp)
            self.assertTrue(info.has_manifest)
            self.assertTrue(info.unknown)
        finally:
            zp.unlink()


if __name__ == "__main__":
    unittest.main()
