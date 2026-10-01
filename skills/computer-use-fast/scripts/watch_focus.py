#!/usr/bin/env python3
"""watch_focus.py -- run a command and record, every 50 ms, which app owns the frontmost window and where the
pointer is. Independent of cua-driver: it reads macOS CoreGraphics directly (no permissions needed for these two).

    python3 watch_focus.py -- python3 cu.py --app Calculator --open --type "1+1=" --read

Prints the front app and pointer before, every change seen while the command ran, and after.
"""
import ctypes, ctypes.util, subprocess, sys, threading, time

CG = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
CF = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


CG.CGEventCreate.restype = ctypes.c_void_p
CG.CGEventCreate.argtypes = [ctypes.c_void_p]
CG.CGEventGetLocation.restype = Point
CG.CGEventGetLocation.argtypes = [ctypes.c_void_p]
CG.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
CG.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
CF.CFArrayGetCount.restype = ctypes.c_long
CF.CFArrayGetCount.argtypes = [ctypes.c_void_p]
CF.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
CF.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
CF.CFDictionaryGetValue.restype = ctypes.c_void_p
CF.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
CF.CFStringCreateWithCString.restype = ctypes.c_void_p
CF.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
CF.CFStringGetCString.restype = ctypes.c_bool
CF.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
CF.CFNumberGetValue.restype = ctypes.c_bool
CF.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
CF.CFRelease.argtypes = [ctypes.c_void_p]
UTF8 = 0x08000100
KEY = {k: CF.CFStringCreateWithCString(None, k.encode(), UTF8) for k in ("kCGWindowLayer", "kCGWindowOwnerName")}


def front_app():
    """Owner of the first layer-0 window in front-to-back order: the app whose window is on top."""
    arr = CG.CGWindowListCopyWindowInfo(1 | 16, 0)  # on-screen only, exclude desktop elements
    try:
        for i in range(CF.CFArrayGetCount(arr)):
            d = CF.CFArrayGetValueAtIndex(arr, i)
            layer = ctypes.c_int(-1)
            CF.CFNumberGetValue(CF.CFDictionaryGetValue(d, KEY["kCGWindowLayer"]), 3, ctypes.byref(layer))
            if layer.value == 0:
                buf = ctypes.create_string_buffer(256)
                CF.CFStringGetCString(CF.CFDictionaryGetValue(d, KEY["kCGWindowOwnerName"]), buf, 256, UTF8)
                return buf.value.decode()
    finally:
        CF.CFRelease(arr)
    return "?"


def pointer():
    ev = CG.CGEventCreate(None)
    p = CG.CGEventGetLocation(ev)
    CF.CFRelease(ev)
    return (round(p.x), round(p.y))


def main():
    cmd = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    seen, done, t0 = [], threading.Event(), time.time()

    def sample():
        last = None
        while not done.is_set():
            now = (front_app(), pointer())
            if now != last:
                seen.append((round(time.time() - t0, 2), *now))
                last = now
            time.sleep(0.05)

    start = (front_app(), pointer())
    th = threading.Thread(target=sample, daemon=True)
    th.start()
    rc = subprocess.run(cmd, capture_output=True).returncode
    done.set(); th.join()
    end = (front_app(), pointer())
    changes = seen[1:]  # the first sample is the starting state
    print(f"rc={rc} before={start} after={end} changes_during={changes if changes else 'none'} samples_every=50ms")


if __name__ == "__main__":
    main()
