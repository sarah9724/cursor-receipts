from datetime import datetime
import sqlite3
import random
import os
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from config import current_config, ENV
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class UserDB:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = 'users.db'
            self.connection_lock = Lock()
            self.init_db()
            if current_config['enabled']:
                self.sms_client = AcsClient(
                    current_config['access_key_id'],
                    current_config['access_key_secret'],
                    'cn-hangzhou'
                )
            self.initialized = True
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query, params=None):
        """执行数据库查询的通用方法"""
        with self.connection_lock:
            conn = None
            cursor = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                result = cursor.fetchall()  # 获取所有结果
                return result
            except Exception as e:
                if conn:
                    conn.rollback()
                raise e
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
    
    def send_code(self, phone):
        """发送验证码（测试版本：使用固定验证码）- 保留此方法以兼容旧代码，但不再使用"""
        try:
            # 使用固定验证码 123456
            code = '123456'
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 直接返回固定验证码
            logger.info(f"测试验证码 - 手机号: {phone}, 验证码: {code}")
            return True, f"验证码: {code}"
                
        except Exception as e:
            logger.error(f"发送验证码失败: {str(e)}")
            return False, f"发送失败: {str(e)}"
    
    def verify_code(self, phone, code, password=None, referred_by=None):
        """验证码验证并注册 - 保留此方法以兼容旧代码，但不再使用"""
        try:
            logger.info("\n=== 开始验证码验证和注册流程 ===")
            logger.info(f"注册手机号: {phone}")
            logger.info(f"推荐人手机号: {referred_by}")
            
            # 检查验证码是否为固定验证码
            if code != '123456':
                return False, "验证码错误"
            
            # 检查用户是否已注册
            result = self.execute_query(
                'SELECT phone FROM users WHERE phone = ?',
                (phone,)
            )
            
            if result:
                # 用户已存在，检查是否已设置密码
                user_data = result[0]
                existing_result = self.execute_query(
                    'SELECT password FROM users WHERE phone = ?',
                    (phone,)
                )
                if existing_result and existing_result[0][0]:
                    return False, "该手机号已注册"
                    
                # 如果用户存在但没有密码，更新用户信息
                self.execute_query('''
                    UPDATE users SET 
                        password = ?,
                        register_time = ?,
                        referred_by = ?
                    WHERE phone = ?
                ''', (password, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), referred_by, phone))
            else:
                # 用户不存在，创建新用户
                self.execute_query('''
                    INSERT INTO users (phone, password, register_time, referred_by, free_uses)
                    VALUES (?, ?, ?, ?, 0)
                ''', (phone, password, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), referred_by))
            
            # 处理推荐人逻辑
            if referred_by:
                # 验证推荐人是否存在且已注册
                ref_result = self.execute_query(
                    'SELECT phone FROM users WHERE phone = ? AND password IS NOT NULL',
                    (referred_by,)
                )
                
                if ref_result:
                    # 给推荐人增加免费次数
                    self.execute_query(
                        'UPDATE users SET free_uses = free_uses + 20 WHERE phone = ?',
                        (referred_by,)
                    )
            
            return True, "注册成功"
            
        except Exception as e:
            logger.error(f"验证失败: {str(e)}")
            return False, f"验证失败: {str(e)}"
    
    def register(self, phone, email, password, referred_by=None):
        """用户注册"""
        try:
            # 检查用户是否已注册
            result = self.execute_query(
                'SELECT phone FROM users WHERE phone = ?', 
                (phone,)
            )
            if result:  # 如果result不为空，说明用户已存在
                return False, "该手机号已注册"
            
            # 检查邮箱是否已被使用
            email_result = self.execute_query(
                'SELECT email FROM users WHERE email = ?', 
                (email,)
            )
            if email_result:  # 如果email_result不为空，说明邮箱已被使用
                return False, "该邮箱已被注册"
            
            # 注册新用户，初始免费使用次数为30
            self.execute_query('''
                INSERT INTO users (phone, email, password, register_time, referred_by, free_uses)
                VALUES (?, ?, ?, ?, ?, 30)
            ''', (phone, email, password, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), referred_by))
            
            # 如果有推荐人，给推荐人增加免费次数
            if referred_by:
                # 检查推荐人是否存在
                ref_result = self.execute_query(
                    'SELECT phone FROM users WHERE phone = ?', 
                    (referred_by,)
                )
                if ref_result:
                    # 给推荐人增加免费次数
                    self.add_free_chance(referred_by, 20)
                    logger.info(f"已给推荐人 {referred_by} 增加20次免费使用次数")
            
            return True, "注册成功"
            
        except Exception as e:
            logger.error(f"注册失败: {str(e)}")
            return False, f"注册失败: {str(e)}"
    
    def login(self, phone, password):
        """用户登录"""
        try:
            # 使用 execute_query 方法查询用户
            result = self.execute_query(
                'SELECT phone, password, free_uses FROM users WHERE phone = ?',
                (phone,)
            )
            
            if not result:
                return False, "用户不存在"
            
            user = result[0]  # 获取第一个结果
            
            if user[1] != password:
                return False, "密码错误"
            
            return True, "登录成功"
            
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return False, f"登录失败: {str(e)}"
    
    def get_user_info(self, phone):
        """获取用户信息"""
        try:
            result = self.execute_query(
                'SELECT phone, free_uses FROM users WHERE phone = ?',
                (phone,)
            )
            
            if result:
                return {
                    'phone': result[0][0],
                    'free_uses': result[0][1]
                }
            return None
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return None
    
    def use_free_chance(self, phone):
        """使用一次免费机会"""
        try:
            result = self.execute_query(
                'SELECT free_uses FROM users WHERE phone = ?',
                (phone,)
            )
            
            if result and result[0][0] > 0:
                self.execute_query(
                    'UPDATE users SET free_uses = free_uses - 1 WHERE phone = ?',
                    (phone,)
                )
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"使用免费次数失败: {str(e)}")
            return False
    
    def is_registered(self, phone):
        """检查用户是否已注册"""
        try:
            result = self.execute_query(
                'SELECT phone FROM users WHERE phone = ? AND password IS NOT NULL',
                (phone,)
            )
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"检查用户注册状态失败: {str(e)}")
            return False
    
    def check_free_uses(self, phone):
        """检查用户的免费次数
        
        Args:
            phone: 用户手机号
            
        Returns:
            int: 用户的免费次数，如果用户不存在则返回0
        """
        try:
            result = self.execute_query(
                'SELECT phone, free_uses, referred_by FROM users WHERE phone = ?',
                (phone,)
            )
            
            if result:
                free_uses = result[0][1] if result[0][1] is not None else 0
                logger.info(f"\n=== 用户信息 ===")
                logger.info(f"手机号: {result[0][0]}")
                logger.info(f"免费次数: {free_uses}")
                logger.info(f"推荐人: {result[0][2] if result[0][2] else '无'}")
                return free_uses
            else:
                logger.info(f"未找到用户: {phone}")
                return 0
            
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return 0
    
    def init_db(self):
        """初始化数据库"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    phone TEXT PRIMARY KEY,
                    password TEXT,
                    verify_code TEXT,
                    verify_time TEXT,
                    register_time TEXT,
                    free_uses INTEGER DEFAULT 30,
                    referred_by TEXT,
                    FOREIGN KEY (referred_by) REFERENCES users(phone)
                )
            ''')
            
            # 检查email列是否存在
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 如果email列不存在，添加它
            if 'email' not in columns:
                # SQLite不允许直接添加UNIQUE列，需要创建新表并迁移数据
                cursor.execute('''
                    CREATE TABLE users_new (
                        phone TEXT PRIMARY KEY,
                        email TEXT UNIQUE,
                        password TEXT,
                        verify_code TEXT,
                        verify_time TEXT,
                        register_time TEXT,
                        free_uses INTEGER DEFAULT 30,
                        referred_by TEXT,
                        FOREIGN KEY (referred_by) REFERENCES users(phone)
                    )
                ''')
                
                # 复制数据到新表
                cursor.execute('''
                    INSERT INTO users_new (phone, password, verify_code, verify_time, register_time, free_uses, referred_by)
                    SELECT phone, password, verify_code, verify_time, register_time, free_uses, referred_by
                    FROM users
                ''')
                
                # 删除旧表
                cursor.execute('DROP TABLE users')
                
                # 重命名新表为users
                cursor.execute('ALTER TABLE users_new RENAME TO users')
                
                logger.info("成功添加email列到users表")
            
            conn.commit()
        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            raise e
        finally:
            if conn:
                conn.close()
    
    def add_free_chance(self, phone, count=1):
        """添加免费使用次数
        
        Args:
            phone: 用户手机号
            count: 要添加的次数，默认为1
            
        Returns:
            bool: 是否添加成功
        """
        try:
            result = self.execute_query(
                'SELECT free_uses FROM users WHERE phone = ?',
                (phone,)
            )
            
            if result:
                current_uses = result[0][0] if result[0][0] is not None else 0
                new_uses = current_uses + count
                
                self.execute_query(
                    'UPDATE users SET free_uses = ? WHERE phone = ?',
                    (new_uses, phone)
                )
                
                logger.info(f"已为用户 {phone} 添加 {count} 次免费使用次数，当前共有 {new_uses} 次")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"添加免费次数失败: {str(e)}")
            return False