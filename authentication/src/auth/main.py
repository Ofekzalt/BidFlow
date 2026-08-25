from fastapi import FastAPI

from auth.controller import router
from auth.exception import AuthError, auth_error_handler

app = FastAPI(title="authentication")
app.add_exception_handler(AuthError, auth_error_handler)
app.include_router(router)
