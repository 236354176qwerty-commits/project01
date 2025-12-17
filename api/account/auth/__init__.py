from flask import Blueprint
import logging

from database import DatabaseManager


auth_bp = Blueprint('auth', __name__)

db_manager = DatabaseManager()
logger = logging.getLogger(__name__)

from . import (
    login,
    logout,
    register,
    get_profile,
    update_profile,
    change_password,
    check_session,
    generate_captcha,
    debug_captcha,
    test_captcha,
    send_verification_code,
    verify_code,
    reset_password,
)

__all__ = ['auth_bp']
