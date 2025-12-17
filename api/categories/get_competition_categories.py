from flask import jsonify

from . import categories_bp, logger


@categories_bp.route('/competition', methods=['GET'])
def get_competition_categories():
    """获取比赛项目分类（三级结构）"""
    try:
        categories = {
            "success": True,
            "categories": [
                {
                    "id": "1",
                    "name": "拳术类项目",
                    "icon": "fa-hand-fist",
                    "subcategories": [
                        {
                            "id": "1-1",
                            "name": "（一）客家拳种",
                            "items": [
                                "连城拳", "五枚拳", "朱家教拳", "张家拳", "字门拳", "巫家拳",
                                "刘凤山派", "流民拳", "昆仑拳", "刘家教", "牛家教", "石家拳",
                                "盘龙拳", "五兽拳", "段家拳", "刁家教", "钟家教", "李家教", "岳家教"
                            ],
                            "has_other": True,
                            "other_label": "其他客家拳种"
                        },
                        {
                            "id": "1-2",
                            "name": "（二）传统太极拳",
                            "items": [
                                "太极（八法五步）", "24式太极拳", "42式太极拳", "陈式太极拳",
                                "杨式太极拳", "吴式太极拳", "武式太极拳", "孙式太极拳"
                            ],
                            "has_other": True,
                            "other_label": "其他传统太极拳"
                        },
                        {
                            "id": "1-3",
                            "name": "（三）传统南拳",
                            "items": [
                                "五祖拳", "永春白鹤拳", "咏春拳", "太祖拳"
                            ],
                            "has_other": True,
                            "other_label": "其他传统南拳"
                        },
                        {
                            "id": "1-4",
                            "name": "（四）单项拳种",
                            "items": [
                                "少林拳", "七星拳", "连环拳", "八极拳", "六合拳", "通臂拳",
                                "查拳", "象形拳"
                            ],
                            "has_other": True,
                            "other_label": "其他单项拳种"
                        },
                        {
                            "id": "1-5",
                            "name": "（五）规定拳术",
                            "items": [
                                "长拳第1-3套", "南拳第1-3套", "太极拳第1-3套",
                                "初级长拳第1-3套", "初级南拳", "初级太极拳",
                                "太极拳第1-3套国际竞赛规定套路"
                            ],
                            "has_other": True,
                            "other_label": "其他规定拳术"
                        },
                        {
                            "id": "1-6",
                            "name": "（六）形意拳",
                            "items": [
                                "形意五行拳", "形意十二形拳", "形意综合拳"
                            ],
                            "has_other": True,
                            "other_label": "其他形意拳"
                        },
                        {
                            "id": "1-7",
                            "name": "（七）八卦掌",
                            "items": [
                                "八卦掌基础套路", "八卦游龙掌", "八卦连环掌"
                            ],
                            "has_other": True,
                            "other_label": "其他八卦掌"
                        }
                    ]
                },
                {
                    "id": "2",
                    "name": "器械类项目",
                    "icon": "fa-sword",
                    "subcategories": [
                        {
                            "id": "2-1",
                            "name": "（一）客家器械",
                            "items": [
                                "连城拳器械", "五枚拳器械", "朱家教拳器械", "张家拳器械",
                                "字门拳器械", "巫家拳器械", "刘凤山派器械", "流民拳器械",
                                "昆仑拳器械", "刘家教器械", "牛家教器械", "石家拳器械",
                                "盘龙拳器械", "五兽拳器械", "段家拳器械", "刁家教器械",
                                "钟家教器械", "李家教器械", "岳家教器械"
                            ],
                            "has_other": True,
                            "other_options": [
                                {"label": "其它客家长器械", "key": "other1"},
                                {"label": "其它客家短器械", "key": "other2"},
                                {"label": "客家双器械", "key": "other3"}
                            ]
                        },
                        {
                            "id": "2-2",
                            "name": "（二）太极器械",
                            "items": [
                                "32式太极剑", "42式太极剑", "传统太极剑", "传统太极刀",
                                "传统太极枪", "传统太极扇"
                            ],
                            "has_other": True,
                            "other_options": [
                                {"label": "其他太极长器械", "key": "other1"},
                                {"label": "其他太极短器械", "key": "other2"}
                            ]
                        },
                        {
                            "id": "2-3",
                            "name": "（三）南拳器械",
                            "items": [
                                "传统南刀", "传统南棍"
                            ],
                            "has_other": True,
                            "other_options": [
                                {"label": "其他南短器械", "key": "other1"},
                                {"label": "其他南长器械", "key": "other2"},
                                {"label": "其他南双器械", "key": "other3"}
                            ]
                        },
                        {
                            "id": "2-4",
                            "name": "（四）传统器械",
                            "items": [
                                "传统刀术", "传统剑术", "传统棍术",
                                "传统大刀（含朴刀、青龙大刀、关刀）",
                                "传统扇子", "传统匕首", "传统棒（含鞭杆、杖、拐）",
                                "形意棍", "阴手棍"
                            ],
                            "has_other": True,
                            "other_options": [
                                {"label": "其他短器械", "key": "other1"},
                                {"label": "其他长器械", "key": "other2"},
                                {"label": "其他双器械", "key": "other3"},
                                {"label": "其他软器械", "key": "other4"}
                            ]
                        },
                        {
                            "id": "2-5",
                            "name": "（五）规定器械",
                            "items": [
                                "自选刀术", "自选枪术", "自选剑术", "自选棍术",
                                "自选南刀", "自选南棍", "初级刀术", "初级剑术",
                                "初级棍术", "初级枪术", "太极剑第1-3套国际竞赛规定套路"
                            ],
                            "has_other": True,
                            "other_options": [
                                {"label": "其他规定短器械", "key": "other1"},
                                {"label": "其他规定长器械", "key": "other2"}
                            ]
                        }
                    ]
                }
            ]
        }

        return jsonify(categories)

    except Exception as e:
        logger.error(f"获取项目分类失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取项目分类失败'
        }), 500
