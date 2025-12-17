from flask import Blueprint
import logging

from database import DatabaseManager


scoring_bp = Blueprint('scoring', __name__)

db_manager = DatabaseManager()
logger = logging.getLogger(__name__)

from . import (
    get_participant_scores,
    submit_score,
    get_round_scores,
    get_event_scores,
    get_judge_scores,
    get_scoring_statistics,
    get_scoring_config,
    validate_score,
)

__all__ = ['scoring_bp']
