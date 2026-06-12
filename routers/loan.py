from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import db.factory as fdb
import auth

router = APIRouter(prefix="/loan-calc")
from tmpl import templates


@router.get("")
async def loan_calc(request: Request):
    user = auth.require_user(request)
    rates = fdb.get_loan_rates(active_only=False)
    return templates.TemplateResponse(request, "loan_calc.html", {
        "user": user,
        "rates": rates,
        "active_page": "loan",
    })


@router.post("/rate/save")
async def save_rate(request: Request,
                    id: int = Form(0),
                    plan_name: str = Form("Standart"),
                    grace_months: int = Form(0),
                    term_months: int = Form(12),
                    rate_tl: float = Form(0.0),
                    rate_usd: float = Form(0.0),
                    rate_eur: float = Form(0.0),
                    file_fee_pct: float = Form(0.5),
                    is_active: int = Form(1)):
    auth.require_admin(request)
    fdb.save_loan_rate(
        id=id or None,
        plan_name=plan_name.strip(),
        grace_months=grace_months,
        term_months=term_months,
        rate_tl=rate_tl,
        rate_usd=rate_usd,
        rate_eur=rate_eur,
        file_fee_pct=file_fee_pct,
        is_active=is_active,
    )
    return RedirectResponse("/loan-calc", 303)


@router.post("/rate/delete")
async def delete_rate(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    fdb.del_loan_rate(id)
    return RedirectResponse("/loan-calc", 303)
