from fastapi.templating import Jinja2Templates
from translations import get_T
from auth import get_impersonator

templates = Jinja2Templates(directory="templates")
templates.env.globals['_T'] = get_T
templates.env.globals['_get_impersonator'] = get_impersonator
