from database import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    cursor = conn.cursor()
    
    # 检查API查询中使用的所有字段
    required_fields = [
        'team_name', 'event_name', 'leader_name', 
        'individual_fee', 'pair_practice_fee', 'team_competition_fee',
        'other_fee', 'total_fee'
    ]
    
    cursor.execute("DESCRIBE team_applications")
    columns = [col[0] for col in cursor.fetchall()]
    
    print('team_applications表字段:')
    for field in required_fields:
        if field in columns:
            print(f'  ✓ {field}')
        else:
            print(f'  ✗ {field} (缺失)')
    
    # 检查是否有类似的字段
    print('\n表中实际存在的相关字段:')
    for col in columns:
        if any(field in col for field in ['name', 'fee', 'leader']):
            print(f'  {col}')