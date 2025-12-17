from flask import Blueprint
import logging


categories_bp = Blueprint('categories', __name__)

logger = logging.getLogger(__name__)

from . import get_competition_categories

__all__ = ['categories_bp']
