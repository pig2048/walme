# Walme Bot

一个自动化的任务管理系统，用于处理 Walme 平台的日常任务和签到。

## ✨ 特性

- 🚀 支持多账户并发处理
- 🔄 自动完成每日任务和签到
- 🌐 支持代理服务器
- 📝 日志记录

## 🛠 安装

1. 克隆仓库：

```
git clone https://github.com/pig2048/walme.git
cd walme-bot-enhanced
```

2. 配置虚拟环境(推荐):
Win/Linux

```
.\venv\Scripts\activate
source .\venv\bin\activate
```

3. 安装依赖：

```
pip install -r requirements.txt
```

## ⚙️ 配置

1. 创建以下文件：

- `tokens.txt`: 每行一个访问令牌
- `proxies.txt`: （可选）每行一个代理服务器地址
- `config.json`: （可选）自定义配置文件

2. 配置选项（config.json）：

- 代理开关,最大并发,重试次数,账户间延迟,任务之间的延迟

## 🚀 使用

运行主程序：

```
python main.py
```
