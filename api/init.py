# API package initialization
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes after blueprint creation to avoid circular imports
from . import auth, emails, ai
