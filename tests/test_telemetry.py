import os
import sys

import pytest

from .conftest import skip_when_haystack_not_installed


@pytest.fixture
def clean_artifacts_for_telemetry():
    try:
        del sys.modules["kotaemon"]
    except KeyError:
        pass

    try:
        del sys.modules["haystack"]
    except KeyError:
        pass

    try:
        del sys.modules["haystack.telemetry"]
    except KeyError:
        pass

    if "HAYSTACK_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HAYSTACK_TELEMETRY_ENABLED"]


@pytest.mark.usefixtures("clean_artifacts_for_telemetry")
@skip_when_haystack_not_installed
def test_disable_telemetry_import_haystack_first():
    """Test that telemetry is disabled when kotaemon lib is initiated after"""
    import os

    import haystack.telemetry

    assert haystack.telemetry.telemetry is not None
    assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") != "False"

    import kotaemon  # noqa: F401

    assert haystack.telemetry.telemetry is None
    assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") == "False"


@pytest.mark.usefixtures("clean_artifacts_for_telemetry")
@skip_when_haystack_not_installed
def test_disable_telemetry_import_haystack_after_kotaemon():
    """Test that telemetry is disabled when kotaemon lib is initiated before"""
    import os

    import haystack.telemetry

    import kotaemon  # noqa: F401

    assert haystack.telemetry.telemetry is None
    assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") == "False"
