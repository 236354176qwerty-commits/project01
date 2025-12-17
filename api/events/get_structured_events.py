from flask import jsonify

from database import DatabaseManager
from utils.decorators import login_required, log_action, handle_db_errors

from . import events_bp, logger


@events_bp.route('/structured', methods=['GET'])
@login_required
@log_action('获取结构化赛事分类')
@handle_db_errors
def get_structured_events():
    """获取结构化的赛事分类数据
    返回传统项目、自选和规定项目、对练项目三个大类别的赛事结构，以及最新赛事
    从数据库动态获取赛事数据，实现实时更新
    """
    try:
        # 定义赛事分类结构 - 按用户需求排序：最新赛事(1)、传统项目(2)、自选和规定项目(3)、对练项目(4)
        event_structure = {
            'latest_events': {
                'name': '最新赛事',
                'sub_categories': {
                    'recent_events': {
                        'name': '近期赛事',
                        'events': [],  # 将从数据库动态填充
                    },
                    'hot_events': {
                        'name': '热门赛事',
                        'events': [],  # 将从数据库动态填充
                    },
                },
            },
            'traditional': {
                'name': '传统项目',
                'sub_categories': {
                    'traditional_boxing': {
                        'name': '拳术',
                        'sub_categories': {
                            'hakka_boxing': {
                                'name': '客家拳术',
                                'events': [],  # 将从数据库动态填充
                            },
                            'traditional_boxing_sub': {
                                'name': '传统拳术',
                                'sub_categories': {
                                    'taiji_boxing': {
                                        'name': '太极拳类',
                                        'events': [],  # 将从数据库动态填充
                                    },
                                    'nanquan_boxing': {
                                        'name': '南拳类',
                                        'events': [],  # 将从数据库动态填充
                                    },
                                    'other_traditional_boxing': {
                                        'name': '其他拳术类',
                                        'events': [],  # 将从数据库动态填充
                                    },
                                },
                            },
                        },
                    },
                    'traditional_weapons': {
                        'name': '器械',
                        'sub_categories': {
                            'hakka_weapons': {
                                'name': '客家器械',
                                'events': [],  # 将从数据库动态填充
                            },
                            'traditional_weapons_sub': {
                                'name': '传统器械',
                                'sub_categories': {
                                    'soft_weapons': {
                                        'name': '软器械',
                                        'events': [],  # 将从数据库动态填充
                                    },
                                    'single_weapons': {
                                        'name': '单器械',
                                        'events': [],  # 将从数据库动态填充
                                    },
                                    'double_weapons': {
                                        'name': '双器械',
                                        'events': [],  # 将从数据库动态填充
                                    },
                                },
                            },
                        },
                    },
                },
            },
            'optional_standard': {
                'name': '自选和规定项目',
                'sub_categories': {
                    'optional_routines': {
                        'name': '自选项目',
                        'events': [],  # 将从数据库动态填充
                    },
                    'standard_routines': {
                        'name': '规定项目',
                        'events': [],  # 将从数据库动态填充
                    },
                },
            },
            'dueling': {
                'name': '对练项目',
                'sub_categories': {},
            },
        }
        
        # 首先使用默认数据作为后备，确保即使数据库查询失败也能显示内容
        # 太极拳类默认数据
        taiji_boxing_events = [
            {'event_id': 1, 'name': '陈式太极拳'},
            {'event_id': 2, 'name': '杨式太极拳'},
            {'event_id': 3, 'name': '吴式太极拳'},
            {'event_id': 4, 'name': '武式太极拳'},
            {'event_id': 5, 'name': '孙式太极拳'},
            {'event_id': 6, 'name': '其它太极拳种'},
        ]
        
        # 南拳类默认数据
        nanquan_boxing_events = [
            {'event_id': 7, 'name': '五祖拳'},
            {'event_id': 8, 'name': '太祖拳'},
            {'event_id': 9, 'name': '永春白鹤拳'},
            {'event_id': 10, 'name': '咏春拳'},
            {'event_id': 111, 'name': '金鹰拳'},
            {'event_id': 112, 'name': '香店拳'},
            {'event_id': 113, 'name': '地术拳'},
            {'event_id': 114, 'name': '罗汉拳'},
            {'event_id': 115, 'name': '达尊拳'},
            {'event_id': 116, 'name': '其它南拳种'},
        ]
        
        # 其他拳术类默认数据
        other_traditional_boxing_events = [
            {'event_id': 35, 'name': '少林拳'},
            {'event_id': 36, 'name': '七星拳'},
            {'event_id': 37, 'name': '连环拳'},
            {'event_id': 38, 'name': '八极拳'},
            {'event_id': 39, 'name': '六合拳'},
            {'event_id': 40, 'name': '通臂拳'},
            {'event_id': 41, 'name': '查拳'},
            {'event_id': 42, 'name': '象形拳'},
            {'event_id': 43, 'name': '其他单项拳种传统拳术'},
        ]
        
        # 设置默认数据
        event_structure['traditional']['sub_categories']['traditional_boxing']['sub_categories']['traditional_boxing_sub']['sub_categories']['taiji_boxing']['events'] = taiji_boxing_events
        event_structure['traditional']['sub_categories']['traditional_boxing']['sub_categories']['traditional_boxing_sub']['sub_categories']['nanquan_boxing']['events'] = nanquan_boxing_events
        event_structure['traditional']['sub_categories']['traditional_boxing']['sub_categories']['traditional_boxing_sub']['sub_categories']['other_traditional_boxing']['events'] = other_traditional_boxing_events
        
        # 尝试从数据库获取赛事数据（如果失败也不会影响默认数据的显示）
        try:
            with DatabaseManager() as db:
                # 获取所有赛事
                all_events = db.execute_query("SELECT event_id, name, category FROM events ORDER BY event_id")
                
                if all_events:
                    logger.info(f'从数据库获取到 {len(all_events)} 个赛事')
                    
                    # 定义分类映射关系
                    category_mapping = {
                        # 太极拳类
                        '陈式太极拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'taiji_boxing'),
                        '杨式太极拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'taiji_boxing'),
                        '吴式太极拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'taiji_boxing'),
                        '武式太极拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'taiji_boxing'),
                        '孙式太极拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'taiji_boxing'),
                        '其它太极拳种': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'taiji_boxing'),
                        
                        # 南拳类
                        '五祖拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '太祖拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '永春白鹤拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '咏春拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '金鹰拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '香店拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '地术拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '罗汉拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '达尊拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        '其它南拳种': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'nanquan_boxing'),
                        
                        # 其他拳术类
                        '少林拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '七星拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '连环拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '八极拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '六合拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '通臂拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '查拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '象形拳': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                        '其他单项拳种传统拳术': ('traditional', 'traditional_boxing', 'traditional_boxing_sub', 'other_traditional_boxing'),
                    }
                    
                    # 重置相关分类的events列表，准备从数据库填充
                    event_structure['traditional']['sub_categories']['traditional_boxing']['sub_categories']['traditional_boxing_sub']['sub_categories']['taiji_boxing']['events'] = []
                    event_structure['traditional']['sub_categories']['traditional_boxing']['sub_categories']['traditional_boxing_sub']['sub_categories']['nanquan_boxing']['events'] = []
                    event_structure['traditional']['sub_categories']['traditional_boxing']['sub_categories']['traditional_boxing_sub']['sub_categories']['other_traditional_boxing']['events'] = []
                    
                    # 填充赛事到对应的分类中
                    for event in all_events:
                        event_id = event['event_id']
                        event_name = event['name']
                        
                        # 检查是否在映射中
                        if event_name in category_mapping:
                            cat_path = category_mapping[event_name]
                            
                            # 安全地导航到目标分类
                            current_level = event_structure
                            for i, cat_key in enumerate(cat_path):
                                if cat_key in current_level:
                                    current_level = current_level[cat_key]
                                    # 如果不是最后一级且有sub_categories，则继续向下
                                    if i < len(cat_path) - 1 and 'sub_categories' in current_level:
                                        current_level = current_level['sub_categories']
                                else:
                                    break
                            
                            # 添加赛事到目标节点
                            if 'events' in current_level:
                                current_level['events'].append({'event_id': event_id, 'name': event_name})
        except Exception as db_error:
            logger.error(f'从数据库获取赛事数据失败: {str(db_error)}')
            # 继续使用默认数据
        
        return jsonify({
            'success': True,
            'data': event_structure,
        })
        
    except Exception as e:
        logger.error(f'获取结构化赛事分类失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取结构化赛事分类失败: {str(e)}',
        }), 500
