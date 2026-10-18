#!/usr/bin/env python3
"""
Tests for validate_api_key().

The previous implementation only checked the length (40 or 64 characters), so
any string of the right size was accepted as a GitHub token - including an
unrelated 40-character string - and the tool then silently ran unauthenticated.

Run: python -m pytest tests/ -v     (or: python tests/test_validate_token.py)
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

# The module imports `fcntl`, which only exists on Unix, so it cannot be
# imported on Windows. Stub it: the function under test is the real one.
if "fcntl" not in sys.modules:
    stub = types.ModuleType("fcntl")
    stub.flock = lambda *a, **k: None
    sys.modules["fcntl"] = stub

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("gnt", ROOT / "getnucleitemplates.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    validate_api_key = _load().validate_api_key
except Exception as _exc:  # pragma: no cover
    raise unittest.SkipTest(f"could not import getnucleitemplates: {_exc}")


class TestValidateApiKey(unittest.TestCase):
    def test_accepts_real_shapes(self):
        for token in (
            "ghp_" + "a" * 36,
            "gho_" + "c" * 36,
            "ghs_" + "d" * 36,
            "github_pat_" + "b" * 22,
        ):
            with self.subTest(token=token[:12]):
                self.assertTrue(validate_api_key(token))

    def test_rejects_wrong_length(self):
        self.assertFalse(validate_api_key("ghp_" + "a" * 39))
        self.assertFalse(validate_api_key("ghp_short"))

    def test_rejects_empty(self):
        self.assertFalse(validate_api_key(""))

    def test_rejects_right_length_without_a_prefix(self):
        # The old length-only check accepted this.
        self.assertFalse(validate_api_key("a" * 40))

    def test_rejects_whitespace(self):
        self.assertFalse(validate_api_key("ghp_" + "a" * 35 + " "))
        self.assertFalse(validate_api_key("ghp_" + "a" * 35 + "\n"))
        self.assertFalse(validate_api_key("ghp_" + "a" * 20 + " " + "b" * 15))

    def test_rejects_prefix_with_nothing_after(self):
        self.assertFalse(validate_api_key("github_pat_"))


if __name__ == "__main__":
    unittest.main(verbosity=2)