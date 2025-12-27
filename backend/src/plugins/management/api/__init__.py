from flask import Blueprint

bp = Blueprint('management', __name__, url_prefix='/management')
import src.plugins.management.api.test
