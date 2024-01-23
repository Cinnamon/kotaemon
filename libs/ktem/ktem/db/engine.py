from sqlmodel import create_engine
from theflow.settings import settings

engine = create_engine(settings.KH_DATABASE)
