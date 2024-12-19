from flask import Flask, render_template, request, jsonify, send_file, session
from invoice_process import process_invoice, process_multiple_invoices
import os
import logging
import io
import random
from datetime import datetime, timedelta
import hashlib
from models import UserDB
import re
from functools import wraps

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
    static_folder=os.path.abspath('static'),
    static_url_path='/static'
)
app.secret_key = 'your-secret-key'  # 用于session

class PaymentControl:
    def __init__(self):
        self.amounts = {}  # 存储金额信息
        self.ip_count = {}  # 记录IP获取次数
        
    def generate_amount(self, ip):
        # 检查IP获取次数
        today = datetime.now().strftime('%Y-%m-%d')
        if today in self.ip_count:
            if ip in self.ip_count[today]:
                if self.ip_count[today][ip] >= 5:  # 每天最多5次
                    return None, "今日获取次数已达上限，请明天再试"
                self.ip_count[today][ip] += 1
            else:
                self.ip_count[today][ip] = 1
        else:
            self.ip_count = {today: {ip: 1}}  # 重置计数
            
        # 生成金额和验证码
        amount = round(1 + random.randint(1, 99) / 100, 2)
        verify_code = ''.join(random.choices('0123456789', k=4))
        expire_time = datetime.now() + timedelta(minutes=15)  # 15分钟有效期
        
        # 生成唯一标识
        identifier = hashlib.md5(f"{amount}{verify_code}{expire_time}".encode()).hexdigest()
        
        self.amounts[identifier] = {
            'amount': amount,
            'verify_code': verify_code,
            'expire_time': expire_time,
            'used': False
        }
        
        return {
            'identifier': identifier,
            'amount': amount,
            'verify_code': verify_code,
            'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S')
        }, None

    def verify_payment(self, identifier, amount, verify_code):
        if identifier not in self.amounts:
            return False, "验证信息无效"
            
        payment_info = self.amounts[identifier]
        
        if payment_info['used']:
            return False, "该验证码已使用"
            
        if datetime.now() > payment_info['expire_time']:
            return False, "验证码已过期"
            
        if abs(float(amount) - payment_info['amount']) > 0.001:
            return False, "支付金额不正确"
            
        if verify_code != payment_info['verify_code']:
            return False, "验证码错误"
            
        # 验证通过，标记为已使用
        payment_info['used'] = True
        return True, "验证成功"

# 创建支付控制实例
payment_control = PaymentControl()

# 创建用户数据库实例
user_db = UserDB()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        phone = session.get('phone')  # 使用phone而不是username
        if not phone or not user_db.is_registered(phone):
            return jsonify({
                'success': False,
                'message': '请先登录'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    try:
        # 清除所有session数据
        session.clear()
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_invoice', methods=['POST'])
@login_required
def handle_invoice():
    try:
        phone = session.get('phone')  # 使用phone而不是username
        
        # 检查是否有免费次数
        if user_db.use_free_chance(phone):  # 使用phone而不是username
            # 有免费次数，直接处理
            pass
        else:
            # 无免费次数，需要付费
            pass
            
        if 'invoices[]' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'})
        
        files = request.files.getlist('invoices[]')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
            
        search_texts = request.form.getlist('search_texts[]')
        search_texts = [text.strip() for text in search_texts if text.strip()]
        
        print("\n=== 开始处理发票 ===")
        print(f"处理文件数量: {len(files)}")
        print(f"搜索文本: {search_texts}")
        
        try:
            result = process_multiple_invoices(files, search_texts)
            
            if result['success']:
                response_data = {
                    'success': True,
                    'total_files': len(files),
                    'processed_files': result['total_processed'],
                    'duplicate_files': result.get('duplicate_count', 0),
                    'processed_filenames': result.get('processed_filenames', []),
                    'duplicate_filenames': result.get('duplicate_filenames', []),
                    'excel_content': result['excel_content'].hex(),
                    'excel_filename': result['excel_filename']
                }
                return jsonify(response_data)
            else:
                return jsonify(result)
            
        except Exception as process_error:
            print(f"\n处理发票时发生错误: {str(process_error)}")
            import traceback
            print(f"错误详情:\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': '处理发票时发生错误'
            })
            
    except Exception as e:
        print(f"\n请求处理错误: {str(e)}")
        import traceback
        print(f"错误详情:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': '处理请求时发生错误'
        })

@app.route('/get_payment_amount', methods=['GET'])
@login_required
def get_payment_amount():
    """获取支付金额和验证码"""
    ip = request.remote_addr
    result, error = payment_control.generate_amount(ip)
    
    if error:
        return jsonify({
            'success': False,
            'message': error
        })
        
    session['payment_identifier'] = result['identifier']
    return jsonify({
        'success': True,
        'amount': result['amount'],
        'verify_code': result['verify_code'],
        'expire_time': result['expire_time']
    })

@app.route('/verify_payment', methods=['POST'])
@login_required
def verify_payment():
    """验证支付"""
    try:
        data = request.get_json()
        identifier = session.get('payment_identifier')
        amount = data.get('amount')
        verify_code = data.get('verify_code')
        
        if not all([identifier, amount, verify_code]):
            return jsonify({
                'success': False,
                'message': '请提供完整的验证信息'
            })
        
        success, message = payment_control.verify_payment(identifier, amount, verify_code)
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/send_code', methods=['POST'])
def send_code():
    """发送验证码"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'success': False,
                'message': '请输入正确的手机号'
            })
        
        try:
            code = user_db.send_code(phone)
            return jsonify({
                'success': True,
                'message': f'验证码已发送: {code}'  # 在实际生产环境中不要返回验证码
            })
        except Exception as e:
            print(f"数据库操作失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': '发送验证码失败，请稍后重试'
            })
            
    except Exception as e:
        print(f"发送验证码接口错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/verify_code', methods=['POST'])
def verify_code():
    """验证码验证"""
    try:
        data = request.get_json()
        print("\n=== 收到验证码验证请求 ===")
        print(f"请求数据: {data}")
        
        phone = data.get('phone')
        code = data.get('code')
        password = data.get('password')
        referred_by = data.get('referredBy')  # 注意这里是referredBy而不是referred_by
        
        print(f"手机号: {phone}")
        print(f"验证码: {code}")
        print(f"推荐人: {referred_by}")
        
        if not phone or not code or not password:
            return jsonify({
                'success': False,
                'message': '请输入手机号、验证码和密码'
            })
        
        success, message = user_db.verify_code(phone, code, password, referred_by)
        print(f"验证结果: success={success}, message={message}")
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        print(f"验证码验证失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/check_auth', methods=['GET'])
def check_auth():
    """检查用户是否已登录"""
    try:
        phone = session.get('phone')  # 使用phone而不是username
        if not phone:
            return jsonify({
                'success': False,
                'message': '未登录'
            })
            
        # 检查用户是否在数据库中
        user_info = user_db.get_user_info(phone)
        if user_info:
            return jsonify({
                'success': True,
                'phone': phone
            })
        else:
            # 如果用户不在数据库中，清除session
            session.pop('phone', None)
            return jsonify({
                'success': False,
                'message': '用户未注册'
            })
            
    except Exception as e:
        logger.error(f"检查登录状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '检查登录状态失败'
        })

@app.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({
        'success': True,
        'message': '已登出'
    })

@app.route('/login', methods=['POST'])
def handle_login():
    """处理登录请求"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        password = data.get('password')
        
        if not phone or not password:
            return jsonify({
                'success': False,
                'message': '请输入手机号和密码'
            })
        
        success, message = user_db.login(phone, password)
        if success:
            session['phone'] = phone  # 保存到session
            session.permanent = True  # 设置session持久化
            
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/register', methods=['POST'])
def handle_register():
    """处理注册请求"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        password = data.get('password')
        referred_by = data.get('referredBy')  # 获取推荐人手机号
        
        if not phone or not password:
            return jsonify({
                'success': False,
                'message': '请输入手机号和密码'
            })
            
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'success': False,
                'message': '请输入正确的手机号'
            })
        
        # 传入推荐人信息
        success, message = user_db.register(phone, password, referred_by)
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/user_info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    try:
        phone = session.get('phone')  # 使用phone而不是username
        if not phone:
            return jsonify({
                'success': False,
                'message': '未登录'
            })
            
        user_info = user_db.get_user_info(phone)
        if user_info:
            return jsonify({
                'success': True,
                **user_info
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取用户信息失败'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    app.run() 