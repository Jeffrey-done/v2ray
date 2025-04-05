#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
周润发公益免费v2ray节点订阅爬虫
每2小时自动爬取更新，提取yaml、base64和mihomo格式订阅链接
"""

import requests
import re
import json
import os
import logging
from datetime import datetime
import traceback  # 添加traceback模块

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shaoyou_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("shaoyou_scraper")

def scrape_shaoyou():
    """
    爬取周润发公益免费v2ray节点订阅信息
    
    返回:
    dict: 包含爬取结果的字典
    """
    url = "https://raw.githubusercontent.com/shaoyouvip/free/refs/heads/main/README.md"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info(f"开始爬取页面: {url}")
        print(f"开始爬取页面: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # 检查请求是否成功
        readme_content = response.text
        
        # 如果内容为空，尝试备用URL
        if not readme_content or len(readme_content) < 100:
            backup_url = "https://github.com/shaoyouvip/free/blob/main/README.md"
            logger.warning(f"原始URL内容为空或太短，尝试备用URL: {backup_url}")
            print(f"原始URL内容为空或太短，尝试备用URL: {backup_url}")
            
            response = requests.get(backup_url, headers=headers, timeout=15)
            response.raise_for_status()
            readme_content = response.text
        
        # 保存源文件用于调试
        os.makedirs("debug", exist_ok=True)
        with open("debug/debug_shaoyou.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        logger.info("已保存源文件到debug/debug_shaoyou.md")
        print("已保存源文件到debug/debug_shaoyou.md")
        
        # 提取标题和描述
        title_match = re.search(r"# (.*?)公益免费v2ray节点订阅", readme_content)
        if title_match:
            title = title_match.group(1) + "公益免费v2ray节点订阅"
        else:
            title = "周润发公益免费v2ray节点订阅"
        
        description = "每2小时更新一次，提供免费v2ray节点订阅"
        
        # 提取yaml格式订阅链接
        yaml_links = []
        yaml_patterns = [
            r"https?://[\w\./\-=]+?\.yaml",
            r"https?://[\w\./\-=]+?/all\.yaml"
        ]
        
        for pattern in yaml_patterns:
            yaml_matches = re.findall(pattern, readme_content)
            if yaml_matches:
                yaml_links.extend(yaml_matches)
        
        yaml_links = list(set(yaml_links))  # 去重
        logger.info(f"找到 {len(yaml_links)} 个yaml格式订阅链接")
        print(f"找到 {len(yaml_links)} 个yaml格式订阅链接: {yaml_links}")
        
        # 提取base64格式订阅链接
        base64_links = []
        base64_patterns = [
            r"https?://[\w\./\-=]+?\.txt",
            r"https?://[\w\./\-=]+?/base64\.txt"
        ]
        
        for pattern in base64_patterns:
            base64_matches = re.findall(pattern, readme_content)
            if base64_matches:
                base64_links.extend(base64_matches)
        
        base64_links = list(set(base64_links))  # 去重
        logger.info(f"找到 {len(base64_links)} 个base64格式订阅链接")
        print(f"找到 {len(base64_links)} 个base64格式订阅链接: {base64_links}")
        
        # 提取mihomo格式订阅链接
        mihomo_links = []
        mihomo_patterns = [
            r"https?://[\w\./\-=]+?mihomo\.yaml",
            r"https?://[\w\./\-=]+?/mihomo\.yaml"
        ]
        
        for pattern in mihomo_patterns:
            mihomo_matches = re.findall(pattern, readme_content)
            if mihomo_matches:
                mihomo_links.extend(mihomo_matches)
        
        mihomo_links = list(set(mihomo_links))  # 去重
        logger.info(f"找到 {len(mihomo_links)} 个mihomo格式订阅链接")
        print(f"找到 {len(mihomo_links)} 个mihomo格式订阅链接: {mihomo_links}")
        
        # 查找无需代理的链接
        no_proxy_section = re.search(r"# 无需代理更新节点订阅([\s\S]+?)(?=#|$)", readme_content)
        no_proxy_links = {
            "yaml": [],
            "base64": [],
            "mihomo": []
        }
        
        if no_proxy_section:
            no_proxy_content = no_proxy_section.group(1)
            
            # 提取无需代理的yaml链接
            yaml_patterns = [
                r"(https?://[\w\./\-=]+?vless-all)",
                r"(https?://[\w\./\-=]+?/all\.yaml)",
                r"(https?://[\w\./\-=]+?/vless-all)"
            ]
            
            for pattern in yaml_patterns:
                yaml_matches = re.findall(pattern, no_proxy_content)
                if yaml_matches:
                    no_proxy_links["yaml"].extend(yaml_matches)
            
            # 提取无需代理的base64链接
            base64_patterns = [
                r"(https?://[\w\./\-=]+?vless-base64)",
                r"(https?://[\w\./\-=]+?/base64\.txt)",
                r"(https?://[\w\./\-=]+?/vless-base64)"
            ]
            
            for pattern in base64_patterns:
                base64_matches = re.findall(pattern, no_proxy_content)
                if base64_matches:
                    no_proxy_links["base64"].extend(base64_matches)
            
            # 提取无需代理的mihomo链接
            mihomo_patterns = [
                r"(https?://[\w\./\-=]+?vless-mihomo)",
                r"(https?://[\w\./\-=]+?/mihomo\.yaml)",
                r"(https?://[\w\./\-=]+?/vless-mihomo)"
            ]
            
            for pattern in mihomo_patterns:
                mihomo_matches = re.findall(pattern, no_proxy_content)
                if mihomo_matches:
                    no_proxy_links["mihomo"].extend(mihomo_matches)
            
            # 去重
            no_proxy_links["yaml"] = list(set(no_proxy_links["yaml"]))
            no_proxy_links["base64"] = list(set(no_proxy_links["base64"]))
            no_proxy_links["mihomo"] = list(set(no_proxy_links["mihomo"]))
            
            logger.info(f"找到无需代理链接: yaml {len(no_proxy_links['yaml'])}, base64 {len(no_proxy_links['base64'])}, mihomo {len(no_proxy_links['mihomo'])}")
            print(f"找到无需代理链接:")
            print(f"  yaml: {no_proxy_links['yaml']}")
            print(f"  base64: {no_proxy_links['base64']}")
            print(f"  mihomo: {no_proxy_links['mihomo']}")
        
        # 提取支持的客户端信息
        clients_section = re.search(r"\|.*?\|.*?\|.*?\|([\s\S]+?)(?=##|$)", readme_content)
        clients = []
        
        if clients_section:
            clients_content = clients_section.group(1)
            client_pattern = r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
            client_matches = re.findall(client_pattern, clients_content)
            
            for client in client_matches:
                name = client[0].strip()
                platform = client[1].strip()
                url = client[2].strip()
                
                if name and platform and url and "http" in url:
                    clients.append({
                        "name": name,
                        "platform": platform,
                        "url": url.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
                    })
            
            logger.info(f"找到 {len(clients)} 个客户端信息")
            print(f"找到 {len(clients)} 个客户端信息")
            for client in clients:
                print(f"  {client['name']} ({client['platform']}): {client['url']}")
        
        # 如果没有找到任何链接，尝试直接使用固定链接
        if not yaml_links and not base64_links and not mihomo_links:
            logger.warning("未从页面提取到任何订阅链接，使用固定链接")
            print("未从页面提取到任何订阅链接，使用固定链接")
            
            yaml_links = ["https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml"]
            base64_links = ["https://raw.githubusercontent.com/shaoyouvip/free/main/base64.txt"]
            mihomo_links = ["https://raw.githubusercontent.com/shaoyouvip/free/main/mihomo.yaml"]
            
            no_proxy_links["yaml"] = ["https://d.aizrf.com/vless-all"]
            no_proxy_links["base64"] = ["https://d.aizrf.com/vless-base64"]
            no_proxy_links["mihomo"] = ["https://d.aizrf.com/vless-mihomo"]
        
        # 整理结果
        result = {
            "title": title,
            "description": description,
            "yaml_links": yaml_links,
            "base64_links": base64_links,
            "mihomo_links": mihomo_links,
            "no_proxy_links": no_proxy_links,
            "clients": clients,
            "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_url": url,
            "update_interval": "2小时"
        }
        
        # 保存结果
        save_result(result)
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"请求错误: {e}")
        print(f"请求错误: {e}")
        
        # 尝试使用固定链接
        try:
            logger.info("尝试使用固定链接")
            print("尝试使用固定链接")
            
            result = {
                "title": "周润发公益免费v2ray节点订阅",
                "description": "每2小时更新一次，提供免费v2ray节点订阅",
                "yaml_links": ["https://raw.githubusercontent.com/shaoyouvip/free/main/all.yaml"],
                "base64_links": ["https://raw.githubusercontent.com/shaoyouvip/free/main/base64.txt"],
                "mihomo_links": ["https://raw.githubusercontent.com/shaoyouvip/free/main/mihomo.yaml"],
                "no_proxy_links": {
                    "yaml": ["https://d.aizrf.com/vless-all"],
                    "base64": ["https://d.aizrf.com/vless-base64"],
                    "mihomo": ["https://d.aizrf.com/vless-mihomo"]
                },
                "clients": [],
                "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_url": url,
                "update_interval": "2小时"
            }
            
            # 保存结果
            save_result(result)
            
            return result
        except Exception as backup_err:
            logger.exception(f"使用固定链接时出错: {backup_err}")
            print(f"使用固定链接时出错: {backup_err}")
            return None
    except Exception as e:
        logger.exception(f"发生错误: {e}")
        print(f"发生错误: {e}")
        traceback.print_exc()  # 打印完整的堆栈跟踪
        return None

def save_result(result):
    """
    将爬取结果保存到文件
    """
    # 创建results/shaoyou目录(如果不存在)
    save_dir = "results/shaoyou"
    os.makedirs(save_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = current_time.strftime('%Y%m%d')
    time_str = current_time.strftime('%H%M%S')
    
    # 保存JSON结果
    json_filename = f"{save_dir}/shaoyou_{date_str}_{time_str}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 保存文本结果
    txt_filename = f"{save_dir}/shaoyou_{date_str}_{time_str}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"标题: {result['title']}\n")
        f.write(f"描述: {result['description']}\n")
        f.write(f"爬取时间: {result['scrape_time']}\n")
        f.write(f"来源: {result['source_url']}\n")
        f.write(f"更新间隔: {result['update_interval']}\n\n")
        
        f.write("yaml格式订阅链接:\n")
        for link in result['yaml_links']:
            f.write(f"- {link}\n")
        
        f.write("\nbase64格式订阅链接:\n")
        for link in result['base64_links']:
            f.write(f"- {link}\n")
        
        f.write("\nmihomo格式订阅链接:\n")
        for link in result['mihomo_links']:
            f.write(f"- {link}\n")
        
        f.write("\n无需代理链接:\n")
        f.write("yaml格式:\n")
        for link in result['no_proxy_links']['yaml']:
            f.write(f"- {link}\n")
        
        f.write("base64格式:\n")
        for link in result['no_proxy_links']['base64']:
            f.write(f"- {link}\n")
        
        f.write("mihomo格式:\n")
        for link in result['no_proxy_links']['mihomo']:
            f.write(f"- {link}\n")
        
        f.write("\n支持的客户端:\n")
        for client in result['clients']:
            f.write(f"- {client['name']} ({client['platform']}): {client['url']}\n")
    
    # 保存当前最新的订阅链接到固定文件
    latest_txt = f"{save_dir}/shaoyou_latest.txt"
    latest_links = {
        "yaml": result['yaml_links'][0] if result['yaml_links'] else "",
        "base64": result['base64_links'][0] if result['base64_links'] else "",
        "mihomo": result['mihomo_links'][0] if result['mihomo_links'] else "",
        "no_proxy_yaml": result['no_proxy_links']['yaml'][0] if result['no_proxy_links']['yaml'] else "",
        "no_proxy_base64": result['no_proxy_links']['base64'][0] if result['no_proxy_links']['base64'] else "",
        "no_proxy_mihomo": result['no_proxy_links']['mihomo'][0] if result['no_proxy_links']['mihomo'] else ""
    }
    
    with open(latest_txt, "w", encoding="utf-8") as f:
        json.dump(latest_links, f, ensure_ascii=False, indent=2)
    
    # 保存最新的JSON结果到固定文件
    latest_json = f"{save_dir}/shaoyou_latest.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果保存到: {json_filename}")
    logger.info(f"结果保存到: {txt_filename}")
    logger.info(f"最新数据保存到: {latest_json}")
    logger.info(f"最新链接保存到: {latest_txt}")
    
    print(f"结果保存到: {json_filename}")
    print(f"结果保存到: {txt_filename}")
    print(f"最新数据保存到: {latest_json}")
    print(f"最新链接保存到: {latest_txt}")

def download_subscription_files(result):
    """
    下载订阅文件内容
    """
    if not result:
        logger.warning("结果为空，无法下载订阅文件")
        return []
    
    # 创建downloads/shaoyou目录(如果不存在)
    download_dir = "downloads/shaoyou"
    os.makedirs(download_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = current_time.strftime('%Y%m%d')
    time_str = current_time.strftime('%H%M%S')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    downloaded_files = []
    
    # 下载yaml格式订阅
    if result.get('yaml_links'):
        try:
            link = result['yaml_links'][0]  # 使用第一个链接
            filename = f"{download_dir}/shaoyou_yaml_{date_str}_{time_str}.yaml"
            response = requests.get(link, headers=headers, timeout=15)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            logger.info(f"已下载yaml订阅: {filename}")
            downloaded_files.append(filename)
            
            # 保存最新的订阅内容到固定文件
            latest_file = f"{download_dir}/shaoyou_yaml_latest.yaml"
            with open(latest_file, "wb") as f:
                f.write(response.content)
        except Exception as e:
            logger.exception(f"下载yaml订阅时出错: {e}")
    
    # 下载base64格式订阅
    if result.get('base64_links'):
        try:
            link = result['base64_links'][0]  # 使用第一个链接
            filename = f"{download_dir}/shaoyou_base64_{date_str}_{time_str}.txt"
            response = requests.get(link, headers=headers, timeout=15)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            logger.info(f"已下载base64订阅: {filename}")
            downloaded_files.append(filename)
            
            # 保存最新的订阅内容到固定文件
            latest_file = f"{download_dir}/shaoyou_base64_latest.txt"
            with open(latest_file, "wb") as f:
                f.write(response.content)
        except Exception as e:
            logger.exception(f"下载base64订阅时出错: {e}")
    
    # 下载mihomo格式订阅
    if result.get('mihomo_links'):
        try:
            link = result['mihomo_links'][0]  # 使用第一个链接
            filename = f"{download_dir}/shaoyou_mihomo_{date_str}_{time_str}.yaml"
            response = requests.get(link, headers=headers, timeout=15)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            logger.info(f"已下载mihomo订阅: {filename}")
            downloaded_files.append(filename)
            
            # 保存最新的订阅内容到固定文件
            latest_file = f"{download_dir}/shaoyou_mihomo_latest.yaml"
            with open(latest_file, "wb") as f:
                f.write(response.content)
        except Exception as e:
            logger.exception(f"下载mihomo订阅时出错: {e}")
    
    return downloaded_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取周润发公益免费v2ray节点订阅信息")
    parser.add_argument("--download", action="store_true", help="是否下载订阅文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    
    args = parser.parse_args()
    
    if args.verbose:
        # 设置日志级别为DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    print("开始爬取周润发公益免费v2ray节点订阅信息...")
    
    # 爬取订阅信息
    result = scrape_shaoyou()
    
    if result:
        # 显示爬取结果
        print("\n爬取结果:")
        print(f"标题: {result['title']}")
        print(f"爬取时间: {result['scrape_time']}")
        
        print("\nyaml格式订阅链接:")
        for link in result['yaml_links']:
            print(f"- {link}")
        
        print("\nbase64格式订阅链接:")
        for link in result['base64_links']:
            print(f"- {link}")
        
        print("\nmihomo格式订阅链接:")
        for link in result['mihomo_links']:
            print(f"- {link}")
        
        print("\n无需代理链接:")
        print("yaml格式:")
        for link in result['no_proxy_links']['yaml']:
            print(f"- {link}")
        
        print("base64格式:")
        for link in result['no_proxy_links']['base64']:
            print(f"- {link}")
        
        print("mihomo格式:")
        for link in result['no_proxy_links']['mihomo']:
            print(f"- {link}")
        
        # 如果需要下载订阅内容
        if args.download:
            print("\n开始下载订阅内容...")
            downloaded_files = download_subscription_files(result)
            if downloaded_files:
                print(f"成功下载 {len(downloaded_files)} 个订阅文件")
            else:
                print("下载订阅内容失败")
        
        print("\n爬取成功!")
    else:
        print("爬取失败") 