"""Contract test: every API path the React app calls must exist in Flask with that HTTP method."""
import re
from pathlib import Path

from werkzeug.exceptions import MethodNotAllowed, NotFound

import app as flask_app

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "src"
CALL = re.compile(r"""\b(?:api|axios)\.(get|post|put|delete|patch)\(\s*([`'"])(/[^`'"]*)\2""")


def _calls():
    for f in FRONTEND.rglob("*.js*"):
        for m in CALL.finditer(f.read_text(errors="ignore")):
            path = re.sub(r"\$\{[^}]+\}", "1", m.group(3)).split("?")[0].rstrip("/")
            yield f.name, m.group(1).upper(), "/api" + path


def test_every_frontend_call_has_a_backend_route():
    adapter = flask_app.app.url_map.bind("localhost")
    problems = []
    for fname, method, path in sorted(set(_calls())):
        try:
            adapter.match(path, method=method)
        except NotFound:
            problems.append(f"{fname}: {method} {path} -> no such route")
        except MethodNotAllowed:
            problems.append(f"{fname}: {method} {path} -> wrong HTTP method")
    assert not problems, "\n".join(problems)
