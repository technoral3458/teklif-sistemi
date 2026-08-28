from fastapi.templating import Jinja2Templates
from translations import get_T
from auth import get_impersonator

templates = Jinja2Templates(directory="templates")
templates.env.globals['_T'] = get_T
templates.env.globals['_get_impersonator'] = get_impersonator


def _pending_requests_count():
    try:
        import db.factory as fdb
        del_count = sum(1 for r in fdb.get_deletion_requests(status="pending") if True)
        price_count = fdb.pending_price_requests_count()
        rollback_count = sum(1 for r in fdb.get_stage_rollback_requests(status="pending") if True)
        return del_count + price_count + rollback_count
    except Exception:
        return 0

templates.env.globals['_pending_requests_count'] = _pending_requests_count

def _count_new_quote_requests():
    try:
        import db.factory as fdb
        return fdb.count_new_quote_requests()
    except Exception:
        return 0

templates.env.globals['fdb'] = type('fdb', (), {
    'count_new_quote_requests': staticmethod(_count_new_quote_requests)
})()
