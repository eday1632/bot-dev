from fastapi import FastAPI
from pydantic import BaseModel
import json

class LevelData(BaseModel):
    enemies: list
    players: list
    hazards: list
    items: list
    game_info: dict
    own_player: dict


app = FastAPI()


@app.get("/")
async def root():
    return ["dash"]

@app.post("/")
async def receive_level_data(level_data: LevelData):
    moves = []
    moves.append({"move_to": level_data.enemies[0]["position"]})
    moves.append("attack")
    return moves