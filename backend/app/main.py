from fastapi import FastAPI

from app.api.routes import router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="FansApprove Rating API")
app.include_router(router)
