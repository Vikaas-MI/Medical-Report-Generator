from fastapi import FastAPI
from routers.report import router as report_router

app = FastAPI()

app.include_router(report_router)