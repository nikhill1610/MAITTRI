import os
import sys

# Allow 'app.main:app' to be loaded directly when running from project root
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.join(_root_dir, "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

_backend_app_dir = os.path.join(_backend_dir, "app")
if os.path.isdir(_backend_app_dir) and _backend_app_dir not in __path__:
    __path__.insert(0, _backend_app_dir)
