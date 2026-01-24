"""PyInstaller runtime hook for autobahn.

Disables the NVX (Cython) module which requires .c source files at runtime.
This forces autobahn to use its pure Python fallback implementation.
"""
import os

# Disable NVX before autobahn is imported
os.environ["AUTOBAHN_USE_NVX"] = "0"
