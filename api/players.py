from flask import Blueprint


players_bp = Blueprint('players', __name__)

# 为保持对外兼容，顶层 api.players 仅作为入口，
# 实际路由实现全部位于 api/players 包中的各个子模块。
from api.players import (  # type: ignore  # noqa: F401
    get_players,
    update_player,
    delete_player,
    add_player,
)

__all__ = ['players_bp']
