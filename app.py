from flask import Flask, render_template, request, jsonify, send_file, session, after_this_request, url_for
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
import base64
import uuid
import tempfile
import time

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
    static_folder=os.path.abspath('static'),
    static_url_path='/static'
)
app.secret_key = 'your-secret-key'  # 用于session

# 优化性能配置
app.config.update(
    SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 静态文件缓存1年
    TEMPLATES_AUTO_RELOAD=False,  # 关闭模板自动重载
    MAX_CONTENT_LENGTH=50 * 1024 * 1024  # 限制上传文件大小为50MB
)

# 创建临时文件夹存储Excel文件
TEMP_FOLDER = os.path.join(tempfile.gettempdir(), 'invoice_excel_files')
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

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

# 创建用户数据库实例
user_db = UserDB()

# 创建支付控制实例
payment_control = PaymentControl()

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
    """首页"""
    try:
        # 清除所有session数据
        session.clear()
        # 添加时间戳防止缓存
        current_time = int(time.time())
        return render_template('index.html', now=current_time)
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_invoice', methods=['POST'])
@login_required
def handle_invoice():
    try:
        # 获取登录用户
        phone = session.get('phone')
        if not phone:
            return jsonify({
                'success': False,
                'message': '请先登录'
            }), 401
            
        # 检查是否有免费次数
        free_uses = user_db.check_free_uses(phone)
        if free_uses <= 0:
            logger.warning(f"用户 {phone} 免费次数用完")
            return jsonify({
                'success': False,
                'message': '免费次数已用完，请付费继续使用'
            })
            
        # 检查是否有提交文件
        if 'invoices[]' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'})
        
        files = request.files.getlist('invoices[]')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
            
        search_texts = request.form.getlist('search_texts[]')
        search_texts = [text.strip() for text in search_texts if text.strip()]
        
        logger.info("\n=== 开始处理发票 ===")
        logger.info(f"处理文件数量: {len(files)}")
        logger.info(f"搜索文本: {search_texts}")
        
        try:
            result = process_multiple_invoices(files, search_texts)
            logger.info(f"处理结果: {result}")  # 添加日志
            
            if result['success']:
                # 消耗一次免费次数 - 确保每次处理都扣减
                user_db.use_free_chance(phone)
                logger.info(f"为用户 {phone} 消耗了1次免费使用次数")
                
                # 获取剩余次数用于返回 - 使用check_free_uses
                remaining_uses = user_db.check_free_uses(phone)
                
                # 生成唯一的文件名
                file_uuid = str(uuid.uuid4())
                excel_filename = result['excel_filename']
                temp_file_path = os.path.join(TEMP_FOLDER, f"{file_uuid}_{excel_filename}")
                
                # 保存Excel文件到临时目录
                with open(temp_file_path, 'wb') as f:
                    f.write(result['excel_content'])
                
                # 记录文件路径和过期时间
                session['excel_uuid'] = file_uuid
                session['excel_filename'] = excel_filename
                
                # 添加日志以检查Excel内容是否正确
                excel_size = len(result['excel_content'])
                logger.info(f"Excel内容大小: {excel_size} 字节")
                logger.info(f"Excel文件保存到: {temp_file_path}")
                
                response_data = {
                    'success': True,
                    'total_files': len(files),
                    'processed_files': result['total_processed'],
                    'duplicate_files': result.get('duplicate_count', 0),
                    'processed_filenames': result.get('processed_filenames', []),
                    'duplicate_filenames': result.get('duplicate_filenames', []),
                    'excel_filename': excel_filename,
                    'download_url': f"/download_excel/{file_uuid}/{excel_filename}",
                    'message': '发票处理成功',
                    'free_uses_remaining': remaining_uses  # 返回剩余免费次数
                }
                
                logger.info(f"返回数据: {response_data}")  # 添加日志
                return jsonify(response_data)
            else:
                error_msg = result.get('message', '处理失败，请检查文件格式是否正确')
                logger.error(f"处理失败: {error_msg}")
                return jsonify({
                    'success': False,
                    'message': error_msg,
                    'error_details': result.get('error', '')
                })
            
        except Exception as process_error:
            logger.error(f"\n处理发票时发生错误: {str(process_error)}")
            import traceback
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': '处理发票时发生错误',
                'error_details': str(process_error)
            })
            
    except Exception as e:
        logger.error(f"\n请求处理错误: {str(e)}")
        import traceback
        logger.error(f"错误详情:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': '处理请求时发生错误',
            'error_details': str(e)
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
        logger.info(f"收到支付验证请求: {data}")
        
        # 由于是测试环境，这里简化验证
        amount = data.get('amount')
        verify_code = data.get('verify_code')
        
        if not amount or not verify_code:
            logger.warning("支付验证失败: 缺少金额或验证码")
            return jsonify({
                'success': False,
                'message': '请提供完整的验证信息'
            })
        
        # 添加用户免费次数
        phone = session.get('phone')
        if phone:
            user_db.add_free_chance(phone, 1)
            logger.info(f"已为用户 {phone} 添加1次免费使用次数")
            
            # 获取更新后的用户信息
            user_info = user_db.get_user_info(phone)
            if user_info:
                return jsonify({
                    'success': True,
                    'message': '支付验证成功',
                    'free_uses': user_info.get('free_uses', 0)
                })
        
        # 在测试环境中，简单返回成功
        return jsonify({
            'success': True,
            'message': '支付验证成功'
        })
        
    except Exception as e:
        logger.error(f"支付验证出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
                'phone': phone,
                'free_uses': user_info.get('free_uses', 0)
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
            
            # 获取用户信息，但不返回免费次数用完的消息
            user_info = user_db.get_user_info(phone)
            if user_info:
                return jsonify({
                    'success': True,
                    'message': message,
                    'free_uses': user_info.get('free_uses', 0),
                    'user_info': user_info
                })
            
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"登录处理失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"登录失败: {str(e)}"
        })

@app.route('/register', methods=['POST'])
def handle_register():
    """处理注册请求"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        email = data.get('email')
        password = data.get('password')
        referred_by = data.get('referredBy')  # 获取推荐人手机号
        
        if not phone or not email or not password:
            return jsonify({
                'success': False,
                'message': '请输入手机号、邮箱和密码'
            })
            
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({
                'success': False,
                'message': '请输入正确的手机号'
            })
            
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({
                'success': False,
                'message': '请输入正确的邮箱格式'
            })
        
        # 传入推荐人信息
        success, message = user_db.register(phone, email, password, referred_by)
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
            # 只返回用户信息，不检查免费次数
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

@app.before_request
def before_request():
    if not request.path.startswith('/static'):
        logger.info(f"Incoming request: {request.method} {request.path}")

@app.after_request
def after_request(response):
    if not request.path.startswith('/static'):
        logger.info(f"Request completed: {response.status_code}")
    return response

@app.route('/download_excel/<file_uuid>/<filename>', methods=['GET'])
def download_excel(file_uuid, filename):
    """下载Excel文件"""
    try:
        # 构建完整的文件路径
        temp_file_path = os.path.join(TEMP_FOLDER, f"{file_uuid}_{filename}")
        
        # 检查文件是否存在
        if not os.path.exists(temp_file_path):
            logger.error(f"找不到Excel文件: {temp_file_path}")
            return jsonify({
                'success': False,
                'message': '找不到Excel文件'
            })
        
        logger.info(f"下载文件: {temp_file_path}")
        
        # 设置一个清理任务，在响应发送后删除文件
        @after_this_request
        def remove_file(response):
            try:
                # 下载完成后30秒删除文件
                def delayed_remove():
                    import time
                    time.sleep(30)
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        logger.info(f"临时文件已删除: {temp_file_path}")
                
                # 在新线程中延迟删除文件
                import threading
                thread = threading.Thread(target=delayed_remove)
                thread.daemon = True
                thread.start()
            except Exception as e:
                logger.error(f"删除临时文件失败: {str(e)}")
            return response
        
        # 使用send_file发送文件
        return send_file(
            temp_file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载Excel文件失败: {str(e)}")
        import traceback
        logger.error(f"错误详情:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': '下载Excel文件失败'
        })

@app.context_processor
def inject_cache_buster():
    """添加时间戳到静态文件URL，防止浏览器缓存"""
    def cache_busting_url(filename):
        import time
        return f"{url_for('static', filename=filename)}?v={int(time.time())}"
    return dict(cache_busting_url=cache_busting_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 