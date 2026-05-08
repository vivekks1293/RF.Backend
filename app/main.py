from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import jobs, resume, tailor

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
app.include_router(jobs.router) 
app.include_router(tailor.router)

@app.get("/")
def root():
    return {"RoleFit API is ready"}