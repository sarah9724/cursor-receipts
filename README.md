# 发票处理系统

一个基于Flask的发票处理系统，支持批量处理PDF发票并生成Excel汇总。

## 功能特点

- 用户系统
  - 用户注册和登录
  - 推荐机制（推荐新用户可获得20次免费使用机会）
  - 免费次数统计

- 发票处理
  - 支持批量上传PDF发票
  - 自动提取发票关键信息
  - 生成Excel汇总报表
  - 支持关键字筛选
  - 自动识别重复发票

## 技术栈

- 后端：Python + Flask
- 数据库：SQLite
- 前端：HTML + JavaScript
- PDF处理：pdfplumber
- Excel生成：openpyxl

## 安装说明

1. 克隆仓库 