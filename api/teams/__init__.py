from flask import Blueprint

teams_bp = Blueprint('teams', __name__)

# 这里仅定义 Blueprint，本包下的各个路由文件会通过导入附加到 teams_bp 上

# 导入所有具体路由模块（每个文件一个 API）
from . import (
    get_teams_by_event,
    create_team,
    update_or_delete_team,
    get_team_details,
    get_my_team_for_event,
    get_my_teams_for_event,
    get_my_created_teams,
    team_draft,
    get_team_players,
    add_team_player,
    update_team_player,
    delete_team_player,
    get_my_team_applications,
    get_team_applications,
    review_team_application,
    cancel_team_application,
    get_team_staff,
    delete_team_staff,
    submit_team_info,
    add_team_staff,
    update_team_staff,
    export_team_info,
)

__all__ = ['teams_bp']
