import os

# 环境配置
ENV = os.getenv('FLASK_ENV', 'development')  # 默认为开发环境

# 短信配置
SMS_CONFIG = {
    'development': {
        'enabled': False,  # 开发环境不发送真实短信
        'access_key_id': 'dev_key',
        'access_key_secret': 'dev_secret',
        'sign_name': '测试签名',
        'template_code': 'TEST_TEMPLATE'
    },
    'production': {
        'enabled': True,  # 生产环境发送真实短信
        'access_key_id': 'YOUR_ACCESS_KEY_ID',
        'access_key_secret': 'YOUR_ACCESS_KEY_SECRET',
        'sign_name': '您的签名',
        'template_code': '您的模板代码'
    }
}

# 获取当前环境的配置
current_config = SMS_CONFIG[ENV] 