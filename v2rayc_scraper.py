#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
v2rayc.github.io 订阅链接爬虫
获取最新的Clash/V2ray/Sing-box订阅链接
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import logging
from datetime import datetime
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("v2rayc_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("v2rayc_scraper")

# GitHub镜像站点列表
GITHUB_RAW_MIRRORS = [
    "https://raw.githubusercontent.com",
    "https://raw.fastgit.org",
    "https://fastly.jsdelivr.net/gh",
    "https://gcore.jsdelivr.net/gh",
    "https://cdn.jsdelivr.net/gh"
]

def scrape_v2rayc():
    """
    爬取 v2rayc.github.io 网站的订阅链接
    
    返回:
    dict: 包含爬取结果的字典
    """
    # 主要从GitHub仓库README.md页面获取信息
    github_url = "https://github.com/v2rayc/v2rayc.github.io/blob/main/README.md"
    readme_url = "https://raw.githubusercontent.com/v2rayc/v2rayc.github.io/main/README.md"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info(f"开始爬取v2rayc.github.io订阅链接...")
        
        # 尝试直接获取README.md文件内容
        readme_content = None
        
        # 先尝试原始URL
        try:
            logger.info(f"尝试从原始URL获取README: {readme_url}")
            response = requests.get(readme_url, headers=headers, timeout=15)
            if response.status_code == 200:
                readme_content = response.text
                logger.info("成功从原始URL获取README内容")
        except Exception as e:
            logger.warning(f"从原始URL获取README失败: {e}")
        
        # 如果原始URL失败，尝试使用镜像站点
        if readme_content is None:
            for mirror in GITHUB_RAW_MIRRORS[1:]:  # 跳过第一个，因为已经尝试过了
                try:
                    # 根据不同镜像站构造URL
                    if "jsdelivr.net" in mirror:
                        mirror_url = f"{mirror}/v2rayc/v2rayc.github.io@main/README.md"
                    else:
                        mirror_url = f"{mirror}/v2rayc/v2rayc.github.io/main/README.md"
                    
                    logger.info(f"尝试从镜像站获取README: {mirror_url}")
                    response = requests.get(mirror_url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        readme_content = response.text
                        logger.info(f"成功从镜像站 {mirror} 获取README内容")
                        break
                except Exception as e:
                    logger.warning(f"从镜像站 {mirror} 获取README失败: {e}")
        
        # 如果所有镜像都失败，尝试获取仓库页面
        if readme_content is None:
            logger.warning(f"所有镜像站都无法获取README，尝试获取仓库页面")
            try:
                response = requests.get(github_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # 使用BeautifulSoup解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                readme_element = soup.find(id="readme")
                if readme_element:
                    readme_content = readme_element.get_text()
                    logger.info("成功从GitHub仓库页面获取README内容")
                else:
                    logger.warning("GitHub仓库页面中未找到README元素")
                    return None
            except Exception as e:
                logger.error(f"从GitHub仓库页面获取README失败: {e}")
                return None
        
        # 保存原始README内容用于调试
        with open("debug_v2rayc_readme.txt", "w", encoding="utf-8") as f:
            f.write(readme_content)
        logger.info("已保存README内容到debug_v2rayc_readme.txt文件")
        
        # 提取标题和日期信息
        title_pattern = re.compile(r'(\d+月\d+日.*?免费节点.*?订阅链接)')
        title_match = title_pattern.search(readme_content)
        title = title_match.group(1) if title_match else "v2rayc.github.io免费节点订阅"
        
        # 提取更新时间
        update_time_pattern = re.compile(r'更新时间\s*(20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})')
        update_time_match = update_time_pattern.search(readme_content)
        update_time = update_time_match.group(1) if update_time_match else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 提取日期信息（从链接或标题中）
        date_pattern = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})|(\d{8})')
        date_match = date_pattern.search(readme_content)
        if date_match:
            if date_match.group(4):  # 形如20250404
                date_str = date_match.group(4)
            else:  # 形如2025-04-04或2025/04/04
                year = date_match.group(1)
                month = date_match.group(2)
                day = date_match.group(3)
                date_str = f"{year}{month}{day}"
        else:
            date_str = datetime.now().strftime("%Y%m%d")
        
        # 提取Clash订阅链接
        clash_links = []
        clash_pattern = re.compile(r'https?://v2rayc\.github\.io/uploads/\d+/\d+/[^.\s]+\.yaml')
        clash_matches = clash_pattern.findall(readme_content)
        clash_links.extend(clash_matches)
        
        # 提取V2ray订阅链接
        v2ray_links = []
        v2ray_pattern = re.compile(r'https?://v2rayc\.github\.io/uploads/\d+/\d+/[^.\s]+\.txt')
        v2ray_matches = v2ray_pattern.findall(readme_content)
        v2ray_links.extend(v2ray_matches)
        
        # 提取Sing-box订阅链接
        singbox_links = []
        singbox_pattern = re.compile(r'https?://v2rayc\.github\.io/uploads/\d+/\d+/[^.\s]+\.json')
        singbox_matches = singbox_pattern.findall(readme_content)
        singbox_links.extend(singbox_matches)
        
        # 整理结果
        result = {
            "title": title,
            "date": date_str,
            "update_time": update_time,
            "clash_links": list(set(clash_links)),
            "v2ray_links": list(set(v2ray_links)),
            "singbox_links": list(set(singbox_links)),
            "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_url": github_url
        }
        
        # 检查是否获取到任何链接
        if not clash_links and not v2ray_links and not singbox_links:
            logger.warning("未找到任何订阅链接，尝试使用备用方式提取")
            
            # 尝试从内容中提取当前年月的链接格式
            current_year = datetime.now().strftime("%Y")
            current_month = datetime.now().strftime("%m")
            base_url = f"https://v2rayc.github.io/uploads/{current_year}/{current_month}/"
            
            # 构造可能的链接格式
            for i in range(5):  # 假设有0-4共5个链接
                clash_links.append(f"{base_url}{i}-{date_str}.yaml")
                v2ray_links.append(f"{base_url}{i}-{date_str}.txt")
            
            # Sing-box通常只有一个
            singbox_links.append(f"{base_url}{date_str}.json")
            
            # 更新结果
            result["clash_links"] = clash_links
            result["v2ray_links"] = v2ray_links
            result["singbox_links"] = singbox_links
            result["note"] = "链接由系统根据日期自动生成，可能需要手动验证可用性"
        
        # 保存结果
        save_result(result)
        
        logger.info(f"成功获取v2rayc.github.io订阅链接，日期: {date_str}")
        return result
        
    except requests.RequestException as e:
        logger.error(f"请求错误: {e}")
        return None
    except Exception as e:
        logger.exception(f"发生错误: {e}")
        return None

def save_result(result):
    """
    将爬取结果保存到文件
    """
    # 创建results/v2rayc目录(如果不存在)
    save_dir = "results/v2rayc"
    os.makedirs(save_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = result.get('date', current_time.strftime('%Y%m%d'))
    time_str = current_time.strftime('%H%M%S')
    
    # 保存JSON结果
    json_filename = f"{save_dir}/v2rayc_{date_str}_{time_str}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 保存文本结果
    txt_filename = f"{save_dir}/v2rayc_{date_str}_{time_str}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"标题: {result['title']}\n")
        f.write(f"更新时间: {result['update_time']}\n")
        f.write(f"爬取时间: {result['scrape_time']}\n")
        f.write(f"来源: {result['source_url']}\n\n")
        
        f.write("Clash订阅链接:\n")
        for i, link in enumerate(result['clash_links']):
            f.write(f"- [{i+1}] {link}\n")
        
        f.write("\nV2ray订阅链接:\n")
        for i, link in enumerate(result['v2ray_links']):
            f.write(f"- [{i+1}] {link}\n")
        
        f.write("\nSing-box订阅链接:\n")
        for i, link in enumerate(result['singbox_links']):
            f.write(f"- [{i+1}] {link}\n")
    
    # 保存最新的订阅链接到固定文件
    latest_json = f"{save_dir}/v2rayc_latest.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果保存到: {json_filename}")
    logger.info(f"结果保存到: {txt_filename}")
    logger.info(f"最新数据保存到: {latest_json}")

def download_subscription_files(result):
    """
    下载订阅文件
    
    参数:
    result (dict): 爬取结果字典
    
    返回:
    list: 下载成功的文件路径列表
    """
    if not result:
        logger.warning("订阅结果为空，无法下载")
        return []
    
    # 创建downloads/v2rayc目录(如果不存在)
    download_dir = "downloads/v2rayc"
    os.makedirs(download_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = result.get('date', current_time.strftime('%Y%m%d'))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    downloaded_files = []
    
    # 镜像站点替换规则
    mirror_patterns = [
        # v2rayc.github.io的域名替换规则
        (r'https?://v2rayc\.github\.io/', [
            "https://v2rayc.github.io/",  # 原始链接
            "https://v2rayc.netlify.app/", # Netlify镜像
            "https://cdn.jsdelivr.net/gh/v2rayc/v2rayc.github.io@gh-pages/", # JSDelivr镜像
            "https://fastly.jsdelivr.net/gh/v2rayc/v2rayc.github.io@gh-pages/" # Fastly镜像
        ])
    ]
    
    # 生成所有可能的镜像链接
    def generate_mirror_links(original_link):
        mirrors = [original_link]  # 始终包含原始链接
        for pattern, replacements in mirror_patterns:
            if re.match(pattern, original_link):
                for replacement in replacements[1:]:  # 排除第一个（原始链接）
                    mirror_link = re.sub(pattern, replacement, original_link)
                    mirrors.append(mirror_link)
                break
        return mirrors
    
    # 下载Clash配置
    for i, link in enumerate(result.get('clash_links', [])):
        try:
            filename = f"{download_dir}/v2rayc_clash_{i+1}_{date_str}.yaml"
            logger.info(f"开始下载Clash配置({i+1}/{len(result['clash_links'])}): {link}")
            
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            success = False
            
            # 获取所有可能的镜像链接
            mirror_links = generate_mirror_links(link)
            logger.info(f"准备尝试的链接列表: {mirror_links}")
            
            while retry_count < max_retries and not success:
                # 遍历所有可能的镜像站点
                for mirror_link in mirror_links:
                    try:
                        logger.info(f"尝试下载链接: {mirror_link}")
                        response = requests.get(mirror_link, headers=headers, timeout=15)
                        response.raise_for_status()
                        
                        # 检查内容是否有效（至少包含一些基本关键字）
                        content = response.text
                        if "proxies:" in content or "proxy-groups:" in content:
                            with open(filename, "wb") as f:
                                f.write(response.content)
                            
                            logger.info(f"已下载Clash配置: {filename}")
                            downloaded_files.append(filename)
                            
                            # 保存最新的Clash订阅
                            latest_file = f"{download_dir}/v2rayc_clash_{i+1}_latest.yaml"
                            with open(latest_file, "wb") as f:
                                f.write(response.content)
                            
                            success = True
                            break  # 成功下载，跳出镜像链接循环
                        else:
                            logger.warning(f"从 {mirror_link} 下载的Clash配置内容无效")
                    except Exception as mirror_e:
                        logger.warning(f"从 {mirror_link} 下载Clash配置时出错: {mirror_e}")
                
                if not success:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"所有镜像站点尝试失败，重试({retry_count}/{max_retries})")
                        time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            logger.exception(f"下载Clash配置时出错 ({link}): {e}")
    
    # 下载V2ray配置
    for i, link in enumerate(result.get('v2ray_links', [])):
        try:
            filename = f"{download_dir}/v2rayc_v2ray_{i+1}_{date_str}.txt"
            logger.info(f"开始下载V2ray配置({i+1}/{len(result['v2ray_links'])}): {link}")
            
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            success = False
            
            # 获取所有可能的镜像链接
            mirror_links = generate_mirror_links(link)
            logger.info(f"准备尝试的链接列表: {mirror_links}")
            
            while retry_count < max_retries and not success:
                # 遍历所有可能的镜像站点
                for mirror_link in mirror_links:
                    try:
                        logger.info(f"尝试下载链接: {mirror_link}")
                        response = requests.get(mirror_link, headers=headers, timeout=15)
                        response.raise_for_status()
                        
                        # V2ray配置通常是base64编码的，至少应有一定长度
                        if len(response.text) > 50:
                            with open(filename, "wb") as f:
                                f.write(response.content)
                            
                            logger.info(f"已下载V2ray配置: {filename}")
                            downloaded_files.append(filename)
                            
                            # 保存最新的V2ray订阅
                            latest_file = f"{download_dir}/v2rayc_v2ray_{i+1}_latest.txt"
                            with open(latest_file, "wb") as f:
                                f.write(response.content)
                            
                            success = True
                            break  # 成功下载，跳出镜像链接循环
                        else:
                            logger.warning(f"从 {mirror_link} 下载的V2ray配置内容过短，可能无效")
                    except Exception as mirror_e:
                        logger.warning(f"从 {mirror_link} 下载V2ray配置时出错: {mirror_e}")
                
                if not success:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"所有镜像站点尝试失败，重试({retry_count}/{max_retries})")
                        time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            logger.exception(f"下载V2ray配置时出错 ({link}): {e}")
    
    # 下载Sing-box配置
    for i, link in enumerate(result.get('singbox_links', [])):
        try:
            filename = f"{download_dir}/v2rayc_singbox_{i+1}_{date_str}.json"
            logger.info(f"开始下载Sing-box配置({i+1}/{len(result['singbox_links'])}): {link}")
            
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            success = False
            
            # 获取所有可能的镜像链接
            mirror_links = generate_mirror_links(link)
            logger.info(f"准备尝试的链接列表: {mirror_links}")
            
            while retry_count < max_retries and not success:
                # 遍历所有可能的镜像站点
                for mirror_link in mirror_links:
                    try:
                        logger.info(f"尝试下载链接: {mirror_link}")
                        response = requests.get(mirror_link, headers=headers, timeout=15)
                        response.raise_for_status()
                        
                        # 检查JSON格式是否有效
                        try:
                            json_content = response.json()
                            if json_content:  # 确保不是空JSON
                                with open(filename, "wb") as f:
                                    f.write(response.content)
                                
                                logger.info(f"已下载Sing-box配置: {filename}")
                                downloaded_files.append(filename)
                                
                                # 保存最新的Sing-box订阅
                                latest_file = f"{download_dir}/v2rayc_singbox_{i+1}_latest.json"
                                with open(latest_file, "wb") as f:
                                    f.write(response.content)
                                
                                success = True
                                break  # 成功下载，跳出镜像链接循环
                            else:
                                logger.warning(f"从 {mirror_link} 下载的Sing-box配置内容为空")
                        except json.JSONDecodeError:
                            logger.warning(f"从 {mirror_link} 下载的Sing-box配置不是有效的JSON")
                    except Exception as mirror_e:
                        logger.warning(f"从 {mirror_link} 下载Sing-box配置时出错: {mirror_e}")
                
                if not success:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"所有镜像站点尝试失败，重试({retry_count}/{max_retries})")
                        time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            logger.exception(f"下载Sing-box配置时出错 ({link}): {e}")
    
    # 汇总下载情况
    logger.info(f"v2rayc订阅下载完成，共成功下载 {len(downloaded_files)}/{len(result.get('clash_links', [])) + len(result.get('v2ray_links', [])) + len(result.get('singbox_links', []))} 个文件")
    
    # 保存下载记录
    download_record_file = f"{download_dir}/v2rayc_download_record_{date_str}.json"
    try:
        download_record = {
            "date": date_str,
            "download_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_links": {
                "clash": len(result.get('clash_links', [])),
                "v2ray": len(result.get('v2ray_links', [])),
                "singbox": len(result.get('singbox_links', []))
            },
            "downloaded_files": [os.path.basename(f) for f in downloaded_files],
            "success_rate": f"{len(downloaded_files)}/{len(result.get('clash_links', [])) + len(result.get('v2ray_links', [])) + len(result.get('singbox_links', []))}"
        }
        with open(download_record_file, "w", encoding="utf-8") as f:
            json.dump(download_record, f, ensure_ascii=False, indent=2)
        logger.info(f"下载记录已保存到: {download_record_file}")
    except Exception as e:
        logger.warning(f"保存下载记录时出错: {e}")
    
    return downloaded_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取v2rayc.github.io的订阅链接")
    parser.add_argument("--download", action="store_true", help="是否下载订阅文件")
    
    args = parser.parse_args()
    
    result = scrape_v2rayc()
    
    if result:
        print("\n爬取结果:")
        print(f"标题: {result['title']}")
        print(f"更新时间: {result['update_time']}")
        print(f"爬取时间: {result['scrape_time']}")
        
        print("\nClash订阅链接:")
        for i, link in enumerate(result['clash_links']):
            print(f"- [{i+1}] {link}")
        
        print("\nV2ray订阅链接:")
        for i, link in enumerate(result['v2ray_links']):
            print(f"- [{i+1}] {link}")
        
        print("\nSing-box订阅链接:")
        for i, link in enumerate(result['singbox_links']):
            print(f"- [{i+1}] {link}")
        
        if args.download:
            print("\n开始下载订阅文件...")
            downloaded_files = download_subscription_files(result)
            if downloaded_files:
                print(f"成功下载 {len(downloaded_files)} 个文件")
            else:
                print("下载订阅文件失败")
    else:
        print("爬取失败") 