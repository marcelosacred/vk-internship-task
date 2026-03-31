from fastapi import FastAPI

app = FastAPI(title="Botfarm")


@app.get("/")
async def root():
    return {"message": "botfarm service"}
