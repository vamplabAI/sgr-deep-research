import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


_initialized = False


def ensure_tracing(service_name: str = "airsroute-gateway") -> None:
    global _initialized
    if _initialized:
        return

    # Set up a basic tracer provider with a console exporter by default.
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # Choose exporter
    exporter = None
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            # Optional dependency: opentelemetry-exporter-otlp
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint.rstrip("/"))
        except Exception:
            exporter = None

    if exporter is None:
        exporter = ConsoleSpanExporter()

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str = __name__):
    return trace.get_tracer(name)


# Convenience tracer for modules to import
ensure_tracing()
tracer = get_tracer("proxy.airsroute_gateway")

