from fastapi import FastAPI

from settlement.controller import router

app = FastAPI(title="settlement")
app.include_router(router)
