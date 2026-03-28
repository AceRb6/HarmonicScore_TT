from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class InputData(BaseModel):
    value: float

@app.get("/")
def root():
    return {"message": "ML service running"}

@app.post("/analyze")
def analyze(data: InputData):
    # Simulación de procesamiento
    score = data.value * 0.87
    return {"score": score}