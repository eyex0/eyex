from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import get_settings

logger = logging.getLogger(__name__)


def setup_telemetry(app) -> None:
    settings = get_settings()
    otlp_endpoint = settings.otlp_endpoint

    resource = Resource.create({
        "service.name": settings.app_name.lower().replace(" ", "-"),
        "service.version": settings.app_version,
        "deployment.environment": "production" if not settings.app_debug else "development",
    })

    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("OpenTelemetry OTLP exporter configured at %s", otlp_endpoint)

    if settings.app_debug or not otlp_endpoint:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("OpenTelemetry console exporter configured")

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    logger.info("OpenTelemetry FastAPI instrumentation applied")
