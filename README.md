# 免费节点订阅爬虫集合

这是一个自动爬取多个来源的免费Clash/V2ray节点订阅链接的工具集合，包括数据爬取、处理和展示功能。

## 功能特点

- 自动爬取多个来源的免费节点订阅链接
- 集成多种节点来源：
  - Datiya网站的每日节点
  - 日日更新节点永久订阅
  - FreeV2.net订阅链接
  - BestClash GitHub仓库订阅
  - 周润发公益v2ray节点
  - v2rayc.github.io节点订阅
- 生成美观的HTML页面展示所有订阅链接
- 支持GitHub Actions自动运行，定时更新数据
- 完善的错误处理机制，确保运行稳定

## 在线查看

通过GitHub Pages可以在线查看最新的节点订阅信息：

https://你的用户名.github.io/项目名称/web/index.html

## 本地运行

### 环境要求

- Python 3.7+
- 安装相关依赖：`pip install -r requirements.txt`

### 快速开始

1. 克隆仓库：
   ```bash
   git clone https://github.com/你的用户名/项目名称.git
   cd 项目名称
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 运行爬虫：
   ```bash
   # Windows
   auto_run.bat
   
   # Linux/Mac
   chmod +x auto_run.sh
   ./auto_run.sh
   ```

### 命令行参数

支持多种命令行参数以执行不同的功能：

- `python monitor_and_fetch.py --all-dates`: 爬取所有日期
- `python monitor_and_fetch.py --force-update`: 强制更新所有数据
- `python monitor_and_fetch.py --generate-html`: 仅重新生成HTML页面
- `python monitor_and_fetch.py --freev2`: 仅爬取FreeV2.net
- `python monitor_and_fetch.py --bestclash`: 仅爬取BestClash
- `python monitor_and_fetch.py --shaoyou`: 仅爬取周润发公益v2ray节点
- `python monitor_and_fetch.py --ripao`: 仅爬取日日更新节点
- `python monitor_and_fetch.py --v2rayc`: 仅爬取v2rayc.github.io节点

## GitHub Actions自动更新

本项目利用GitHub Actions实现了自动化爬取和更新：

1. 每天自动运行爬虫收集最新节点
2. 自动提交更新的数据到仓库
3. 自动生成最新的HTML展示页面

### 手动触发更新

1. 前往仓库的"Actions"标签页
2. 选择"自动爬取节点订阅"工作流
3. 点击"Run workflow"按钮手动触发更新

## 目录结构

- `datiya_scraper.py`: Datiya网站爬虫
- `freev2_scraper.py`: FreeV2.net网站爬虫
- `github_monitor.py`: GitHub仓库监控
- `monitor_and_fetch.py`: 整合功能的主程序
- `v2rayc_scraper.py`: v2rayc.github.io爬虫
- `ripao_scraper.py`: 日日更新节点爬虫
- `shaoyou_scraper.py`: 周润发公益v2ray节点爬虫
- `auto_run.bat`/`auto_run.sh`: 一键运行脚本
- `results/`: 保存爬取结果
- `downloads/`: 保存下载的订阅文件
- `web/`: 生成的HTML页面和数据

## 免责声明

- 本项目仅用于学习和研究网络爬虫技术
- 请遵守相关网站的使用条款和法律法规
- 获取的节点仅供学习和测试使用，请勿用于非法用途

## 许可证

MIT许可证 