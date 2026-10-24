"""Native class lookup with a fake API; no Windows class or ABI proof."""

import ctypes
import unittest
from types import SimpleNamespace

from filewheel.platforms.windows.native import Native


def native_with_lookup(lookup):
    native = object.__new__(Native)
    native.c = ctypes
    native.user = SimpleNamespace(GetClassNameW=lookup)
    return native


class NativeWindowClassTests(unittest.TestCase):
    def test_native_api_receives_requested_hwnd_and_bounded_buffer(self):
        calls = []

        def lookup(hwnd, buffer, count):
            calls.append((hwnd, count, len(buffer)))
            buffer.value = "SysListView32"
            return len(buffer.value)

        native = native_with_lookup(lookup)
        self.assertEqual(native.window_class(123), "SysListView32")
        self.assertEqual(calls, [(123, 256, 256)])

    def test_native_class_is_not_inferred_from_uia_label(self):
        def lookup(hwnd, buffer, count):
            buffer.value = "DirectUIHWND"
            return len(buffer.value)

        self.assertEqual(native_with_lookup(lookup).window_class(123), "DirectUIHWND")

    def test_invalid_handles_do_not_call_native_api(self):
        def lookup(*args):
            self.fail("invalid handle reached native API")

        native = native_with_lookup(lookup)
        for hwnd in (None, False, True, 0, -1, "123", 123.0,
                     1 << (ctypes.sizeof(ctypes.c_void_p) * 8)):
            with self.subTest(hwnd=hwnd):
                self.assertIsNone(native.window_class(hwnd))

    def test_failed_lookup_returns_none_even_if_buffer_has_text(self):
        def lookup(hwnd, buffer, count):
            buffer.value = "unreliable"
            return 0

        self.assertIsNone(native_with_lookup(lookup).window_class(123))

    def test_empty_class_name_returns_none(self):
        self.assertIsNone(native_with_lookup(lambda hwnd, buffer, count: 1).window_class(123))
