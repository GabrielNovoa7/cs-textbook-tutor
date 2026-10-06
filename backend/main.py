from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "CS Textbook Tutor API is running"}