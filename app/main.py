from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import resume

app = FastAPI(
    title = "RoleFit App",
    description = "Python Backend",
    Version = "0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)

@app.get("/")
def root():
    return {"RoleFit API is ready"}