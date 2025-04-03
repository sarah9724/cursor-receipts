# 卫华发票辅助整理系统

这是一个基于Flask的发票处理系统，支持批量处理PDF发票并生成Excel汇总报告。

## 功能特点

- 用户注册和登录系统
- 发票PDF文件上传和批量处理
- 发票信息自动提取
- 生成Excel格式的汇总报告
- 免费/付费使用模式
- 推荐用户奖励机制

## 技术栈

- 后端：Flask
- 前端：原生JavaScript, HTML, CSS
- 数据库：SQLite
- PDF处理：pdfplumber
- Excel生成：openpyxl

## 本地开发

1. 克隆仓库
```bash
git clone <仓库URL>
cd 发票工具
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 启动开发服务器
```bash
export FLASK_ENV=development  # Windows: set FLASK_ENV=development
python app.py
```

## 生产部署

系统已配置为可在Cloudflare上部署，详见部署文档。 