from flask import Blueprint

players_bp = Blueprint('players', __name__)

# 每个具体路由实现在本包下的独立模块中

from . import (
    get_players,
    update_player,
    delete_player,
    add_player,
)

__all__ = ['players_bp']
