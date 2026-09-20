from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
# In-memory counters: fine for a single waitress process, reset on restart.
# No default limits; only routes decorated with @limiter.limit are throttled.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
