"""Offision API 入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.v1 import auth, users, branches, rooms, reservations, dashboard, categories, roles, equipment, amenities

app = FastAPI(
    title="Offision API",
    version="1.0.0",
    description="M7 組織目錄 + M1 預約管理（房間）— 第一輪 vertical slice",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"
app.include_router(auth.router, prefix=API_V1)
app.include_router(users.router, prefix=API_V1)
app.include_router(users.group_router, prefix=API_V1)
app.include_router(branches.router, prefix=API_V1)
app.include_router(branches.loc_router, prefix=API_V1)
app.include_router(rooms.router, prefix=API_V1)
app.include_router(rooms.blackout_router, prefix=API_V1)
app.include_router(equipment.router, prefix=API_V1)
app.include_router(amenities.router, prefix=API_V1)
app.include_router(reservations.router, prefix=API_V1)
app.include_router(dashboard.router, prefix=API_V1)
app.include_router(categories.router, prefix=API_V1)
app.include_router(roles.router, prefix=API_V1)


@app.get("/health")
def health():
    return {"status": "ok"}
