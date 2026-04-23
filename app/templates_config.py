from fastapi.templating import Jinja2Templates
from app.services.quotes import random_quote

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["random_quote"] = random_quote
