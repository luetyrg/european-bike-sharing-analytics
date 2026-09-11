"""Small end-to-end dashboard check using Streamlit's test runtime."""

from streamlit.testing.v1 import AppTest


def test_dashboard_builds_and_filters_without_exceptions() -> None:
    app = AppTest.from_file("dashboard/app.py", default_timeout=30).run()
    assert not app.exception
    assert len(app.metric) == 6
    assert len(app.get("plotly_chart")) == 6

    app.selectbox[0].set_value("Bilbao")
    app.radio[0].set_value("Weekend")
    app.run()
    assert not app.exception

