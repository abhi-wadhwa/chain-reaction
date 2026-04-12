from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes_agents import router as agents_router
from api.routes_game import router as game_router
from api.routes_tournament import router as tournament_router
from api.routes_training import router as training_router
from api.ws_live import router as ws_router

app = FastAPI(title="Chain Reaction AI Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(game_router)
app.include_router(tournament_router)
app.include_router(training_router)
app.include_router(ws_router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Chain Reaction AI Platform", "version": "2.0.0"}
