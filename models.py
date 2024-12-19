from datetime import datetime
import sqlite3
import random
import os

class UserDB:
    def __init__(self):
        self.db_path = 'users.db'
        # 确保数据库文件所在目录存在
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,     -- 用户名
                password TEXT,                 -- 密码
                register_time TEXT,            -- 注册时间
                free_uses INTEGER DEFAULT 0,   -- 免费使用次数
                referred_by TEXT,              -- 推荐人的用户名
                FOREIGN KEY (referred_by) REFERENCES users(username)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register(self, username, password, referred_by=None):
        """注册用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户是否已存在
            cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                conn.close()
                return False, "用户名已存在"
            
            if referred_by:
                # 验证推荐人是否存在
                cursor.execute('SELECT username FROM users WHERE username = ?', (referred_by,))
                referrer = cursor.fetchone()
                if not referrer:
                    conn.close()
                    return False, "推荐人不存在"
                    
                # 给推荐人增加20次免费使用机会
                cursor.execute('''
                    UPDATE users 
                    SET free_uses = free_uses + 20 
                    WHERE username = ?
                ''', (referred_by,))
                
                # 注册新用户
                cursor.execute('''
                    INSERT INTO users (username, password, register_time, referred_by)
                    VALUES (?, ?, ?, ?)
                ''', (username, password, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), referred_by))
            else:
                # 注册新用户（无推荐）
                cursor.execute('''
                    INSERT INTO users (username, password, register_time)
                    VALUES (?, ?, ?)
                ''', (username, password, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            return True, "注册成功"
            
        except Exception as e:
            print(f"注册失败: {str(e)}")
            return False, f"注册失败: {str(e)}"
    
    def login(self, username, password):
        """用户登录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if not result:
                return False, "用户不存在"
            
            if password != result[0]:
                return False, "密码错误"
            
            return True, "登录成功"
            
        except Exception as e:
            print(f"登录失败: {str(e)}")
            return False, f"登录失败: {str(e)}"
    
    def get_user_info(self, username):
        """获取用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, free_uses 
                FROM users WHERE username = ?
            ''', (username,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'username': result[0],
                    'free_uses': result[1]
                }
            return None
            
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return None
    
    def use_free_chance(self, username):
        """使用一次免费机会"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT free_uses FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                cursor.execute('''
                    UPDATE users 
                    SET free_uses = free_uses - 1 
                    WHERE username = ?
                ''', (username,))
                conn.commit()
                return True
                
            return False
            
        except Exception as e:
            print(f"使用免费次数失败: {str(e)}")
            return False