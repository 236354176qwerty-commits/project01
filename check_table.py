from database import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE 'team_applications'")
    result = cursor.fetchone()
    if result:
        print('team_applications表存在')
        cursor.execute("DESCRIBE team_applications")
        columns = cursor.fetchall()
        print('表结构:')
        for col in columns:
            print(f'  {col[0]} - {col[1]}')
    else:
        print('team_applications表不存在')