from flask import Blueprint

participants_bp = Blueprint('participants', __name__)

from . import (
    get_participants_list,
    get_team_fees,
    approve_participant,
    save_team_fees,
)

__all__ = ['participants_bp']
