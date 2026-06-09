from ktem.settings_config import app_settings as settings
from sqlalchemy import create_engine

engine = create_engine(settings.KH_DATABASE)
