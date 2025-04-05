#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日日更新节点订阅爬虫
提供永久稳定的Clash和通用base64/v2ray订阅链接
"""

import requests
import json
import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ripao_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ripao_scraper")

def scrape_ripao():
    """
    获取日日更新节点的永久订阅链接
    
    返回:
    dict: 包含订阅链接的字典
    """
    try:
        logger.info("开始获取日日更新节点订阅信息")
        print("开始获取日日更新节点订阅信息")
        
        # 永久固定的订阅链接
        clash_link = "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash"
        v2ray_link = "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub"
        
        # 国内镜像链接 (假设使用ghproxy等代理)
        clash_mirror = "https://ghproxy.com/https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash"
        v2ray_mirror = "https://ghproxy.com/https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub"
        
        # 测试链接是否可用
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
        
        clash_available = False
        v2ray_available = False
        
        try:
            logger.info("测试Clash订阅链接可用性")
            response = requests.head(clash_link, headers=headers, timeout=10)
            clash_available = response.status_code == 200
            logger.info(f"Clash订阅链接可用性: {clash_available}")
        except Exception as e:
            logger.warning(f"测试Clash订阅链接时出错: {e}")
        
        try:
            logger.info("测试V2Ray订阅链接可用性")
            response = requests.head(v2ray_link, headers=headers, timeout=10)
            v2ray_available = response.status_code == 200
            logger.info(f"V2Ray订阅链接可用性: {v2ray_available}")
        except Exception as e:
            logger.warning(f"测试V2Ray订阅链接时出错: {e}")
        
        # 整理结果
        result = {
            "title": "日日更新节点永久订阅",
            "description": "永久固定的订阅地址，国内优先使用镜像订阅",
            "clash_link": clash_link,
            "v2ray_link": v2ray_link,
            "clash_mirror": clash_mirror,
            "v2ray_mirror": v2ray_mirror,
            "clash_available": clash_available,
            "v2ray_available": v2ray_available,
            "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "update_interval": "日更新"
        }
        
        # 保存结果
        save_result(result)
        
        logger.info("日日更新节点订阅信息获取成功")
        print("日日更新节点订阅信息获取成功")
        
        return result
    
    except Exception as e:
        logger.exception(f"获取日日更新节点订阅信息时出错: {e}")
        print(f"获取日日更新节点订阅信息时出错: {e}")
        return None

def save_result(result):
    """
    将爬取结果保存到文件
    """
    # 创建results/ripao目录(如果不存在)
    save_dir = "results/ripao"
    os.makedirs(save_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = current_time.strftime('%Y%m%d')
    time_str = current_time.strftime('%H%M%S')
    
    # 保存JSON结果
    json_filename = f"{save_dir}/ripao_{date_str}_{time_str}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 保存文本结果
    txt_filename = f"{save_dir}/ripao_{date_str}_{time_str}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"标题: {result['title']}\n")
        f.write(f"描述: {result['description']}\n")
        f.write(f"爬取时间: {result['scrape_time']}\n")
        f.write(f"更新频率: {result['update_interval']}\n\n")
        
        f.write("Clash订阅链接:\n")
        f.write(f"- {result['clash_link']}\n")
        f.write(f"- 可用性: {'可用' if result['clash_available'] else '不可用'}\n\n")
        
        f.write("V2Ray订阅链接:\n")
        f.write(f"- {result['v2ray_link']}\n")
        f.write(f"- 可用性: {'可用' if result['v2ray_available'] else '不可用'}\n\n")
        
        f.write("国内镜像链接:\n")
        f.write(f"- Clash镜像: {result['clash_mirror']}\n")
        f.write(f"- V2Ray镜像: {result['v2ray_mirror']}\n")
    
    # 保存最新结果到固定文件
    latest_json = f"{save_dir}/ripao_latest.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果保存到: {json_filename}")
    logger.info(f"结果保存到: {txt_filename}")
    logger.info(f"最新数据保存到: {latest_json}")
    
    print(f"结果保存到: {json_filename}")
    print(f"结果保存到: {txt_filename}")
    print(f"最新数据保存到: {latest_json}")

def download_subscription_files(result):
    """
    下载订阅文件内容
    """
    if not result:
        logger.warning("结果为空，无法下载订阅文件")
        return []
    
    # 创建downloads/ripao目录(如果不存在)
    download_dir = "downloads/ripao"
    os.makedirs(download_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = current_time.strftime('%Y%m%d')
    time_str = current_time.strftime('%H%M%S')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    downloaded_files = []
    
    # 尝试下载Clash配置
    try:
        # 优先使用直连
        link = result['clash_link']
        filename = f"{download_dir}/ripao_clash_{date_str}_{time_str}.yaml"
        
        logger.info(f"开始下载Clash订阅: {link}")
        response = requests.get(link, headers=headers, timeout=15)
        response.raise_for_status()
        
        with open(filename, "wb") as f:
            f.write(response.content)
        
        logger.info(f"已下载Clash订阅: {filename}")
        downloaded_files.append(filename)
        
        # 保存最新的订阅内容到固定文件
        latest_file = f"{download_dir}/ripao_clash_latest.yaml"
        with open(latest_file, "wb") as f:
            f.write(response.content)
    except Exception as e:
        logger.exception(f"下载Clash订阅时出错: {e}")
        
        # 尝试使用镜像
        try:
            mirror_link = result['clash_mirror']
            logger.info(f"尝试使用镜像下载Clash订阅: {mirror_link}")
            
            response = requests.get(mirror_link, headers=headers, timeout=15)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            logger.info(f"已通过镜像下载Clash订阅: {filename}")
            downloaded_files.append(filename)
            
            # 保存最新的订阅内容到固定文件
            latest_file = f"{download_dir}/ripao_clash_latest.yaml"
            with open(latest_file, "wb") as f:
                f.write(response.content)
        except Exception as mirror_err:
            logger.exception(f"使用镜像下载Clash订阅时出错: {mirror_err}")
    
    # 尝试下载V2Ray配置
    try:
        # 优先使用直连
        link = result['v2ray_link']
        filename = f"{download_dir}/ripao_v2ray_{date_str}_{time_str}.txt"
        
        logger.info(f"开始下载V2Ray订阅: {link}")
        response = requests.get(link, headers=headers, timeout=15)
        response.raise_for_status()
        
        with open(filename, "wb") as f:
            f.write(response.content)
        
        logger.info(f"已下载V2Ray订阅: {filename}")
        downloaded_files.append(filename)
        
        # 保存最新的订阅内容到固定文件
        latest_file = f"{download_dir}/ripao_v2ray_latest.txt"
        with open(latest_file, "wb") as f:
            f.write(response.content)
    except Exception as e:
        logger.exception(f"下载V2Ray订阅时出错: {e}")
        
        # 尝试使用镜像
        try:
            mirror_link = result['v2ray_mirror']
            logger.info(f"尝试使用镜像下载V2Ray订阅: {mirror_link}")
            
            response = requests.get(mirror_link, headers=headers, timeout=15)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            logger.info(f"已通过镜像下载V2Ray订阅: {filename}")
            downloaded_files.append(filename)
            
            # 保存最新的订阅内容到固定文件
            latest_file = f"{download_dir}/ripao_v2ray_latest.txt"
            with open(latest_file, "wb") as f:
                f.write(response.content)
        except Exception as mirror_err:
            logger.exception(f"使用镜像下载V2Ray订阅时出错: {mirror_err}")
    
    return downloaded_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="获取日日更新节点的永久订阅链接")
    parser.add_argument("--download", action="store_true", help="是否下载订阅文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    
    args = parser.parse_args()
    
    if args.verbose:
        # 设置日志级别为DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # 获取订阅信息
    result = scrape_ripao()
    
    if result:
        # 显示获取结果
        print("\n获取结果:")
        print(f"标题: {result['title']}")
        print(f"描述: {result['description']}")
        print(f"爬取时间: {result['scrape_time']}")
        
        print("\nClash订阅链接:")
        print(f"- {result['clash_link']}")
        print(f"- 可用性: {'可用' if result['clash_available'] else '不可用'}")
        
        print("\nV2Ray订阅链接:")
        print(f"- {result['v2ray_link']}")
        print(f"- 可用性: {'可用' if result['v2ray_available'] else '不可用'}")
        
        print("\n国内镜像链接:")
        print(f"- Clash镜像: {result['clash_mirror']}")
        print(f"- V2Ray镜像: {result['v2ray_mirror']}")
        
        # 如果需要下载订阅内容
        if args.download:
            print("\n开始下载订阅内容...")
            downloaded_files = download_subscription_files(result)
            if downloaded_files:
                print(f"成功下载 {len(downloaded_files)} 个订阅文件")
            else:
                print("下载订阅内容失败")
        
        print("\n获取成功!")
    else:
        print("获取失败") 