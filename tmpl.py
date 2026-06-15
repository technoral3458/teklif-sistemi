from fastapi.templating import Jinja2Templates
from translations import get_T
from auth import get_impersonator

templates = Jinja2Templates(directory="templates")
templates.env.globals['_T'] = get_T
templates.env.globals['_get_impersonator'] = get_impersonator


def _pending_requests_count():
    try:
        import db.factory as fdb
        return sum(1 for r in fdb.get_deletion_requests(status="pending") if True)
    except Exception:
        return 0

templates.env.globals['_pending_requests_count'] = _pending_requests_count
