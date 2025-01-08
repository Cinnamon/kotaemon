from prometheus_client import Counter

FILE_UPLOAD = Counter("file_upload", "Total of uploaded file(s)")

MESSAGES = Counter("message_sent", "Total of message(s)")


class MetricCounter:
    FILE_UPLOAD: Counter = FILE_UPLOAD
    MESSAGES: Counter = MESSAGES
