from fastapi.templating import Jinja2Templates
from translations import get_T

templates = Jinja2Templates(directory="templates")
templates.env.globals['_T'] = get_T
