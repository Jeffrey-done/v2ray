#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FreeV2.net 订阅链接爬虫
每天零点自动爬取订阅链接并保存
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("freev2_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("freev2_scraper")

def scrape_freev2():
    """
    爬取 FreeV2.net 网站的订阅链接
    
    返回:
    dict: 包含爬取结果的字典
    """
    url = "https://b.freev2.net/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://b.freev2.net/"
    }
    
    try:
        logger.info(f"开始爬取页面: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # 检查请求是否成功
        
        # 保存HTML内容以便调试
        with open("debug_freev2.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info("已保存HTML内容到debug_freev2.html文件")
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 优先查找class为btn的元素
        subscription_link = None
        
        # 直接查找带有data-clipboard-text属性的元素
        clipboard_elements = soup.find_all(attrs={"data-clipboard-text": True})
        
        if clipboard_elements:
            for element in clipboard_elements:
                clipboard_text = element.get('data-clipboard-text')
                if clipboard_text and (clipboard_text.startswith('http') or clipboard_text.startswith('vmess:')):
                    subscription_link = clipboard_text
                    logger.info(f"从data-clipboard-text属性中找到订阅链接: {subscription_link}")
                    break
        
        # 如果没有找到，尝试其他方法
        if not subscription_link:
            # 尝试查找class为btn的元素
            btn_elements = soup.find_all(class_='btn')
            for btn in btn_elements:
                clipboard_text = btn.get('data-clipboard-text')
                if clipboard_text:
                    subscription_link = clipboard_text
                    logger.info(f"从btn元素的data-clipboard-text属性中找到订阅链接: {subscription_link}")
                    break
        
        # 尝试多种方式查找"立即复制"按钮
        if not subscription_link:
            copy_button = soup.find('a', string='立即复制')
            
            if not copy_button:
                copy_button = soup.find('button', string='立即复制')
            
            if not copy_button:
                # 尝试查找包含"复制"文本的任何元素
                copy_buttons = soup.find_all(string=lambda text: text and ('复制' in text or '立即复制' in text))
                for text in copy_buttons:
                    parent = text.parent
                    if parent.get('data-clipboard-text'):
                        copy_button = parent
                        break
            
            if not copy_button:
                # 尝试查找class中包含button或btn的元素
                buttons = soup.find_all(['button', 'a'], class_=lambda c: c and ('button' in c.lower() or 'btn' in c.lower()))
                for btn in buttons:
                    if btn.text and '复制' in btn.text:
                        copy_button = btn
                        break
            
            if copy_button:
                logger.info(f"找到按钮: {copy_button}")
                # 获取按钮的data-clipboard-text属性，这通常包含订阅链接
                subscription_link = copy_button.get('data-clipboard-text')
                
                # 如果没有data-clipboard-text属性，尝试获取href属性
                if not subscription_link:
                    subscription_link = copy_button.get('href')
        
        # 如果仍然没有找到链接，尝试执行JavaScript获取
        if not subscription_link:
            logger.info("尝试通过脚本标签查找订阅链接")
            # 查找页面中的所有脚本标签
            scripts = soup.find_all('script')
            
            # 在脚本中搜索可能的订阅链接
            for script in scripts:
                if script.string:
                    # 查找类似于 data-clipboard-text="https://..." 或 copyText = "https://..." 的模式
                    matches = re.findall(r'data-clipboard-text=["\'](https?://[^"\']+)["\']', str(script))
                    if matches:
                        subscription_link = matches[0]
                        logger.info(f"在脚本中找到链接: {subscription_link}")
                        break
                    
                    # 查找其他可能的模式
                    match = re.search(r'(copyText|clipboard|subscribe|link|url)\s*=\s*["\']([^"\']+)["\']', str(script))
                    if match:
                        subscription_link = match.group(2)
                        logger.info(f"在脚本中找到链接: {subscription_link}")
                        break
        
        # 如果仍然没有找到链接，尝试从页面中提取所有链接
        if not subscription_link:
            logger.info("尝试从页面提取所有链接")
            all_links = []
            
            # 查找所有a标签的href属性
            for a in soup.find_all('a'):
                href = a.get('href')
                if href and (href.startswith('http') or href.startswith('vmess:') or href.startswith('ss:')):
                    all_links.append(href)
            
            # 在页面文本中搜索base64编码的链接格式
            base64_pattern = r'[A-Za-z0-9+/=]{30,}'
            base64_matches = re.findall(base64_pattern, response.text)
            
            # 在页面文本中搜索subscription或者订阅相关的链接
            sub_link_pattern = r'https?://[^\s\'"\)>]+(?:subscribe|sub|clash|v2ray|vmess|trojan)[^\s\'"\)<]+'
            sub_matches = re.findall(sub_link_pattern, response.text)
            
            # 合并所有可能的链接
            potential_links = all_links + base64_matches + sub_matches
            
            if potential_links:
                # 选择最有可能是订阅链接的那个
                for link in potential_links:
                    if 'subscribe' in link.lower() or 'sub' in link.lower() or 'clash' in link.lower() or 'v2ray' in link.lower():
                        subscription_link = link
                        logger.info(f"找到可能的订阅链接: {subscription_link}")
                        break
                
                # 如果没有找到明显的订阅链接，使用第一个链接
                if not subscription_link and potential_links:
                    subscription_link = potential_links[0]
                    logger.info(f"使用第一个可能的链接: {subscription_link}")
        
        if not subscription_link:
            logger.warning("无法获取订阅链接")
            return None
        
        # 获取网站上的其他信息
        info_text = ""
        
        # 尝试找到hero-body类的div
        info_section = soup.find('div', class_='hero-body')
        
        # 如果找不到hero-body，尝试找到页面中的所有段落
        if not info_section:
            # 尝试查找主要内容区域
            main_content = soup.find('main')
            if main_content:
                info_section = main_content
            else:
                info_section = soup
        
        # 提取段落文本
        paragraphs = info_section.find_all('p')
        for p in paragraphs:
            if p.text.strip():
                info_text += p.text.strip() + "\n"
        
        # 如果没有找到段落，尝试提取div文本
        if not info_text:
            for div in info_section.find_all('div'):
                if div.text.strip() and len(div.text.strip()) < 200:  # 避免提取过长的文本
                    info_text += div.text.strip() + "\n"
        
        # 整理结果
        result = {
            "subscription_link": subscription_link,
            "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_url": url,
            "info": info_text.strip()
        }
        
        # 保存结果
        save_result(result)
        
        logger.info(f"成功获取订阅链接: {subscription_link[:30]}...")
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
    # 创建results/freev2目录(如果不存在)
    save_dir = "results/freev2"
    os.makedirs(save_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = current_time.strftime('%Y%m%d')
    time_str = current_time.strftime('%H%M%S')
    
    # 保存JSON结果
    json_filename = f"{save_dir}/freev2_{date_str}_{time_str}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 保存文本结果
    txt_filename = f"{save_dir}/freev2_{date_str}_{time_str}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"爬取时间: {result['scrape_time']}\n")
        f.write(f"来源: {result['source_url']}\n\n")
        f.write(f"订阅链接:\n{result['subscription_link']}\n\n")
        f.write(f"网站信息:\n{result['info']}\n")
    
    # 保存当前最新的订阅链接到固定文件
    latest_txt = f"{save_dir}/freev2_latest.txt"
    with open(latest_txt, "w", encoding="utf-8") as f:
        f.write(result['subscription_link'])
    
    logger.info(f"结果保存到: {json_filename}")
    logger.info(f"结果保存到: {txt_filename}")
    logger.info(f"最新订阅链接保存到: {latest_txt}")

def download_subscription_file(subscription_link):
    """
    下载订阅文件内容
    """
    if not subscription_link:
        logger.warning("订阅链接为空，无法下载")
        return None
    
    # 创建downloads/freev2目录(如果不存在)
    download_dir = "downloads/freev2"
    os.makedirs(download_dir, exist_ok=True)
    
    current_time = datetime.now()
    date_str = current_time.strftime('%Y%m%d')
    time_str = current_time.strftime('%H%M%S')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        # 下载订阅文件
        response = requests.get(subscription_link, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 获取文件格式（通常是base64编码的内容）
        content = response.text
        
        # 保存到文件
        filename = f"{download_dir}/freev2_subscription_{date_str}_{time_str}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 保存最新的订阅内容到固定文件
        latest_file = f"{download_dir}/freev2_subscription_latest.txt"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"订阅内容已下载到: {filename}")
        return filename
    
    except Exception as e:
        logger.exception(f"下载订阅内容时出错: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取 FreeV2.net 的订阅链接")
    parser.add_argument("--download", action="store_true", help="是否下载订阅内容")
    
    args = parser.parse_args()
    
    # 爬取订阅链接
    result = scrape_freev2()
    
    if result:
        # 显示爬取结果
        print("\n爬取结果:")
        print(f"订阅链接: {result['subscription_link']}")
        print(f"爬取时间: {result['scrape_time']}")
        
        # 如果需要下载订阅内容
        if args.download:
            print("\n开始下载订阅内容...")
            download_file = download_subscription_file(result['subscription_link'])
            if download_file:
                print(f"订阅内容已下载到: {download_file}")
            else:
                print("下载订阅内容失败")
    else:
        print("爬取失败") 