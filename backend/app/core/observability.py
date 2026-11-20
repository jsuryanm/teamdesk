import logging 

import logfire
from fastapi import FastAPI 
from sqlalchemy.engine import Engine 

from app.core.config import Settings 

_configured = False 

def setup_observability(settings: Settings, engine: Engine) -> None:
    """Configure Logfire once per process (safe to call repeatedly)."""
    global _configured 
    if _configured:
        return 
    is_test = settings.environment == "test"
    
    logfire.configure(
        service_name="teamdesk-api",
        service_version=settings.app_version,
        environment=settings.environment,
        token=settings.logfire_token.get_secret_value(),
        send_to_logfire='if-token-present',
        console=False if is_test else logfire.ConsoleOptions(min_log_level='info'),
        distributed_tracing=True, 
    )

    logfire.instrument_pydantic(record='failure')
    # records validation failures only
    logfire.instrument_sqlalchemy(engine=engine)
    # captures sql query execution, db operation reduction
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logfire.LogfireLoggingHandler()],
        force=True
    )
    _configured = True

def instrument_app(app: FastAPI) -> None:
    """One span per HTTP request, with route, status code and timing."""
    logfire.instrument_fastapi(app,exclude_urls="/health")

