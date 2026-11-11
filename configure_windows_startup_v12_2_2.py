from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
APP=ROOT/'app'
if str(APP) not in sys.path: sys.path.insert(0,str(APP))
from windows_startup import apply_default_if_unset

def main() -> int:
    ok, message = apply_default_if_unset(True)
    print(message)
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
