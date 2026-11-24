"""Drive the installed game for live tests: start, stop, keys, screenshots, log.

Requires a test-mode install (`python -m ua install --game DIR --test-mode`):
the plugin then runs the game borderless and saves frames on request.

  python tools/runtime/live.py start
  python tools/runtime/live.py keys ENTER DOWN DOWN ENTER     # key presses (virtual keyboard, no focus)
  python tools/runtime/live.py hold W 2                      # hold a key for 2 seconds
  python tools/runtime/live.py shot main-menu                # -> build/screens/main-menu.png
  python tools/runtime/live.py log
  python tools/runtime/live.py stop
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXE_NAME = "LEGOIndy.exe"
STEAM_APP_ID = "32330"

GAME_DIR = Path(os.environ.get("UA_STEAM_GAME") or sys.exit("Set UA_STEAM_GAME to the Steam game folder."))
SCREENS = GAME_DIR / "scripts" / "screens"
LOG = GAME_DIR / "scripts" / "legoindy-ua-pc.log"
OUT = REPO / "build" / "screens"

user32 = ctypes.WinDLL("user32", use_last_error=True)

# DirectInput reads hardware scan codes.
SCAN = {"ESC": 0x01, "ENTER": 0x1C, "SPACE": 0x39, "UP": 0xC8, "DOWN": 0xD0, "LEFT": 0xCB, "RIGHT": 0xCD,
        "W": 0x11, "A": 0x1E, "S": 0x1F, "D": 0x20, "J": 0x24, "K": 0x25, "L": 0x26, "I": 0x17,
        "TAB": 0x0F, "BACK": 0x0E, "Z": 0x2C, "X": 0x2D, "C": 0x2E, "V": 0x2F, "Q": 0x10, "E": 0x12,
        "F1": 0x3B, "U": 0x16, "H": 0x23, "F2": 0x3C, "M": 0x32, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05}
EXTENDED = {"UP", "DOWN", "LEFT", "RIGHT"}
# Test mode feeds keys straight into the game's DirectInput keyboard (VirtualKeys=1),
# so the game needs no focus. UA_LIVE_FOCUS=1 falls back to SendInput with focus.
VIRTUAL = os.environ.get("UA_LIVE_FOCUS") != "1"


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def _send(scan: int, up: bool, extended: bool) -> None:
    flags = 0x0008 | (0x0002 if up else 0) | (0x0001 if extended else 0)  # SCANCODE, KEYUP, EXTENDED
    item = INPUT(type=1)
    item.ki = KEYBDINPUT(0, scan, flags, 0, 0)
    user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT))


def window() -> int:
    found = []
    pids = game_pids()
    if not pids:
        return 0

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def callback(hwnd, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows(callback, 0)
    return found[0] if found else 0


def game_pids() -> set[int]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return {int(line.split('","')[1]) for line in out.splitlines() if line.startswith('"')}


def focus() -> None:
    hwnd = window()
    if not hwnd or user32.GetForegroundWindow() == hwnd:
        return
    user32.ShowWindow(hwnd, 9)
    # Windows refuses SetForegroundWindow to background processes; a synthetic Alt
    # press and attaching to the foreground thread lift the lock.
    kernel32 = ctypes.WinDLL("kernel32")
    current = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    mine = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(mine, current, True)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(mine, current, False)
    time.sleep(0.3)


def _virtual(scans: list[int]) -> None:
    """Hold these DirectInput scan codes via the test-mode virtual keyboard."""
    SCREENS.mkdir(parents=True, exist_ok=True)
    (SCREENS / "keys.txt").write_text(" ".join(f"{s:02X}" for s in scans), encoding="ascii")


def _press(name: str, down: bool) -> None:
    scan, extended = SCAN[name.upper()], name.upper() in EXTENDED
    if VIRTUAL:
        _virtual([scan] if down else [])
    else:
        _send(scan, not down, extended)


def keys(names: list[str], hold: float = 0.12, gap: float = 0.35) -> None:
    if not VIRTUAL:
        focus()
    for name in names:
        if name.startswith("WAIT"):
            time.sleep(float(name[4:] or 1))
            continue
        _press(name, True)
        time.sleep(hold)
        _press(name, False)
        time.sleep(gap)


def hold(name: str, seconds: float) -> None:
    if not VIRTUAL:
        focus()
    _press(name, True)
    time.sleep(seconds)
    _press(name, False)


def shot(name: str, timeout: float = 10) -> Path:
    from PIL import Image
    SCREENS.mkdir(parents=True, exist_ok=True)
    target = SCREENS / f"{name}.bmp"
    if target.exists():
        target.unlink()
    (SCREENS / "request.txt").write_text(name, encoding="ascii")
    end = time.time() + timeout
    while time.time() < end:
        if target.exists():
            time.sleep(0.5)
            OUT.mkdir(parents=True, exist_ok=True)
            png = OUT / f"{name}.png"
            Image.open(target).convert("RGB").save(png)
            target.unlink()
            return png
        time.sleep(0.2)
    raise TimeoutError("no frame: is the game running in test mode?")


def start(wait: float = 20) -> None:
    if game_pids():
        return
    env = dict(os.environ, SteamAppId=STEAM_APP_ID, SteamGameId=STEAM_APP_ID)
    info = subprocess.STARTUPINFO()
    info.dwFlags = subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 4  # SW_SHOWNOACTIVATE: the first window opens without taking focus
    user32 = ctypes.windll.user32
    previous = user32.GetForegroundWindow()
    subprocess.Popen([str(GAME_DIR / EXE_NAME)], cwd=str(GAME_DIR), env=env, startupinfo=info,
                     creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    end = time.time() + wait
    while time.time() < end:
        hwnd = window()
        if hwnd and user32.GetForegroundWindow() == hwnd and previous:
            user32.SetForegroundWindow(previous)  # give focus back if the game took it
        time.sleep(0.5)


def stop() -> None:
    for pid in game_pids():
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    time.sleep(1)


def main(argv: list[str]) -> int:
    command, rest = argv[0], argv[1:]
    if command == "start":
        start()
        print("window" if window() else "no window yet")
    elif command == "stop":
        stop()
    elif command == "keys":
        keys(rest)
    elif command == "hold":
        hold(rest[0], float(rest[1]))
    elif command == "shot":
        print(shot(rest[0]))
    elif command == "log":
        print(LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else "(no log)")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
