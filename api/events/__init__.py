from flask import Blueprint
import logging

from database import DatabaseManager


events_bp = Blueprint('events', __name__)

db_manager = DatabaseManager()
logger = logging.getLogger(__name__)

# 每个具体路由实现在本包下的独立模块中
from . import (
    get_events,
    get_event,
    create_event,
    update_event,
    delete_event,
    register_event,
    get_participants,
    checkin_participant,
    get_event_results,
    publish_event,
    search_events,
    get_events_summary,
    get_structured_events,
)

__all__ = ['events_bp']
