# Disable telemetry with monkey patching
import logging
import pprint

logger = logging.getLogger(__name__)
try:
    import posthog

    def capture(*args, **kwargs):
        payload = pprint.pformat(
            {"args": args, "kwargs": kwargs},
            width=100,
            compact=False,
        )
        logger.info("posthog.capture called:\n%s", payload)

    posthog.capture = capture
except ImportError:
    pass

try:
    import os

    os.environ["HAYSTACK_TELEMETRY_ENABLED"] = "False"
    import haystack.telemetry

    haystack.telemetry.telemetry = None
except ImportError:
    pass
