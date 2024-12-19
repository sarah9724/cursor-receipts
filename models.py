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
                phone TEXT PRIMARY KEY,     -- 手机号
                password TEXT,              -- 密码
                verify_code TEXT,           -- 验证码
                verify_time TEXT,           -- 验证码发送时间
                register_time TEXT,         -- 注册时间
                free_uses INTEGER DEFAULT 0,   -- 免费使用次数
                referred_by TEXT,           -- 推荐人的手机号
                FOREIGN KEY (referred_by) REFERENCES users(phone)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send_code(self, phone):
        """发送验证码（测试版本）"""
        try:
            # 首先检查用户是否已经注册
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT password FROM users WHERE phone = ? AND password IS NOT NULL', (phone,))
            if cursor.fetchone():
                conn.close()
                return False, "该手机号已注册"
            
            # 生成6位测试验证码
            code = '123456'  # 固定测试验证码
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查用户是否存在
            cursor.execute('SELECT phone FROM users WHERE phone = ?', (phone,))
            if cursor.fetchone():
                # 更新现有用户的验证码
                cursor.execute('''
                    UPDATE users 
                    SET verify_code = ?, verify_time = ?
                    WHERE phone = ?
                ''', (code, now, phone))
            else:
                # 创建新用户记录
                cursor.execute('''
                    INSERT INTO users (phone, verify_code, verify_time)
                    VALUES (?, ?, ?)
                ''', (phone, code, now))
            
            conn.commit()
            conn.close()
            
            # 在控制台打印验证码（方便测试）
            print(f"\n=== 测试验证码 ===")
            print(f"手机号: {phone}")
            print(f"验证码: {code}")
            print(f"发送时间: {now}")
            
            return code
            
        except Exception as e:
            print(f"发送验证码失败: {str(e)}")
            raise e
    
    def verify_code(self, phone, code, password, referred_by=None):
        """验证码验证并注册"""
        try:
            print("\n=== 开始验证码验证和注册流程 ===")
            print(f"注册手机号: {phone}")
            print(f"推荐人手机号: {referred_by}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 首先检查用户是否已经注册
            cursor.execute('SELECT password, register_time FROM users WHERE phone = ?', (phone,))
            existing_user = cursor.fetchone()
            if existing_user and existing_user[0] is not None:
                print(f"\n=== 注册检查 ===")
                print(f"手机号: {phone}")
                print(f"已注册时间: {existing_user[1]}")
                conn.close()
                return False, "该手机号已注册"
            
            # 检查验证码
            cursor.execute('SELECT verify_code, verify_time FROM users WHERE phone = ?', (phone,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return False, "手机号未发送验证码"
            
            saved_code, verify_time = result
            
            # 验证码5分钟内有效
            verify_datetime = datetime.strptime(verify_time, '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - verify_datetime).seconds > 300:
                conn.close()
                return False, "验证码已过期"
            
            if code != saved_code:
                conn.close()
                return False, "验证码错误"
            
            # 验证成功，完成注册
            if referred_by:
                print("\n=== 开始处理推荐 ===")
                print(f"新用户: {phone}")
                print(f"推荐人: {referred_by}")
                
                # 验证推荐人是否存在且已注册
                cursor.execute('''
                    SELECT phone, free_uses, password, register_time 
                    FROM users 
                    WHERE phone = ?
                ''', (referred_by,))
                referrer = cursor.fetchone()
                
                print(f"推荐人信息: {referrer}")  # 打印完整的推荐人信息
                
                if not referrer or not referrer[2]:  # 检查password是否存在
                    print(f"推荐人不存在或未完成注册")
                    print(f"推荐人数据: {referrer}")
                    conn.close()
                    return False, "推荐人不存在或未完成注册"
                    
                current_free_uses = referrer[1] if referrer[1] is not None else 0
                print(f"推荐人当前免费次数: {current_free_uses}")
                
                # 给推荐人增加20次免费使用机会
                new_free_uses = current_free_uses + 20
                print(f"准备更新免费次数为: {new_free_uses}")
                
                try:
                    cursor.execute('''
                        UPDATE users 
                        SET free_uses = ? 
                        WHERE phone = ?
                    ''', (new_free_uses, referred_by))
                    print("执行更新SQL成功")
                except Exception as e:
                    print(f"更新推荐人免费次数失败: {str(e)}")
                
                # 验证更新是否成功
                cursor.execute('SELECT free_uses FROM users WHERE phone = ?', (referred_by,))
                result = cursor.fetchone()
                if result:
                    print(f"更新后免费次数: {result[0]}")
                else:
                    print("更新失败")
                
                # 检查更新是否被提交
                try:
                    conn.commit()
                    print("提交更新成功")
                except Exception as e:
                    print(f"提交更新失败: {str(e)}")
                
                cursor.execute('SELECT free_uses FROM users WHERE phone = ?', (referred_by,))
                final_check = cursor.fetchone()
                print(f"最终确认免费次数: {final_check[0] if final_check else 'None'}")
            
            # 更新新用户信息
            cursor.execute('''
                UPDATE users SET 
                    password = ?,
                    register_time = ?,
                    referred_by = ?,
                    free_uses = 0  -- 新用户初始免费次数为0
                WHERE phone = ?
            ''', (password, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), referred_by, phone))
            
            conn.commit()
            conn.close()
            return True, "注册成功"
            
        except Exception as e:
            print(f"验证失败: {str(e)}")
            if conn:
                conn.close()
            return False, f"验证失败: {str(e)}"
    
    def login(self, phone, password):
        """用户登录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT password FROM users WHERE phone = ?', (phone,))
            result = cursor.fetchone()
            
            if not result:
                return False, "用户不存在"
            
            if password != result[0]:
                return False, "密码错误"
            
            return True, "登录成功"
            
        except Exception as e:
            print(f"登录失败: {str(e)}")
            return False, f"登录失败: {str(e)}"
    
    def get_user_info(self, phone):
        """获取用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT phone, free_uses 
                FROM users WHERE phone = ?
            ''', (phone,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'phone': result[0],
                    'free_uses': result[1]
                }
            return None
            
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return None
    
    def use_free_chance(self, phone):
        """使用一次免费机会"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT free_uses FROM users WHERE phone = ?', (phone,))
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                cursor.execute('''
                    UPDATE users 
                    SET free_uses = free_uses - 1 
                    WHERE phone = ?
                ''', (phone,))
                conn.commit()
                return True
                
            return False
            
        except Exception as e:
            print(f"使用免费次数失败: {str(e)}")
            return False
    
    def is_registered(self, phone):
        """检查用户是否已注册"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT phone FROM users 
                WHERE phone = ? AND password IS NOT NULL
            ''', (phone,))
            
            result = cursor.fetchone()
            return result is not None
            
        except Exception as e:
            print(f"检查用户注册状态失败: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def check_free_uses(self, phone):
        """检查用户的免费次数（调试用）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT phone, free_uses, referred_by 
                FROM users 
                WHERE phone = ?
            ''', (phone,))
            
            result = cursor.fetchone()
            if result:
                print(f"\n=== 用户信息 ===")
                print(f"手机号: {result[0]}")
                print(f"免费次数: {result[1] if result[1] is not None else 0}")
                print(f"推荐人: {result[2] if result[2] else '无'}")
            else:
                print(f"未找到用户: {phone}")
            
        except Exception as e:
            print(f"查询失败: {str(e)}")
        finally:
            if conn:
                conn.close()