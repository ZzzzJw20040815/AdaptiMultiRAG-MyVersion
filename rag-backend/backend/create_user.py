#!/usr/bin/env python3
"""
创建管理员用户的脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import bcrypt

# 加载环境变量
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

from backend.config.database import DatabaseFactory
from backend.model.user import User


def hash_password(password: str) -> str:
    """密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_admin_user():
    """创建管理员用户"""
    # 用户信息
    username = "admin"
    email = "admin@example.com"
    password = "admin123"
    
    Session = DatabaseFactory.get_session()
    session = Session()
    
    try:
        # 检查用户是否已存在
        existing_user = session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"用户已存在: {existing_user.username} ({existing_user.email})")
            return
        
        # 创建新用户
        hashed_password = hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            is_active=True
        )
        
        session.add(user)
        session.commit()
        
        print("=" * 50)
        print("管理员用户创建成功!")
        print("=" * 50)
        print(f"用户名: {username}")
        print(f"邮箱: {email}")
        print(f"密码: {password}")
        print("=" * 50)
        print("请使用邮箱和密码登录系统")
        
    except Exception as e:
        session.rollback()
        print(f"创建用户失败: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_admin_user()
