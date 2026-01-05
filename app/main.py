from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.db import engine, Base
from .api.routes.auth import router as auth_router
from .api.routes.users import router as users_router
from .api.routes.chat import router as chat_router
from .api.routes.misc import router as misc_router
from .api.routes.feedback import router as feedback_router

app = FastAPI(title="Deterministic MH Screening Platform", version="v6.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.include_router(misc_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(chat_router)
app.include_router(feedback_router)
