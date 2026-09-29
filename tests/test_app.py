import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streamlit.testing.v1 import AppTest


def test_app_runs_without_exception():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception


def test_app_preset_button_runs():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60)
    at.run()
    at.button[0].click().run()
    assert not at.exception
