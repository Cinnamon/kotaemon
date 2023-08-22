def test_disable_telemetry_import_haystack_first():
    """Test that telemetry is disabled when kotaemon lib is initiated after"""
    import os
    import haystack.telemetry
    assert haystack.telemetry.telemetry is not None
    assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") != "False"

    import kotaemon     # noqa: F401
    assert haystack.telemetry.telemetry is None
    assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") == "False"


def test_disable_telemetry_import_haystack_after_kotaemon():
    """Test that telemetry is disabled when kotaemon lib is initiated before"""
    import os

    import kotaemon     # noqa: F401
    import haystack.telemetry
    assert haystack.telemetry.telemetry is None
    assert os.environ.get("HAYSTACK_TELEMETRY_ENABLED", "True") == "False"

