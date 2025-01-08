from prometheus_client import Counter, start_http_server
from pydantic_settings import BaseSettings, SettingsConfigDict


class PrometheusSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix="prometheus_")

    port: int = 8000
    host: str = "0.0.0.0"
    enable: bool = True


def on_start_prometheus() -> None:
    settings = PrometheusSettings()
    print("Prometheus settings:", settings.model_dump())

    if settings.enable:
        print(f"Enable prometheus server at: {settings.host}:{settings.port}")
        start_http_server(port=settings.port, addr=settings.host)

    return


FILE_UPLOAD = Counter("file_upload", "Total of uploaded file(s)")

MESSAGES = Counter("message_sent", "Total of message(s)")


class MetricCounter:
    FILE_UPLOAD: Counter = FILE_UPLOAD
    MESSAGES: Counter = MESSAGES


on_start_prometheus()
