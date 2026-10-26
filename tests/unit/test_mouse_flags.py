from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from filewheel.core.models import (
    LLMHF_INJECTED,
    LLMHF_LOWER_IL_INJECTED,
    MouseEvent,
    mouse_event_permitted,
)
from filewheel.platforms.windows.hook import WindowsMouseSource


@pytest.mark.parametrize(
    "injected, flags, default_allowed, opted_in_allowed",
    [
        (False, None, True, True),
        (False, 0, True, True),
        (True, None, False, False),
        (True, 0, False, False),
        (False, LLMHF_INJECTED, False, True),
        (True, LLMHF_INJECTED, False, True),
        (False, LLMHF_LOWER_IL_INJECTED, False, False),
        (True, LLMHF_LOWER_IL_INJECTED, False, False),
        (False, 3, False, False),
        (True, 3, False, False),
        (False, 4, False, False),
        (False, 5, False, False),
        (False, 0xFFFFFFFF, False, False),
    ],
)
def test_mouse_policy(injected, flags, default_allowed, opted_in_allowed):
    event = MouseEvent(1, (12, 34), 1.0, 123, injected, flags)
    assert event.native_flags == flags
    assert event.injected is (injected or bool((flags or 0) & 3))
    assert event.lower_integrity_injected is bool((flags or 0) & LLMHF_LOWER_IL_INJECTED)
    assert mouse_event_permitted(event) is default_allowed
    assert mouse_event_permitted(event, allow_injected=True) is opted_in_allowed


@pytest.mark.parametrize("flags", [True, False, -1, 0x100000000, 1.0, "1"])
def test_model_requires_dword_flags(flags):
    with pytest.raises(ValueError, match="DWORD"):
        MouseEvent(1, (0, 0), 1.0, 123, native_flags=flags)


@pytest.mark.parametrize("injected", [0, 1, None, "true"])
def test_model_requires_boolean_injected(injected):
    with pytest.raises(ValueError, match="bool"):
        MouseEvent(1, (0, 0), 1.0, 123, injected)


@pytest.mark.parametrize(
    "field, value", [("native_flags", True), ("native_flags", -1), ("injected", 1)]
)
def test_policy_defends_against_malformed_event(field, value):
    event = MouseEvent(1, (0, 0), 1.0, 123)
    object.__setattr__(event, field, value)
    assert not mouse_event_permitted(event, allow_injected=True)


def test_opt_in_requires_explicit_true():
    event = MouseEvent(1, (0, 0), 1.0, 123, native_flags=LLMHF_INJECTED)
    assert not mouse_event_permitted(event, allow_injected=1)
    assert not mouse_event_permitted(object(), allow_injected=True)


def test_fake_hook_preserves_full_flags_and_always_chains():
    events = Queue()
    seen = []
    info = SimpleNamespace(pt=SimpleNamespace(x=12, y=34), flags=0)
    user = Mock()
    user.GetForegroundWindow.return_value = 123
    user.SetTimer.return_value = 1
    user.GetMessageW.return_value = 0
    user.UnhookWindowsHookEx.return_value = True
    user.CallNextHookEx.return_value = 42

    def install(_kind, callback, _module, _thread):
        for flags in (0, 1, 2, 3, 0x80000001):
            info.flags = flags
            seen.append(callback(0, 0x0207, 99))
        seen.append(callback(-1, 0x0207, 99))
        seen.append(callback(0, 0x0200, 99))
        return 456

    user.SetWindowsHookExW.side_effect = install
    native = SimpleNamespace(
        user=user,
        kernel=SimpleNamespace(GetModuleHandleW=lambda _: 1),
        c=SimpleNamespace(
            cast=lambda *_: SimpleNamespace(contents=info), POINTER=lambda _: None,
            byref=lambda value: value,
        ),
        MouseData=object,
        callback_type=lambda callback: callback,
        w=SimpleNamespace(MSG=object),
    )
    with patch("filewheel.platforms.windows.hook.Native", return_value=native):
        source = WindowsMouseSource(events)
        source.run()
    captured = [events.get_nowait() for _ in range(events.qsize())]
    assert [event.native_flags for event in captured] == [0, 1, 2, 3, 0x80000001]
    assert [event.injected for event in captured] == [False, True, True, True, True]
    assert [event.sequence for event in captured] == [1, 2, 3, 4, 5]
    assert all(event.point == (12, 34) and event.window_id == 123 for event in captured)
    assert seen == [42] * 7
    assert user.CallNextHookEx.call_count == 7
    assert source.dropped_events == 0
    user.UnhookWindowsHookEx.assert_called_once_with(456)
