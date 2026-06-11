import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

import db.users as udb
import db.factory as fdb
import auth
from config import BASE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "img", "uploads"), exist_ok=True)
    udb.init()
    fdb.init()
    yield


app = FastAPI(title="B2B Teklif Sistemi", version="3.0.0", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

from routers.auth_router import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.customers import router as customers_router
from routers.categories import router as categories_router
from routers.models import router as models_router
from routers.options import router as options_router
from routers.offers import router as offers_router
from routers.orders import router as orders_router
from routers.ledger import router as ledger_router
from routers.costs import router as costs_router
from routers.dealers import router as dealers_router
from routers.manufacturers import router as manufacturers_router
from routers.profile import router as profile_router
from routers.admin_router import router as admin_router

for r in [
    auth_router,
    dashboard_router,
    customers_router,
    categories_router,
    models_router,
    options_router,
    offers_router,
    orders_router,
    ledger_router,
    costs_router,
    dealers_router,
    manufacturers_router,
    profile_router,
    admin_router,
]:
    app.include_router(r)


from fastapi import Form as _Form
from fastapi.responses import RedirectResponse as _Redir
from db.users import update_profile as _upd_profile


@app.post("/set-lang")
async def set_lang(request: Request, lang: str = _Form("tr")):
    user = auth.require_user(request)
    _upd_profile(user["id"], lang=lang)
    return _Redir(request.headers.get("referer", "/"), 303)


@app.exception_handler(302)
async def redirect_handler(request: Request, exc):
    return RedirectResponse(url=exc.headers["Location"], status_code=302)
