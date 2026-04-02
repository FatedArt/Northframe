import os
import sys
import unittest
from pathlib import Path


# Import app.py from the parent folder.
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

# The app imports `flask` and `requests`. In CI-like environments they may be absent.
# For our unit tests (pure functions), we stub them to avoid installing dependencies.
try:
    import requests  # noqa: F401
except Exception:
    import types

    requests_stub = types.ModuleType("requests")
    exc_type = type("HTTPError", (Exception,), {})
    requests_stub.exceptions = types.SimpleNamespace(HTTPError=exc_type)

    def _no_network_get(*_args, **_kwargs):
        raise RuntimeError("Network is not available in unit tests")

    requests_stub.get = _no_network_get
    sys.modules["requests"] = requests_stub

try:
    import flask  # noqa: F401
except Exception:
    import types

    flask_stub = types.ModuleType("flask")

    class DummyFlask:
        def __init__(self, *_args, **_kwargs):
            pass

        def route(self, *_args, **_kwargs):
            def decorator(fn):
                return fn

            return decorator

    flask_stub.Flask = DummyFlask
    flask_stub.render_template = lambda *_args, **_kwargs: None
    flask_stub.request = types.SimpleNamespace(args={}, json={}, method=None)
    flask_stub.jsonify = lambda *_args, **_kwargs: None
    sys.modules["flask"] = flask_stub

import app as audit_app  # noqa: E402


class TestAuditCore(unittest.TestCase):
    def test_parse_figma_url_filekey_nodeid_encoded(self):
        url = "https://www.figma.com/file/ABCDE12345/My-Design?node-id=1234%3A5678"
        parsed = audit_app.parse_figma_url(url)
        self.assertEqual(parsed["file_key"], "ABCDE12345")
        self.assertEqual(parsed["node_id"], "1234:5678")

    def test_parse_figma_url_filekey_nodeid_dash(self):
        url = "https://www.figma.com/design/ABCDE12345/My-Design?node-id=1234-5678"
        parsed = audit_app.parse_figma_url(url)
        self.assertEqual(parsed["file_key"], "ABCDE12345")
        self.assertEqual(parsed["node_id"], "1234:5678")

    def test_parse_figma_url_invalid_host(self):
        url = "https://example.com/file/ABCDE12345?node-id=1234-5678"
        parsed = audit_app.parse_figma_url(url)
        self.assertIsNone(parsed["file_key"])
        self.assertIsNone(parsed["node_id"])

    def test_detect_viewport_keyword(self):
        self.assertEqual(audit_app.detect_viewport("Mobile Button", "Header"), "mobile")
        self.assertEqual(audit_app.detect_viewport("Desktop Card", "Web"), "desktop")

    def test_detect_viewport_by_width(self):
        self.assertEqual(audit_app.detect_viewport("Card", "Any", width=500), "mobile")
        self.assertEqual(audit_app.detect_viewport("Card", "Any", width=900), "desktop")

    def test_score_tokens_alias_usage(self):
        # Minimal payload: only alias usage matters here.
        variables_data = {
            "meta": {
                "variableCollections": {
                    "col1": {
                        "name": "Semantic",
                        "modes": [{"modeId": "m1", "name": "Light"}],
                        "variableIds": ["var1", "var2"],
                    }
                },
                "variables": {
                    "var1": {
                        "id": "var1",
                        "name": "color/text/primary",
                        "resolvedType": "COLOR",
                        "valuesByMode": {"m1": {"type": "VARIABLE_ALIAS"}},
                    },
                    "var2": {
                        "id": "var2",
                        "name": "color/surface",
                        "resolvedType": "COLOR",
                        "valuesByMode": {"m1": {"type": "COLOR"}},
                    },
                },
            }
        }

        _, subchecks = audit_app.score_tokens(flat_nodes=[], variables_data=variables_data)
        alias_check = next(ch for ch in subchecks if ch["label"] == "Alias usage")
        # alias_mode_alias_values=1, alias_mode_values=2 => alias_pct=0.5 => alias_score=int(0.5*150)=75
        self.assertEqual(alias_check["score"], 75)


if __name__ == "__main__":
    unittest.main()

