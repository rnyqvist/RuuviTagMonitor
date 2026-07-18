"""Initialize Tcl before Tkinter when using Python install-manager runtimes."""

import ctypes
import os
import sys


bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
os.environ["TCL_LIBRARY"] = os.path.join(bundle_dir, "_tcl_data")
os.environ["TK_LIBRARY"] = os.path.join(bundle_dir, "_tk_data")

tcl = ctypes.WinDLL(os.path.join(bundle_dir, "tcl86t.dll"))
tcl.Tcl_FindExecutable.argtypes = [ctypes.c_char_p]
tcl.Tcl_FindExecutable(os.path.join(bundle_dir, "python.exe").encode("utf-8"))
