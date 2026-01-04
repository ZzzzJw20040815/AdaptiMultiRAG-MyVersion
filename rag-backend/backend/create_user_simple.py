#!/usr/bin/env python3
"""
简单的用户创建脚本 - 直接使用 PyMySQL
"""
import bcrypt
import pymysql

# 数据库连接配置 (来自 docker-compose-full.yml)
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'password',
    'database': 'rag_db',
    'charset': 'utf8mb4'
}

# 用户信息
USERNAME = 'admin'
EMAIL = 'admin@example.com'
PASSWORD = 'admin123'


def create_user():
    """创建用户"""
    # 生成密码哈希
    password_hash = bcrypt.hashpw(PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print(f"生成的密码哈希: {password_hash}")
    
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT id, username, email FROM users WHERE username = %s OR email = %s", (USERNAME, EMAIL))
            existing = cursor.fetchone()
            
            if existing:
                print(f"用户已存在: id={existing[0]}, username={existing[1]}, email={existing[2]}")
                # 更新密码
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s OR email = %s",
                    (password_hash, USERNAME, EMAIL)
                )
                connection.commit()
                print("已更新密码哈希!")
            else:
                # 插入新用户
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, is_active) VALUES (%s, %s, %s, %s)",
                    (USERNAME, EMAIL, password_hash, 1)
                )
                connection.commit()
                print("新用户创建成功!")
            
            # 验证
            cursor.execute("SELECT id, username, email, password_hash, is_active FROM users WHERE email = %s", (EMAIL,))
            user = cursor.fetchone()
            
            print("\n" + "=" * 50)
            print("用户信息:")
            print("=" * 50)
            print(f"ID: {user[0]}")
            print(f"用户名: {user[1]}")
            print(f"邮箱: {user[2]}")
            print(f"密码哈希长度: {len(user[3])}")
            print(f"是否激活: {user[4]}")
            print("=" * 50)
            print(f"\n登录信息:")
            print(f"邮箱: {EMAIL}")
            print(f"密码: {PASSWORD}")
            print("=" * 50)
            
    finally:
        connection.close()


if __name__ == "__main__":
    create_user()
