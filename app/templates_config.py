from fastapi.templating import Jinja2Templates
from app.services.quotes import random_quote
from app.services.gallery import random_gallery_thumbs

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["random_quote"] = random_quote
templates.env.globals["random_gallery_thumbs"] = random_gallery_thumbs
