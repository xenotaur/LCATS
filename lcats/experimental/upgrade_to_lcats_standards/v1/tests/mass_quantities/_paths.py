"""Import only the standalone extraction utilities without LCATS installation."""
import sys
import pathlib
SOURCE = pathlib.Path(__file__).resolve().parents[2] / "lcats" / "gatherers" / "mass_quantities"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))
