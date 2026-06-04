from sqlalchemy import create_engine
from ktem.settings_config import app_settings as settings

engine = create_engine(settings.KH_DATABASE)
