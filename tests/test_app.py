from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_app_default_run():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    app.button[0].click().run(timeout=60)
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 3
