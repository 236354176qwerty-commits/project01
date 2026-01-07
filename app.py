from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, g
from werkzeug.utils import secure_filename
import os
import sys
import json
from datetime import datetime
import time
from user_manager import user_manager
import re
from dotenv import load_dotenv
from utils.excel_handler import ExcelHandler
from io import BytesIO
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

from config import config as config_map
from models import UserRole, UserStatus
from database import DatabaseManager
#测试
from api.account import auth_bp, users_bp
from api.competition import events_bp, teams_bp, players_bp, participants_bp
from api.communication import announcements_bp, notifications_bp
from api.maintenance import maintenance_bp
from api.dashboard import dashboard_bp


def create_app():
    app = Flask(__name__)
    env_name = os.environ.get('APP_ENV', 'default').lower()
    app.config.from_object(config_map.get(env_name, config_map['default']))

    if env_name == 'production' and not app.config.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY environment variable is required in production')

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.before_request
    def start_request_timer():
        g.request_start_time = time.perf_counter()

    @app.after_request
    def log_request_time(response):
        start_time = getattr(g, 'request_start_time', None)
        if start_time is not None:
            duration_ms = (time.perf_counter() - start_time) * 1000
            app.logger.info(
                "Request %s %s took %.2fms, status %d",
                request.method,
                request.path,
                duration_ms,
                response.status_code,
            )
        return response

    # 应用启动时进行一次数据库结构检查与迁移（只增量修复，不重建）
    try:
        db_manager = DatabaseManager()
        db_manager.init_database(force_recreate=False)
        app.logger.info("数据库初始化成功")
    except Exception as e:
        # 记录错误但不阻止应用启动，避免因迁移问题直接中断服务
        app.logger.error(f"数据库初始化检查失败: {e}")
        # 如果是连接限制错误，等待一段时间后重试
        if "max_user_connections" in str(e):
            app.logger.warning("检测到数据库连接限制，等待30秒后重试...")
            time.sleep(30)
            try:
                db_manager.init_database(force_recreate=False)
                app.logger.info("数据库重试初始化成功")
            except Exception as retry_e:
                app.logger.error(f"数据库重试初始化失败: {retry_e}")

    @app.before_request
    def check_user_status():
        path = request.path or ''

        if (
            path.startswith('/static')
            or path in [
                '/login', 
                '/register', 
                '/api/auth/login', 
                '/api/auth/register', 
                '/api/auth/logout', 
                '/favicon.ico', 
            ]
        ):
            return

        username = session.get('username')
        if not username:
            return

        try:
            last_check = session.get('user_status_last_check')
            now_ts = time.time()
            interval = app.config.get('USER_STATUS_CHECK_INTERVAL', 10)
            if isinstance(last_check, (int, float)) and now_ts - last_check < interval:
                return

            # 使用 user_manager 复用用户缓存/管理逻辑，避免每次都直接打数据库
            user = user_manager.get_user(username)

            if user and not user.can_login():
                session.clear()
                if path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'message': '账号状态异常或被冻结，已登出，请联系管理员。', 
                        'status': user.status.value,
                        'status_display': user.get_status_display(),
                        'force_logout': True,
                    })
                else:
                    flash('账号状态异常或被冻结，请联系管理员。', 'error')
                    return redirect(url_for('login'))

            if user and user.can_login():
                session['user_status_last_check'] = now_ts

        except Exception:
            session.clear()
            if path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'message': '会话校验失败，请重新登录。',
                    'force_logout': True,
                })
            else:
                flash('会话校验失败，请重新登录。', 'error')
                return redirect(url_for('login'))

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api/events')
    app.register_blueprint(teams_bp, url_prefix='/api')
    app.register_blueprint(players_bp, url_prefix='/api')
    app.register_blueprint(participants_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(notifications_bp, url_prefix='/api')
    app.register_blueprint(announcements_bp, url_prefix='/api')
    app.register_blueprint(maintenance_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')

    from api.competition import categories_bp

    app.register_blueprint(categories_bp, url_prefix='/api/categories')

    return app


app = create_app()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    next_url = request.args.get('next', '')
    return render_template('login.html', next_url=next_url)

@app.route('/register')
def register():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/events')
def events():
    return render_template('events.html')

@app.route('/participants')
def participants():
    return render_template('participants.html')

@app.route('/checkin')
def checkin():
    return render_template('checkin.html')

@app.route('/results')
def results():
    user_role = session.get('user_role', 'user')
    return render_template('results.html', user_role=user_role)


@app.route('/team_review_list')
def team_review_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        flash('NO_PERMISSION', 'error')
        return redirect(url_for('dashboard'))

    return render_template('team_review_list.html')

@app.route('/send_notification')
def send_notification():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
        flash('NO_PERMISSION', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('send_notification.html')

@app.route('/notifications')
def notifications():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template('notifications.html')

@app.route('/user_management')
def user_management():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_role = session.get('user_role')
    if user_role not in ['super_admin', 'admin']:
        flash('NO_PERMISSION', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('user_management.html', 
                         user_role=user_role,
                         user_name=session.get('user_name'))

@app.route('/team_profile')
def team_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('team_profile.html')

@app.route('/my_certificates')
def my_certificates():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('participant_overview.html')


@app.route('/participant_overview')
def participant_overview():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name', '')
    return render_template('participant_overview.html', event_id=event_id, event_name=event_name)


@app.route('/data_summary')
def data_summary():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name', '')

    user_id = session.get('user_id')
    is_team_leader = False
    if user_id:
        try:
            db_manager = DatabaseManager()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM team_applications
                    WHERE user_id = %s AND status IN ('pending', 'approved')
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                if row is not None:
                    count = row[0] if isinstance(row, tuple) else list(row.values())[0]
                    is_team_leader = bool(count and count > 0)
        except Exception as e:
            print(f"检查领队身份失败: {e}")
            is_team_leader = False

    event_info = {
        'id': event_id,
        'name': event_name,
    }

    return render_template('data_summary.html', event=event_info, is_team_leader=is_team_leader)


@app.route('/event_registration')
def event_registration():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name', '')
    event_type = request.args.get('event_type', '')

    return render_template('event_registration.html',
                           event_id=event_id,
                           event_name=event_name,
                           event_type=event_type)

@app.route('/event_selection')
def event_selection():
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.url))
    return render_template('event_selection.html')

@app.route('/select_event')
def select_event_legacy():
    return redirect(url_for('event_selection'))

@app.route('/staff_registration')
def staff_registration():
    return redirect(url_for('add_staff'))

@app.route('/add_staff')
def add_staff():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('add_staff.html')

@app.route('/add_staff_direct')
def add_staff_direct():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name')
    
    if not event_id or not event_name:
        return redirect(url_for('event_selection', source='staff_list'))
    
    return render_template('add_staff_direct.html', 
                         event_id=event_id, 
                         event_name=event_name)

@app.route('/staff_list')
def staff_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name')
    source = request.args.get('source')
    
    return render_template('staff_list.html', 
                         event_id=event_id, 
                         event_name=event_name,
                         source=source)

@app.route('/player_list')
def player_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name')
    
    return render_template('player_list.html', 
                         event_id=event_id, 
                         event_name=event_name)

@app.route('/player_registration_list')
def player_registration_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name')
    source = request.args.get('source')

    return render_template('player_registration_list.html',
                         event_id=event_id,
                         event_name=event_name,
                         source=source)

@app.route('/add_player')
def add_player():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    event_id = request.args.get('event_id')
    event_name = request.args.get('event_name')
    
    if not event_id or not event_name:
        return redirect(url_for('event_selection', source='player_list'))
    
    return render_template('add_player.html', 
                         event_id=event_id, 
                         event_name=event_name)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


@app.context_processor
def inject_user():
    current_user_display = session.get('user_name')
    user_role = session.get('user_role')
    user_role_display = session.get('user_role_display')

    # 如果未显式设置中文展示名称，则根据角色编码生成默认中文名称
    if not user_role_display and user_role:
        role_display_map = {
            'super_admin': '超级管理员',
            'admin': '管理员',
            'judge': '裁判',
            'user': '普通用户',
        }
        user_role_display = role_display_map.get(user_role, user_role)

    return dict(
        current_user=current_user_display,
        user_role=user_role,
        user_role_display=user_role_display,
        is_logged_in=session.get('logged_in', False)
    )

if __name__ == '__main__':
    try:
        os.makedirs('uploads', exist_ok=True)
        
        app.run(
            host=app.config.get('HOST', '0.0.0.0'),
            port=app.config.get('PORT', 5000),
            debug=app.config.get('DEBUG', True)
        )
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        sys.exit(1)
