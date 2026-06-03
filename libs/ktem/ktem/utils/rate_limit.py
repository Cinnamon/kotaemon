from collections import defaultdict
from datetime import datetime, timedelta

import gradio as gr
from decouple import config

# In-memory store for rate limiting (for demonstration purposes)
rate_limit_store: dict[str, dict] = defaultdict(dict)

# Rate limit configuration
RATE_LIMIT = config("RATE_LIMIT", default=20, cast=int)
RATE_LIMIT_PERIOD = timedelta(hours=24)


def check_rate_limit(limit_type: str, request: gr.Request):
    if request is None:
        raise ValueError("This feature is not available")

    user_id = None
    try:
        import gradiologin as grlogin

        user = grlogin.get_user(request)
        if user:
            user_id = user.get("email")
    except (ImportError, AssertionError):
        pass

    if not user_id:
        raise ValueError("Please sign-in to use this feature")

    now = datetime.now()
    user_data = rate_limit_store[limit_type].get(
        user_id, {"count": 0, "reset_time": now + RATE_LIMIT_PERIOD}
    )

    if now >= user_data["reset_time"]:
        # Reset the rate limit for the user
        user_data = {"count": 0, "reset_time": now + RATE_LIMIT_PERIOD}

    if user_data["count"] >= RATE_LIMIT:
        raise ValueError("Rate limit exceeded. Please try again later.")

    # Increment the request count
    user_data["count"] += 1
    rate_limit_store[limit_type][user_id] = user_data

    return user_id
