workers = 4  # 根据CPU核心数调整
bind = "0.0.0.0:5000"
timeout = 120  # 增加超时时间，处理大文件
max_requests = 1000
max_requests_jitter = 50 