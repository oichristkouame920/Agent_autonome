"""Instance GUI unique AgentLocal et activation de la fenêtre existante."""
from __future__ import annotations

import ctypes
import os

MUTEX_NAME = "Local\\AgentLocal_GUI_V12_3"
ERROR_ALREADY_EXISTS = 183


class InstanceGuard:
    def __init__(self) -> None:
        self.handle = None
        self.already_running = False
        if os.name != "nt":
            return
        kernel32 = ctypes.windll.kernel32
        self.handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        self.already_running = bool(self.handle and kernel32.GetLastError() == ERROR_ALREADY_EXISTS)

    def close(self) -> None:
        if self.handle and os.name == "nt":
            try:
                ctypes.windll.kernel32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None


def focus_existing_window() -> bool:
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        found = {"hwnd": None}
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @EnumWindowsProc
        def callback(hwnd, _lparam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value.startswith("AgentLocal - Assistant local"):
                found["hwnd"] = hwnd
                return False
            return True

        user32.EnumWindows(callback, 0)
        hwnd = found["hwnd"]
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False
