#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
整合GitHub监控和datiya爬取功能的脚本
监控https://github.com/OpenRunner/clash-freenode仓库中的日期变化
并根据新的日期从free.datiya.com爬取对应的数据
同时生成一个美观的HTML页面展示所有爬取的结果
新增: 每天零点自动爬取FreeV2.net网站的订阅链接
"""

import logging
import time
import schedule
import os
import argparse
import json
import re
import sys
import random
import requests
from datetime import datetime
from github_monitor import get_all_dates_to_process, get_new_dates, get_last_processed_date, save_last_processed_date
from datiya_scraper import scrape_datiya, download_subscription_files

# 导入FreeV2爬虫
try:
    from freev2_scraper import scrape_freev2, download_subscription_file
    FREEV2_ENABLED = True
except ImportError:
    FREEV2_ENABLED = False
    print("未找到freev2_scraper模块，FreeV2.net爬取功能将不可用")

# 导入周润发公益v2ray节点爬虫
try:
    from shaoyou_scraper import scrape_shaoyou, download_subscription_files as download_shaoyou_files
    SHAOYOU_ENABLED = True
except ImportError:
    SHAOYOU_ENABLED = False
    print("未找到shaoyou_scraper模块，周润发公益v2ray节点爬取功能将不可用")

# 导入日日更新节点爬虫
RIPAO_ENABLED = True
try:
    import ripao_scraper
except ImportError:
    RIPAO_ENABLED = False
    print("未找到ripao_scraper模块，日日更新节点爬取功能将不可用")

# 导入v2rayc节点爬虫
V2RAYC_ENABLED = True
try:
    import v2rayc_scraper
    V2RAYC_ENABLED = True
except ImportError:
    V2RAYC_ENABLED = False
    print("未找到v2rayc_scraper模块，v2rayc节点爬取功能将不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitor_and_fetch.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("monitor_and_fetch")

# 创建必要的目录
os.makedirs("results", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("web", exist_ok=True)
os.makedirs("results/bestclash", exist_ok=True)

def fetch_with_retry(date, max_retries=3, retry_delay=5):
    """
    带重试机制的爬取函数
    
    参数:
    date (str): 要爬取的日期，格式为YYYYMMDD
    max_retries (int): 最大重试次数
    retry_delay (int): 重试间隔，单位为秒
    
    返回:
    dict: 爬取结果，如果失败则返回None
    """
    for attempt in range(max_retries):
        try:
            result = scrape_datiya(date)
            if result:
                return result
            logger.warning(f"爬取日期 {date} 返回空结果 (尝试 {attempt+1}/{max_retries})")
        except Exception as e:
            logger.warning(f"爬取日期 {date} 出错: {e} (尝试 {attempt+1}/{max_retries})")
        
        if attempt < max_retries - 1:
            # 添加一些随机性，避免爬取频率过高
            jitter = random.uniform(0.5, 1.5)
            sleep_time = retry_delay * jitter
            logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
            time.sleep(sleep_time)
    
    return None

def fetch_and_process(date_tuples, download=True, force_update=False):
    """
    爬取并处理指定日期的数据
    
    参数:
    date_tuples (list): 要处理的日期列表，格式为 [(YYYYMMDD, node_count), ...]
    download (bool): 是否下载订阅文件
    force_update (bool): 是否强制更新已有数据
    
    返回:
    list: 成功处理的日期列表
    """
    if not date_tuples:
        logger.info("没有需要处理的日期")
        return []
    
    date_strings = [f"{dt[0][:4]}-{dt[0][4:6]}-{dt[0][6:8]}({dt[1]})" for dt in date_tuples]
    logger.info(f"开始处理 {len(date_tuples)} 个日期: {', '.join(date_strings)}")
    
    # 检查已有的结果文件
    existing_results = {}
    if os.path.exists("web/data.json"):
        try:
            with open("web/data.json", "r", encoding="utf-8") as f:
                existing_results = json.load(f)
        except Exception as e:
            logger.exception(f"读取已有数据时出错: {e}")
    
    success_dates = []
    all_results = existing_results.copy()
    error_count = 0
    
    for date_tuple in date_tuples:
        date = date_tuple[0]
        node_count = date_tuple[1]
        
        # 格式化日期，用连字符分隔
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        
        # 如果已经处理过且不是强制更新，则跳过
        if date in existing_results and not force_update:
            logger.info(f"日期 {formatted_date} 已处理过，跳过")
            success_dates.append(date)
            continue
        
        try:
            # 添加处理进度信息
            current_index = date_tuples.index(date_tuple) + 1
            logger.info(f"处理进度: {current_index}/{len(date_tuples)} - 开始爬取日期 {formatted_date} 的数据...")
            
            # 使用带重试的爬取函数
            result = fetch_with_retry(date)
            
            if result:
                logger.info(f"成功爬取 {formatted_date} 的数据: {result['title']}")
                
                if download:
                    logger.info(f"开始下载 {formatted_date} 的订阅文件...")
                    try:
                        downloaded_files = download_subscription_files(result)
                        logger.info(f"成功下载 {len(downloaded_files)} 个文件")
                    except Exception as e:
                        logger.exception(f"下载 {formatted_date} 的订阅文件出错: {e}")
                
                # 保存结果到all_results
                all_results[date] = {
                    "date": formatted_date,
                    "title": result["title"],
                    "update_time": result["update_time"],
                    "clash_links": result["clash_links"],
                    "v2ray_links": result["v2ray_links"],
                    "nodes_info": result["nodes_info"],
                    "expected_node_count": node_count,  # 从GitHub获取的预期节点数
                    "scrape_time": result["scrape_time"]
                }
                
                success_dates.append(date)
                
                # 每爬取一定数量的日期就保存一次结果，避免全部失败
                if len(success_dates) % 3 == 0:
                    save_results_to_json(all_results)
                    logger.info(f"已保存当前进度 ({len(success_dates)} 个日期)")
            else:
                logger.warning(f"爬取日期 {formatted_date} 的数据失败")
                error_count += 1
                
                # 如果连续多次失败，可能是被限制了，暂停一段时间
                if error_count >= 3:
                    logger.warning(f"连续失败 {error_count} 次，暂停60秒")
                    time.sleep(60)
                    error_count = 0
        except Exception as e:
            logger.exception(f"处理日期 {formatted_date} 时出错: {e}")
            error_count += 1
            
            # 如果连续多次异常，暂停一段时间
            if error_count >= 3:
                logger.warning(f"连续异常 {error_count} 次，暂停60秒")
                time.sleep(60)
                error_count = 0
    
    if success_dates:
        logger.info(f"成功处理 {len(success_dates)} 个日期")
        
        # 保存所有结果到JSON文件
        save_results_to_json(all_results)
        
        # 生成HTML页面
        generate_html_page(all_results)
        
        # 保存最新处理的日期
        if success_dates:
            latest_date = sorted(success_dates, reverse=True)[0]
            save_last_processed_date(latest_date)
    else:
        logger.warning("没有成功处理任何日期")
    
    return success_dates

# 新增: 每天零点爬取FreeV2.net的任务
def fetch_freev2():
    """
    爬取FreeV2.net网站的订阅链接
    """
    logger.info("开始爬取FreeV2.net...")
    
    try:
        # 爬取订阅链接
        result = scrape_freev2()
        
        if not result:
            logger.error("爬取FreeV2.net失败")
            return False
        
        logger.info(f"成功获取FreeV2.net订阅链接")
        
        # 下载订阅内容
        if 'subscription_link' in result and result['subscription_link']:
            download_file = download_subscription_file(result['subscription_link'])
            if download_file:
                logger.info(f"成功下载FreeV2.net订阅内容: {download_file}")
            else:
                logger.warning("下载FreeV2.net订阅内容失败")
        else:
            logger.error("未找到可用的订阅链接")
            
        return True
    except Exception as e:
        logger.exception(f"下载FreeV2.net订阅内容时出错: {e}")
        return False

# 新增：获取BestClash的订阅链接
def fetch_bestclash():
    """
    获取BestClash的订阅链接和信息
    
    返回:
    dict: 包含订阅链接和信息的字典
    """
    logger.info("开始获取BestClash订阅...")
    
    # BestClash的订阅链接
    github_url = "https://raw.githubusercontent.com/PuddinCat/BestClash/refs/heads/main/proxies.yaml"
    mirror_url = "https://ghfile.geekertao.top/https://github.com/PuddinCat/BestClash/blob/main/proxies.yaml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    result = {
        "github_link": github_url,
        "mirror_link": mirror_url,
        "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_url": "https://github.com/PuddinCat/BestClash",
        "description": "免费Clash代理！自动从网上爬取最快的代理，每30分钟更新！"
    }
    
    # 将结果保存到文件中
    try:
        # 检查链接是否可访问
        try:
            response = requests.get(github_url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info("GitHub链接可访问")
        except:
            logger.warning("GitHub链接不可访问，建议使用国内镜像")
            
        # 保存JSON结果
        json_filename = f"results/bestclash/bestclash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 保存文本结果
        txt_filename = f"results/bestclash/bestclash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(f"BestClash 免费Clash代理\n")
            f.write(f"更新频率: 每30分钟\n")
            f.write(f"爬取时间: {result['scrape_time']}\n")
            f.write(f"来源: {result['source_url']}\n\n")
            f.write("GitHub 订阅链接:\n")
            f.write(f"{github_url}\n\n")
            f.write("国内镜像 订阅链接:\n")
            f.write(f"{mirror_url}\n")
        
        # 保存最新链接
        latest_txt = "results/bestclash/bestclash_latest.txt"
        with open(latest_txt, "w", encoding="utf-8") as f:
            f.write(github_url)
        
        logger.info(f"结果保存到: {json_filename}")
        logger.info(f"结果保存到: {txt_filename}")
        logger.info(f"最新订阅链接保存到: {latest_txt}")
        
        return result
    except Exception as e:
        logger.exception(f"获取BestClash订阅时出错: {e}")
        return None

# 新增：获取周润发公益v2ray节点订阅
def fetch_shaoyou():
    """
    获取周润发公益v2ray节点订阅信息
    
    返回:
    dict: 包含订阅链接和信息的字典
    """
    logger.info("开始获取周润发公益v2ray节点订阅...")
    
    try:
        # 爬取订阅信息
        result = scrape_shaoyou()
        
        if not result:
            logger.error("爬取周润发公益v2ray节点订阅失败")
            return None
        
        logger.info(f"成功获取周润发公益v2ray节点订阅信息")
        
        # 下载订阅文件
        if SHAOYOU_ENABLED:
            download_shaoyou_files(result)
            logger.info("成功下载周润发公益v2ray节点订阅文件")
        else:
            logger.warning("周润发公益v2ray节点爬取功能未启用，跳过下载")
            
        return result
    except Exception as e:
        logger.exception(f"获取周润发公益v2ray节点订阅时出错: {e}")
        return None

def save_results_to_json(results):
    """
    保存所有结果到JSON文件
    
    参数:
    results (dict): 所有爬取结果
    """
    try:
        with open("web/data.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("已保存所有结果到 web/data.json")
    except Exception as e:
        logger.exception(f"保存结果到JSON文件时出错: {e}")
        # 尝试创建备份
        try:
            backup_file = f"web/data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"已创建备份文件: {backup_file}")
        except:
            pass

def generate_html_page(results):
    """
    生成HTML页面展示所有爬取结果
    
    参数:
    results (dict): 爬取结果字典，格式为 {date: result_dict}
    """
    try:
        logger.info("开始生成HTML页面...")
        
        # 创建web目录(如果不存在)
        if not os.path.exists("web"):
            os.makedirs("web")
        
        # 获取FreeV2.net最新订阅链接
        freev2_latest_file = "results/freev2/freev2_latest.txt"
        freev2_latest_json = None
        freev2_link = None
        
        # 查找最新的FreeV2 JSON结果文件
        freev2_dir = "results/freev2"
        if os.path.exists(freev2_dir):
            json_files = [f for f in os.listdir(freev2_dir) if f.endswith('.json')]
            if json_files:
                # 按文件名排序，获取最新的文件
                latest_json = sorted(json_files, reverse=True)[0]
                freev2_latest_json = os.path.join(freev2_dir, latest_json)
        
        # 读取FreeV2.net的订阅链接
        freev2_data = None
        if os.path.exists(freev2_latest_file):
            try:
                with open(freev2_latest_file, 'r', encoding='utf-8') as f:
                    freev2_link = f.read().strip()
                logger.info(f"获取到FreeV2.net最新订阅链接: {freev2_link}")
            except Exception as e:
                logger.error(f"读取FreeV2.net链接文件时出错: {e}")
        
        # 如果有JSON文件，读取更多信息
        if freev2_latest_json and os.path.exists(freev2_latest_json):
            try:
                with open(freev2_latest_json, 'r', encoding='utf-8') as f:
                    freev2_data = json.load(f)
                logger.info(f"获取到FreeV2.net订阅数据")
            except Exception as e:
                logger.error(f"读取FreeV2.net JSON文件时出错: {e}")
        
        # 新增：获取BestClash订阅链接
        bestclash_latest_file = "results/bestclash/bestclash_latest.txt"
        bestclash_latest_json = None
        bestclash_github_link = None
        bestclash_mirror_link = None
        bestclash_data = None
        
        # 查找最新的BestClash JSON结果文件
        bestclash_dir = "results/bestclash"
        if os.path.exists(bestclash_dir):
            json_files = [f for f in os.listdir(bestclash_dir) if f.endswith('.json')]
            if json_files:
                # 按文件名排序，获取最新的文件
                latest_json = sorted(json_files, reverse=True)[0]
                bestclash_latest_json = os.path.join(bestclash_dir, latest_json)
        
        # 读取BestClash链接和数据
        if os.path.exists(bestclash_latest_file):
            try:
                with open(bestclash_latest_file, 'r', encoding='utf-8') as f:
                    bestclash_github_link = f.read().strip()
                logger.info(f"获取到BestClash GitHub订阅链接")
            except Exception as e:
                logger.error(f"读取BestClash链接文件时出错: {e}")
        
        # 如果有JSON文件，读取更多信息
        if bestclash_latest_json and os.path.exists(bestclash_latest_json):
            try:
                with open(bestclash_latest_json, 'r', encoding='utf-8') as f:
                    bestclash_data = json.load(f)
                    bestclash_mirror_link = bestclash_data.get("mirror_link", "")
                logger.info(f"获取到BestClash订阅数据")
            except Exception as e:
                logger.error(f"读取BestClash JSON文件时出错: {e}")
        
        # 没有BestClash数据时，尝试获取一次
        if not bestclash_data:
            try:
                bestclash_data = fetch_bestclash()
                if bestclash_data:
                    bestclash_github_link = bestclash_data.get("github_link", "")
                    bestclash_mirror_link = bestclash_data.get("mirror_link", "")
                    logger.info("成功获取BestClash订阅数据")
            except Exception as e:
                logger.error(f"自动获取BestClash订阅时出错: {e}")
        
        # 新增：获取周润发公益v2ray节点订阅链接
        shaoyou_latest_file = "results/shaoyou/shaoyou_latest.txt"
        shaoyou_latest_json = None
        shaoyou_yaml_link = None
        shaoyou_base64_link = None
        shaoyou_mihomo_link = None
        shaoyou_no_proxy_link = None
        shaoyou_data = None
        
        # 查找最新的周润发公益v2ray JSON结果文件
        shaoyou_dir = "results/shaoyou"
        if os.path.exists(shaoyou_dir):
            json_files = [f for f in os.listdir(shaoyou_dir) if f.endswith('.json') and f != 'shaoyou_latest.json']
            if json_files:
                # 按文件名排序，获取最新的文件
                latest_json = sorted(json_files, reverse=True)[0]
                shaoyou_latest_json = os.path.join(shaoyou_dir, latest_json)
        
        # 读取周润发公益v2ray的订阅链接
        if os.path.exists(shaoyou_latest_file):
            try:
                with open(shaoyou_latest_file, 'r', encoding='utf-8') as f:
                    shaoyou_links = json.load(f)
                    shaoyou_yaml_link = shaoyou_links.get('yaml', '')
                    shaoyou_base64_link = shaoyou_links.get('base64', '')
                    shaoyou_mihomo_link = shaoyou_links.get('mihomo', '')
                    shaoyou_no_proxy_link = shaoyou_links.get('no_proxy_yaml', '')
                logger.info(f"获取到周润发公益v2ray节点订阅链接")
            except Exception as e:
                logger.error(f"读取周润发公益v2ray链接文件时出错: {e}")
        
        # 如果有JSON文件，读取更多信息
        if shaoyou_latest_json and os.path.exists(shaoyou_latest_json):
            try:
                with open(shaoyou_latest_json, 'r', encoding='utf-8') as f:
                    shaoyou_data = json.load(f)
                logger.info(f"获取到周润发公益v2ray节点订阅数据")
            except Exception as e:
                logger.error(f"读取周润发公益v2ray JSON文件时出错: {e}")
        
        # 没有周润发公益v2ray数据时，尝试获取一次
        if not shaoyou_data and SHAOYOU_ENABLED:
            try:
                shaoyou_data = fetch_shaoyou()
                if shaoyou_data:
                    shaoyou_yaml_link = shaoyou_data.get('yaml_links', [])[0] if shaoyou_data.get('yaml_links') else ""
                    shaoyou_base64_link = shaoyou_data.get('base64_links', [])[0] if shaoyou_data.get('base64_links') else ""
                    shaoyou_mihomo_link = shaoyou_data.get('mihomo_links', [])[0] if shaoyou_data.get('mihomo_links') else ""
                    no_proxy_links = shaoyou_data.get('no_proxy_links', {})
                    shaoyou_no_proxy_link = no_proxy_links.get('yaml', [])[0] if no_proxy_links.get('yaml') else ""
                    logger.info("成功获取周润发公益v2ray节点订阅数据")
            except Exception as e:
                logger.error(f"自动获取周润发公益v2ray节点订阅时出错: {e}")
        
        # 新增：获取日日更新节点订阅链接
        ripao_latest_json = "results/ripao/ripao_latest.json"
        ripao_data = None
        ripao_clash_link = None
        ripao_v2ray_link = None
        ripao_clash_mirror = None
        ripao_v2ray_mirror = None
        
        # 读取日日更新节点订阅数据
        if os.path.exists(ripao_latest_json):
            try:
                with open(ripao_latest_json, 'r', encoding='utf-8') as f:
                    ripao_data = json.load(f)
                    ripao_clash_link = ripao_data.get('clash_link', '')
                    ripao_v2ray_link = ripao_data.get('v2ray_link', '')
                    ripao_clash_mirror = ripao_data.get('clash_mirror', '')
                    ripao_v2ray_mirror = ripao_data.get('v2ray_mirror', '')
                logger.info(f"获取到日日更新节点订阅数据")
            except Exception as e:
                logger.error(f"读取日日更新节点JSON文件时出错: {e}")
        
        # 如果没有数据，尝试获取一次
        if not ripao_data and RIPAO_ENABLED:
            try:
                ripao_data = fetch_ripao()
                if ripao_data:
                    ripao_clash_link = ripao_data.get('clash_link', '')
                    ripao_v2ray_link = ripao_data.get('v2ray_link', '')
                    ripao_clash_mirror = ripao_data.get('clash_mirror', '')
                    ripao_v2ray_mirror = ripao_data.get('v2ray_mirror', '')
                    logger.info("成功获取日日更新节点订阅数据")
            except Exception as e:
                logger.error(f"自动获取日日更新节点订阅时出错: {e}")
        
        # 新增：获取v2rayc.github.io订阅链接
        v2rayc_latest_json = "results/v2rayc/v2rayc_latest.json"
        v2rayc_data = None
        v2rayc_clash_links = []
        v2rayc_v2ray_links = []
        v2rayc_singbox_links = []
        v2rayc_update_time = "未知"
        
        # 读取v2rayc.github.io订阅数据
        if os.path.exists(v2rayc_latest_json):
            try:
                with open(v2rayc_latest_json, 'r', encoding='utf-8') as f:
                    v2rayc_data = json.load(f)
                    v2rayc_clash_links = v2rayc_data.get('clash_links', [])
                    v2rayc_v2ray_links = v2rayc_data.get('v2ray_links', [])
                    v2rayc_singbox_links = v2rayc_data.get('singbox_links', [])
                    v2rayc_update_time = v2rayc_data.get('update_time', v2rayc_data.get('scrape_time', '未知'))
                    logger.info(f"获取到v2rayc.github.io订阅数据")
            except Exception as e:
                logger.error(f"读取v2rayc.github.io JSON文件时出错: {e}")
        
        # 如果没有数据，尝试获取一次
        if not v2rayc_data and V2RAYC_ENABLED:
            try:
                v2rayc_data = fetch_v2rayc()
                if v2rayc_data:
                    v2rayc_clash_links = v2rayc_data.get('clash_links', [])
                    v2rayc_v2ray_links = v2rayc_data.get('v2ray_links', [])
                    v2rayc_singbox_links = v2rayc_data.get('singbox_links', []) 
                    v2rayc_update_time = v2rayc_data.get('update_time', v2rayc_data.get('scrape_time', '未知'))
                    logger.info("成功获取v2rayc.github.io订阅数据")
            except Exception as e:
                logger.error(f"自动获取v2rayc.github.io订阅时出错: {e}")
        
        # 如果仍然没有数据，使用默认空数据
        if not v2rayc_data:
            v2rayc_data = {
                "title": "v2rayc.github.io节点",
                "clash_links": [],
                "v2ray_links": [],
                "singbox_links": [],
                "update_time": "未知",
                "scrape_time": "未知",
                "date": "未知",
                "source_url": "https://github.com/v2rayc/v2rayc.github.io"
            }
        
        # 计算节点和订阅统计数据
        total_dates = 0
        total_clash_links = 0
        total_v2ray_links = 0
        total_nodes = 0
        
        try:
            if isinstance(results, dict) and any(isinstance(results.get(key), dict) for key in results):
                total_dates = len([key for key in results if isinstance(results[key], dict)])
                total_clash_links = sum(len(results[date].get('clash_links', [])) for date in results if isinstance(results[date], dict))
                total_v2ray_links = sum(len(results[date].get('v2ray_links', [])) for date in results if isinstance(results[date], dict))
                
                for date in results:
                    if not isinstance(results[date], dict):
                        continue
                    
                    nodes_info = results[date].get('nodes_info', {})
                    if isinstance(nodes_info, list):
                        total_nodes += len(nodes_info)
                    elif isinstance(nodes_info, dict):
                        # 尝试提取节点数量
                        for key, value in nodes_info.items():
                            if '可用节点' in key or '节点' in key:
                                try:
                                    # 提取数字
                                    node_count = re.search(r'\d+', value)
                                    if node_count:
                                        total_nodes += int(node_count.group())
                                        break
                                except:
                                    pass
        except Exception as e:
            logger.exception(f"计算统计数据时出错: {e}")
            # 使用默认值
            total_dates = 0
            total_clash_links = 0
            total_v2ray_links = 0
            total_nodes = 0
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clash/V2Ray 免费节点订阅</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.3/font/bootstrap-icons.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/animate.css@4.1.1/animate.min.css">
    <style>
        :root {{
            --primary-color: #0d6efd;
            --secondary-color: #6c757d;
            --success-color: #198754;
            --info-color: #0dcaf0;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --light-color: #f8f9fa;
            --dark-color: #212529;
        }}
        
        body {{
            background-color: #f0f2f5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .navbar {{
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .card {{
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            border: none;
            border-radius: 10px;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }}
        
        .card-header {{
            font-weight: bold;
            background-color: rgba(13, 110, 253, 0.05);
            border-radius: 10px 10px 0 0 !important;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }}
        
        .badge {{
            margin-right: 5px;
            padding: 0.5em 0.8em;
            font-weight: 500;
            border-radius: 6px;
        }}
        
        .stats-card {{
            background-color: #fff;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            border-top: 3px solid var(--primary-color);
            transition: all 0.3s ease;
        }}
        
        .stats-card:hover {{
            box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        }}
        
        .copy-btn {{
            cursor: pointer;
            transition: all 0.2s;
            border-radius: 0 5px 5px 0;
        }}
        
        .copy-btn:hover {{
            background-color: var(--primary-color);
            color: white;
        }}
        
        .section-title {{
            margin-top: 50px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--primary-color);
            font-weight: 600;
            color: var(--dark-color);
            position: relative;
        }}
        
        .section-title:after {{
            content: '';
            position: absolute;
            width: 60px;
            height: 3px;
            background-color: var(--warning-color);
            bottom: -2px;
            left: 0;
        }}
        
        .highlight-card {{
            border-left: 4px solid var(--primary-color);
            transition: all 0.3s ease;
        }}
        
        .highlight-card:hover {{
            border-left-color: var(--warning-color);
        }}
        
        footer {{
            margin-top: 70px;
            padding: 30px 0;
            background-color: #fff;
            border-top: 1px solid #e9ecef;
            box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
        }}
        
        .social-icons {{
            font-size: 1.5rem;
            margin-right: 15px;
            transition: all 0.3s ease;
            color: var(--secondary-color);
        }}
        
        .social-icons:hover {{
            color: var(--primary-color);
            transform: scale(1.2);
        }}
        
        .accordion-button:not(.collapsed) {{
            background-color: rgba(13, 110, 253, 0.1);
            font-weight: 500;
        }}
        
        .form-control:focus {{
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.15);
        }}
        
        .alert {{
            border-radius: 10px;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .alert-info {{
            background-color: rgba(13, 202, 240, 0.1);
            color: #087990;
        }}
        
        .node-info-section {{
            background-color: rgba(248, 249, 250, 0.7);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        
        .subscription-button {{
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .subscription-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 10px rgba(0,0,0,0.1);
        }}
        
        .input-group {{
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .input-group .form-control {{
            border-right: none;
        }}
        
        .top-banner {{
            background: linear-gradient(45deg, #0d6efd, #0dcaf0);
            color: white;
            padding: 15px 0;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        
        .stats-icon {{
            font-size: 1.8rem;
            margin-bottom: 10px;
            color: var(--primary-color);
        }}
        
        .animated-hover {{
            transition: all 0.3s ease;
        }}
        
        .animated-hover:hover {{
            transform: translateY(-3px);
        }}
    </style>
</head>
<body class="animate__animated animate__fadeIn">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center" href="#">
                <i class="bi bi-globe2 me-2"></i> 
                <span>Clash/V2Ray 免费节点订阅</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link active" href="#top">
                            <i class="bi bi-house-door-fill me-1"></i> 首页
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#freev2">
                            <i class="bi bi-star-fill me-1"></i> FreeV2.net
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#bestclash">
                            <i class="bi bi-star-fill me-1"></i> BestClash
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#shaoyou">
                            <i class="bi bi-clock-history me-1"></i> 周润发公益v2ray
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#ripao">
                            <i class="bi bi-bookmark-star-fill me-1"></i> 日日更新节点
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#v2rayc">
                            <i class="bi bi-lightning-charge-fill me-1"></i> V2rayc订阅
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#datiya">
                            <i class="bi bi-calendar-date me-1"></i> 按日期查看
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-5">
        <div class="top-banner p-4 animate__animated animate__fadeInDown">
            <div class="row align-items-center">
                <div class="col-md-8">
                    <h2><i class="bi bi-lightning-charge-fill me-2"></i> 免费节点集合</h2>
                    <p class="mb-0">汇集多个来源的免费Clash/V2Ray节点，定时更新</p>
                </div>
                <div class="col-md-4 text-md-end">
                    <p class="mb-0">
                        <i class="bi bi-clock-history me-1"></i> 
                        更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    </p>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-4">
                <div class="stats-card animate__animated animate__fadeInLeft">
                    <div class="text-center stats-icon">
                        <i class="bi bi-calendar-check"></i>
                    </div>
                    <h5 class="text-center mb-3">日期统计</h5>
                    <div class="text-center">
                        <div class="mb-3">
                            <span class="badge bg-primary rounded-pill fs-6">{total_dates} 个日期</span>
                        </div>
                        <p class="mb-1">最早日期: <span class="badge bg-secondary">{min(results.keys()) if results else 'N/A'}</span></p>
                        <p>最新日期: <span class="badge bg-secondary">{max(results.keys()) if results else 'N/A'}</span></p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stats-card animate__animated animate__fadeInUp">
                    <div class="text-center stats-icon">
                        <i class="bi bi-diagram-3"></i>
                    </div>
                    <h5 class="text-center mb-3">订阅统计</h5>
                    <div class="text-center">
                        <div class="mb-3">
                            <span class="badge bg-primary rounded-pill fs-6">{total_clash_links + total_v2ray_links} 个链接</span>
                        </div>
                        <p class="mb-1">Clash订阅: <span class="badge bg-success">{total_clash_links}</span></p>
                        <p>V2Ray订阅: <span class="badge bg-info">{total_v2ray_links}</span></p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stats-card animate__animated animate__fadeInRight">
                    <div class="text-center stats-icon">
                        <i class="bi bi-hdd-network"></i>
                    </div>
                    <h5 class="text-center mb-3">节点统计</h5>
                    <div class="text-center">
                        <div class="mb-3">
                            <span class="badge bg-primary rounded-pill fs-6">{total_nodes} 个节点</span>
                        </div>
                        <p class="mb-1">平均每日: <span class="badge bg-warning text-dark">{int(total_nodes/total_dates) if total_dates > 0 else 0} 个</span></p>
                        <p>更新频率: <span class="badge bg-secondary">每日更新</span></p>
                    </div>
                </div>
            </div>
        </div>

        <!-- FreeV2.net 订阅部分 -->
        <h3 id="freev2" class="section-title animate__animated animate__fadeIn">
            <i class="bi bi-star-fill me-2 text-warning"></i> FreeV2.net 最新订阅
        </h3>
        <div class="row">
            <div class="col-12">
                <div class="card highlight-card animate__animated animate__fadeInUp">
                    <div class="card-body">
                        <h5 class="card-title d-flex align-items-center">
                            <i class="bi bi-lightning-charge me-2 text-warning"></i> 
                            FreeV2.net 免费节点
                        </h5>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-clock me-1"></i>
                                更新时间: {freev2_data.get('scrape_time', '未知') if freev2_data else '未知'}
                            </small>
                        </p>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> 订阅链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="freev2-link" class="form-control" value="{freev2_link or '暂无订阅链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#freev2-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">复制后可直接导入到Clash/V2Ray客户端使用</small>
                        </div>
                        
                        <div class="alert alert-light node-info-section">
                            <p class="mb-1"><i class="bi bi-info-circle me-1 text-info"></i> 网站信息:</p>
                            <p class="mb-3">为了避免乱码和不必要的信息，此处已省略网站信息</p>
                            <a href="https://b.freev2.net/" target="_blank" class="btn btn-outline-primary animated-hover">
                                <i class="bi bi-box-arrow-up-right me-1"></i> 访问FreeV2.net
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- BestClash 订阅部分 -->
        <h3 id="bestclash" class="section-title animate__animated animate__fadeIn">
            <i class="bi bi-star-fill me-2 text-warning"></i> BestClash 最新订阅
        </h3>
        <div class="row">
            <div class="col-12">
                <div class="card highlight-card animate__animated animate__fadeInUp">
                    <div class="card-body">
                        <h5 class="card-title d-flex align-items-center">
                            <i class="bi bi-star-fill me-2 text-warning"></i> 
                            BestClash 免费节点
                        </h5>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-clock me-1"></i>
                                更新时间: {bestclash_data.get('scrape_time', '未知') if bestclash_data else '未知'}
                            </small>
                        </p>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> 订阅链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="bestclash-link" class="form-control" value="{bestclash_github_link or '暂无订阅链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#bestclash-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">复制后可直接导入到Clash/V2Ray客户端使用</small>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> 国内镜像链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="bestclash-mirror-link" class="form-control" value="{bestclash_mirror_link or '暂无镜像链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#bestclash-mirror-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">国内用户推荐使用此链接</small>
                        </div>
                        
                        <div class="alert alert-light node-info-section">
                            <p class="mb-1"><i class="bi bi-info-circle me-1 text-info"></i> 网站信息:</p>
                            <p class="mb-3">{bestclash_data.get('description', '免费Clash代理！自动从网上爬取最快的代理，每30分钟更新！') if bestclash_data else '免费Clash代理！自动从网上爬取最快的代理，每30分钟更新！'}</p>
                            <a href="https://github.com/PuddinCat/BestClash" target="_blank" class="btn btn-outline-primary animated-hover">
                                <i class="bi bi-box-arrow-up-right me-1"></i> 访问BestClash
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 周润发公益v2ray节点订阅部分 -->
        <h3 id="shaoyou" class="section-title animate__animated animate__fadeIn">
            <i class="bi bi-clock-history me-2 text-info"></i> 周润发公益v2ray节点订阅
        </h3>
        <div class="row">
            <div class="col-12">
                <div class="card highlight-card animate__animated animate__fadeInUp">
                    <div class="card-body">
                        <h5 class="card-title d-flex align-items-center">
                            <i class="bi bi-clock-history me-2 text-info"></i> 
                            周润发公益v2ray节点
                        </h5>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-clock me-1"></i>
                                更新时间: {shaoyou_data.get('scrape_time', '未知') if shaoyou_data else '未知'} (每2小时更新一次)
                            </small>
                        </p>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> yaml格式订阅链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="shaoyou-yaml-link" class="form-control" value="{shaoyou_yaml_link or '暂无订阅链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#shaoyou-yaml-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">适用于Clash/Clash Verge等客户端</small>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> base64格式订阅链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="shaoyou-base64-link" class="form-control" value="{shaoyou_base64_link or '暂无订阅链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#shaoyou-base64-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">适用于V2rayN/V2rayNG等客户端</small>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> mihomo格式订阅链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="shaoyou-mihomo-link" class="form-control" value="{shaoyou_mihomo_link or '暂无订阅链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#shaoyou-mihomo-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">适用于带分流规则的Clash客户端</small>
                        </div>
                        
                        <div class="mb-4">
                            <h6 class="mb-3"><i class="bi bi-link-45deg me-1"></i> 国内镜像链接:</h6>
                            <div class="input-group mb-2">
                                <input type="text" id="shaoyou-no-proxy-link" class="form-control" value="{shaoyou_no_proxy_link or '暂无镜像链接'}" readonly>
                                <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#shaoyou-no-proxy-link">
                                    <i class="bi bi-clipboard"></i> 复制
                                </button>
                            </div>
                            <small class="text-muted">国内用户推荐使用此无需代理的更新链接</small>
                        </div>
                        
                        <div class="alert alert-light node-info-section">
                            <p class="mb-1"><i class="bi bi-info-circle me-1 text-info"></i> 特别说明:</p>
                            <p class="mb-3">{shaoyou_data.get('description', '每2小时更新一次的免费v2ray节点，请勿用于非法用途') if shaoyou_data else '每2小时更新一次的免费v2ray节点，请勿用于非法用途'}</p>
                            <a href="https://github.com/shaoyouvip/free" target="_blank" class="btn btn-outline-primary animated-hover">
                                <i class="bi bi-box-arrow-up-right me-1"></i> 访问节点仓库
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Shadowrocket 共享账号部分 -->
        <h3 id="shadowrocket" class="section-title animate__animated animate__fadeIn">
            <i class="bi bi-apple me-2 text-danger"></i> Shadowrocket 共享账号
        </h3>
        <div class="row">
            <div class="col-12">
                <div class="card highlight-card animate__animated animate__fadeInUp">
                    <div class="card-body">
                        <h5 class="card-title d-flex align-items-center">
                            <i class="bi bi-rocket me-2 text-danger"></i> 
                            Shadowrocket (小火箭) 免费共享Apple ID
                        </h5>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-info-circle me-1"></i>
                                实时更新的Apple账号，用于免费下载小火箭
                            </small>
                        </p>
                        
                        <div class="alert alert-warning">
                            <p class="mb-1"><i class="bi bi-exclamation-triangle me-1"></i> <strong>使用注意事项:</strong></p>
                            <ol class="mb-0">
                                <li>打开iPhone/iPad的蓝色 AppStore 软件（请不要打开设置）</li>
                                <li>右上角点击 个人头像 进入账户，下拉到最底找到并点击 退出登录</li>
                                <li>使用下方获取的共享账号和密码登录</li>
                                <li>点击登录，提示 Apple id安全，请点击 其他选项-不升级</li>
                                <li>搜索 Shadowrocket 下载，或者其他你想下载的软件</li>
                                <li>用完务必 退出登录，避免你的手机被锁</li>
                            </ol>
                        </div>
                        
                        <div class="d-grid gap-2 mt-4">
                            <a href="https://proxy4all.github.io/FreeShadowrocket/" target="_blank" class="btn btn-danger btn-lg animated-hover">
                                <i class="bi bi-rocket me-2"></i> 获取免费小火箭共享账号
                            </a>
                            <a href="https://ids.ailiao.eu/" target="_blank" class="btn btn-secondary btn-lg animated-hover">
                                <i class="bi bi-person-badge me-2"></i> 备选账号获取通道
                            </a>
                        </div>
                        
                        <div class="alert alert-light mt-4 node-info-section">
                            <p class="mb-1"><i class="bi bi-info-circle me-1 text-info"></i> 说明:</p>
                            <p class="mb-3">为保证账号安全性和可用性，我们不直接显示账号信息，请通过上方按钮跳转到官方站点获取最新账号。</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 日日更新节点订阅部分 -->
        <h3 id="ripao" class="section-title animate__animated animate__fadeIn">
            <i class="bi bi-bookmark-star-fill me-2 text-danger"></i> 日日更新节点永久订阅
        </h3>
        <div class="row">
            <div class="col-12">
                <div class="card highlight-card animate__animated animate__fadeInUp">
                    <div class="card-body">
                        <h5 class="card-title d-flex align-items-center">
                            <i class="bi bi-calendar2-check me-2 text-danger"></i> 
                            日日更新节点永久订阅
                            <span class="badge bg-danger ms-2">永久地址</span>
                        </h5>
                        <p class="card-text">
                            永久固定的订阅地址，国内优先使用镜像订阅（镜像不稳定时可切换直连）
                        </p>
                        
                        <div class="row mb-4">
                            <div class="col-md-6 mb-3">
                                <div class="card sub-card">
                                    <div class="card-header">
                                        <i class="bi bi-intersect me-2"></i> Clash 订阅
                                    </div>
                                    <div class="card-body">
                                        <div class="input-group mb-3">
                                            <input type="text" id="ripao-clash-link" class="form-control" value="{ripao_clash_link or '暂无订阅链接'}" readonly>
                                            <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#ripao-clash-link">
                                                <i class="bi bi-clipboard"></i> 复制
                                            </button>
                                        </div>
                                        <p class="text-muted small mb-2">国内镜像链接：</p>
                                        <div class="input-group">
                                            <input type="text" id="ripao-clash-mirror" class="form-control" value="{ripao_clash_mirror or '暂无镜像链接'}" readonly>
                                            <button class="btn btn-outline-success copy-btn" data-clipboard-target="#ripao-clash-mirror">
                                                <i class="bi bi-clipboard"></i> 复制
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6 mb-3">
                                <div class="card sub-card">
                                    <div class="card-header">
                                        <i class="bi bi-hdd-network me-2"></i> 通用/V2ray 订阅
                                    </div>
                                    <div class="card-body">
                                        <div class="input-group mb-3">
                                            <input type="text" id="ripao-v2ray-link" class="form-control" value="{ripao_v2ray_link or '暂无订阅链接'}" readonly>
                                            <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#ripao-v2ray-link">
                                                <i class="bi bi-clipboard"></i> 复制
                                            </button>
                                        </div>
                                        <p class="text-muted small mb-2">国内镜像链接：</p>
                                        <div class="input-group">
                                            <input type="text" id="ripao-v2ray-mirror" class="form-control" value="{ripao_v2ray_mirror or '暂无镜像链接'}" readonly>
                                            <button class="btn btn-outline-success copy-btn" data-clipboard-target="#ripao-v2ray-mirror">
                                                <i class="bi bi-clipboard"></i> 复制
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-muted small">
                                <i class="bi bi-info-circle me-1"></i> 
                                更新频率：{ripao_data.get('update_interval', '日更新') if ripao_data else '日更新'}
                            </span>
                            <a href="https://github.com/ripaojiedian/freenode" target="_blank" class="btn btn-sm btn-outline-secondary">
                                <i class="bi bi-github me-1"></i> 访问源码库
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- V2rayc.github.io 订阅部分 -->
        <h3 id="v2rayc" class="section-title animate__animated animate__fadeIn">
            <i class="bi bi-lightning-charge-fill me-2 text-primary"></i> V2rayc.github.io 节点订阅
        </h3>
        <div class="row">
            <div class="col-12">
                <div class="card highlight-card animate__animated animate__fadeInUp">
                    <div class="card-body">
                        <h5 class="card-title d-flex align-items-center">
                            <i class="bi bi-globe me-2 text-primary"></i> 
                            V2rayc免费节点订阅
                            <span class="badge bg-info ms-2">每日更新</span>
                        </h5>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-clock me-1"></i>
                                更新时间: {v2rayc_update_time}
                            </small>
                        </p>
                        
                        <div class="row mb-4">
                            <!-- Clash 订阅 -->
                            <div class="col-md-4 mb-3">
                                <div class="card sub-card">
                                    <div class="card-header">
                                        <i class="bi bi-intersect me-2"></i> Clash 订阅
                                    </div>
                                    <div class="card-body">
                                        <div class="list-group">
"""
        v2rayc_clash_html = ""
        if v2rayc_clash_links:
            for i, link in enumerate(v2rayc_clash_links[:3]):
                v2rayc_clash_html += f"""
                                            <div class="list-group-item mb-2">
                                                <div class="input-group">
                                                    <input type="text" id="v2rayc-clash-{i}" class="form-control" value="{link}" readonly>
                                                    <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#v2rayc-clash-{i}">
                                                        <i class="bi bi-clipboard"></i>
                                                    </button>
                                                </div>
                                            </div>"""
        else:
            v2rayc_clash_html = '<div class="alert alert-info">暂无Clash订阅链接</div>'
        
        html_content += v2rayc_clash_html + """
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- V2Ray 订阅 -->
                            <div class="col-md-4 mb-3">
                                <div class="card sub-card">
                                    <div class="card-header">
                                        <i class="bi bi-hdd-network me-2"></i> V2Ray 订阅
                                    </div>
                                    <div class="card-body">
                                        <div class="list-group">
"""
        v2rayc_v2ray_html = ""
        if v2rayc_v2ray_links:
            for i, link in enumerate(v2rayc_v2ray_links[:3]):
                v2rayc_v2ray_html += f"""
                                            <div class="list-group-item mb-2">
                                                <div class="input-group">
                                                    <input type="text" id="v2rayc-v2ray-{i}" class="form-control" value="{link}" readonly>
                                                    <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#v2rayc-v2ray-{i}">
                                                        <i class="bi bi-clipboard"></i>
                                                    </button>
                                                </div>
                                            </div>"""
        else:
            v2rayc_v2ray_html = '<div class="alert alert-info">暂无V2Ray订阅链接</div>'
        
        html_content += v2rayc_v2ray_html + """
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Sing-box 订阅 -->
                            <div class="col-md-4 mb-3">
                                <div class="card sub-card">
                                    <div class="card-header">
                                        <i class="bi bi-box me-2"></i> Sing-box 订阅
                                    </div>
                                    <div class="card-body">
                                        <div class="list-group">
"""
        v2rayc_singbox_html = ""
        if v2rayc_singbox_links:
            for i, link in enumerate(v2rayc_singbox_links[:3]):
                v2rayc_singbox_html += f"""
                                            <div class="list-group-item mb-2">
                                                <div class="input-group">
                                                    <input type="text" id="v2rayc-singbox-{i}" class="form-control" value="{link}" readonly>
                                                    <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#v2rayc-singbox-{i}">
                                                        <i class="bi bi-clipboard"></i>
                                                    </button>
                                                </div>
                                            </div>"""
        else:
            v2rayc_singbox_html = '<div class="alert alert-info">暂无Sing-box订阅链接</div>'
        
        html_content += v2rayc_singbox_html + """
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="d-flex justify-content-between align-items-center">
            <span class="text-muted small">
                <i class="bi bi-info-circle me-1"></i> 
                更新频率：每日更新
            </span>
            <a href="https://github.com/v2rayc/v2rayc.github.io" target="_blank" class="btn btn-sm btn-outline-secondary">
                <i class="bi bi-github me-1"></i> 访问源码库
            </a>
        </div>
    </div>
</div>

<h3 id="datiya" class="section-title animate__animated animate__fadeIn">
    <i class="bi bi-card-list me-2"></i> 按日期查看节点
</h3>
<div class="row">
"""
        
        # 添加"dates"数组的检查
        date_keys = []
        if "dates" in results and isinstance(results["dates"], list) and results["dates"]:
            date_keys = results["dates"]
        else:
            # 如果没有dates数组，则从键中查找日期
            date_keys = sorted([k for k in results.keys() if k not in ["freev2", "bestclash", "shaoyou", "ripao", "v2rayc", "dates"] and isinstance(results.get(k), dict)], reverse=True)
        
        # 生成节点卡片
        for date in date_keys:
            if date not in results or not isinstance(results[date], dict):
                continue  # 跳过不存在或非字典类型的结果
            
            result = results[date]
            
            # 检查必要的键是否存在，添加默认值
            if 'title' not in result:
                result['title'] = f"日期 {date} 的节点数据"
            if 'clash_links' not in result:
                result['clash_links'] = []
            if 'v2ray_links' not in result:
                result['v2ray_links'] = []
            if 'date' not in result:
                result['date'] = date
            
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) >= 8 else date
            
            # 获取节点信息
            nodes_info_html = ""
            if 'nodes_info' in result and result['nodes_info'] is not None:
                if isinstance(result['nodes_info'], dict):
                    for key, value in result['nodes_info'].items():
                        nodes_info_html += f"<p class='mb-1'><span class='fw-bold'>{key}:</span> {value}</p>"
                elif isinstance(result['nodes_info'], list) and result['nodes_info']:
                    nodes_info_html = f"<p>节点数量: {len(result['nodes_info'])}</p>"
                else:
                    nodes_info_html = "<p>无节点信息</p>"
            else:
                nodes_info_html = "<p>无节点信息</p>"
            
            # 创建唯一ID
            card_id = f"card-{date}"
            collapse_id = f"collapse-{date}"
            
            html_content += f"""
            <div class="col-md-6 col-lg-4 animate__animated animate__fadeIn" style="animation-delay: {0.1 * list(results.keys()).index(date)}s">
                <div class="card h-100" id="{card_id}">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span class="fs-5">
                            <i class="bi bi-calendar-date me-2 text-primary"></i>{formatted_date}
                        </span>
                        <div>
                            <span class="badge bg-primary">
                                <i class="bi bi-lightning me-1"></i>{len(result['clash_links'])}
                            </span>
                            <span class="badge bg-success">
                                <i class="bi bi-hdd-network me-1"></i>{len(result['v2ray_links'])}
                            </span>
                        </div>
                    </div>
                    <div class="card-body">
                        <h5 class="card-title text-truncate" title="{result['title']}">{result['title']}</h5>
                        <p class="card-text">
                            <small class="text-muted">
                                <i class="bi bi-clock-history me-1"></i>
                                更新时间: {result.get('update_time', '未知')}
                            </small>
                        </p>
                        
                        <div class="mb-3">
                            <h6 class="mb-2"><i class="bi bi-info-circle me-1 text-info"></i>节点信息:</h6>
                            <div class="alert alert-light p-2 mb-3 node-info-section">
                                {nodes_info_html}
                            </div>
                        </div>
                        
                        <button class="btn btn-primary subscription-button w-100" type="button" data-bs-toggle="collapse" data-bs-target="#{collapse_id}">
                            <i class="bi bi-link-45deg me-1"></i> 查看订阅链接
                        </button>
                    </div>
                    
                    <div class="collapse" id="{collapse_id}">
                        <div class="card-body border-top">
"""
            
            # 生成订阅链接折叠面板
            # Clash 订阅链接
            if result['clash_links']:
                html_content += f"""
                            <h6 class="mb-3"><i class="bi bi-lightning-charge me-1 text-primary"></i>Clash 订阅链接:</h6>
                            <div class="list-group mb-3">
"""
                # 添加Clash订阅链接
                for i, link in enumerate(result['clash_links']):
                    link_id = f"clash-{date}-{i}"
                    html_content += f"""
                                <div class="list-group-item mb-2">
                                    <div class="input-group">
                                        <input type="text" id="{link_id}" class="form-control" value="{link}" readonly>
                                        <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#{link_id}">
                                            <i class="bi bi-clipboard"></i>
                                        </button>
                                    </div>
                                </div>
"""
                html_content += "                            </div>\n"
            
            # V2Ray 订阅链接
            if result['v2ray_links']:
                html_content += f"""
                            <h6 class="mb-3"><i class="bi bi-hdd-network me-1 text-success"></i>V2Ray 订阅链接:</h6>
                            <div class="list-group mb-3">
"""
                # 添加V2Ray订阅链接
                for i, link in enumerate(result['v2ray_links']):
                    link_id = f"v2ray-{date}-{i}"
                    html_content += f"""
                                <div class="list-group-item mb-2">
                                    <div class="input-group">
                                        <input type="text" id="{link_id}" class="form-control" value="{link}" readonly>
                                        <button class="btn btn-outline-primary copy-btn" data-clipboard-target="#{link_id}">
                                            <i class="bi bi-clipboard"></i>
                                        </button>
                                    </div>
                                </div>
"""
                html_content += "                            </div>\n"
            
            html_content += """
                        </div>
                    </div>
                </div>
            </div>
"""
        
        # 完成HTML
        html_content += """
        </div>
    </div>

    <footer id="about" class="bg-light text-center text-lg-start mt-5">
        <div class="container p-4">
            <div class="row">
                <div class="col-lg-4 col-md-12 mb-4 mb-md-0">
                    <h5 class="mb-3"><i class="bi bi-info-circle me-2"></i>关于本项目</h5>
                    <p>
                        此页面自动从多个来源采集免费Clash/V2Ray节点订阅，供学习和测试使用。
                        请勿用于非法用途，遵守当地法律法规。
                    </p>
                    <div class="mt-4">
                        <a href="#" class="btn btn-outline-primary">
                            <i class="bi bi-github me-1"></i> 项目源码
                        </a>
                    </div>
                </div>
                <div class="col-lg-4 col-md-6 mb-4 mb-md-0">
                    <h5 class="mb-3"><i class="bi bi-diagram-3 me-2"></i>数据来源</h5>
                    <ul class="list-unstyled">
                        <li class="mb-2">
                            <a href="https://free.datiya.com/" target="_blank" class="text-decoration-none">
                                <i class="bi bi-link-45deg me-1"></i>Datiya
                            </a>
                        </li>
                        <li class="mb-2">
                            <a href="https://b.freev2.net/" target="_blank" class="text-decoration-none">
                                <i class="bi bi-link-45deg me-1"></i>FreeV2.net
                            </a>
                        </li>
                        <li class="mb-2">
                            <a href="https://github.com/PuddinCat/BestClash" target="_blank" class="text-decoration-none">
                                <i class="bi bi-link-45deg me-1"></i>BestClash
                            </a>
                        </li>
                        <li class="mb-2">
                            <a href="https://github.com/shaoyouvip/free" target="_blank" class="text-decoration-none">
                                <i class="bi bi-link-45deg me-1"></i>周润发公益v2ray
                            </a>
                        </li>
                        <li class="mb-2">
                            <a href="https://proxy4all.github.io/FreeShadowrocket/" target="_blank" class="text-decoration-none">
                                <i class="bi bi-link-45deg me-1"></i>Shadowrocket共享账号
                            </a>
                        </li>
                    </ul>
                </div>
                <div class="col-lg-4 col-md-6 mb-4 mb-md-0">
                    <h5 class="mb-3"><i class="bi bi-shield-exclamation me-2"></i>免责声明</h5>
                    <p>
                        本站不生产任何节点，仅收集和整理公开的免费节点信息。
                        节点稳定性和可用性无法保证，请勿依赖这些节点进行重要活动。
                    </p>
                    <p class="mt-2">
                        <small class="text-muted">更新频率: 每日自动更新</small>
                    </p>
                </div>
            </div>
        </div>
        <div class="text-center p-3" style="background-color: rgba(0, 0, 0, 0.05);">
            © 2025 Clash/V2Ray 免费节点订阅 | <i class="bi bi-arrow-clockwise me-1"></i>每日自动更新
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/clipboard@2.0.11/dist/clipboard.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化剪贴板
            var clipboard = new ClipboardJS('.copy-btn');
            
            clipboard.on('success', function(e) {
                const originalHtml = e.trigger.innerHTML;
                e.trigger.innerHTML = '<i class="bi bi-check"></i> 已复制';
                e.trigger.classList.add('btn-success');
                e.trigger.classList.remove('btn-outline-primary');
                
                setTimeout(function() {
                    e.trigger.innerHTML = originalHtml;
                    e.trigger.classList.remove('btn-success');
                    e.trigger.classList.add('btn-outline-primary');
                }, 1500);
                
                e.clearSelection();
            });

            // 平滑滚动
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        window.scrollTo({
                            top: target.offsetTop - 70,
                            behavior: 'smooth'
                        });
                    }
                });
            });
        });
    </script>
</body>
</html>
"""
        
        # 保存HTML文件
        with open("web/index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 保存数据文件，用于后续更新
        with open("web/data.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info("HTML页面生成成功: web/index.html")
        
        # 生成简化版HTML
        try:
            simple_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Clash/V2Ray 免费节点订阅</title>
</head>
<body>
    <h1>Clash/V2Ray 免费节点订阅</h1>
    <p>数据更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <p>共收录 {len(results)} 个日期的数据</p>
    
    <!-- 日日更新节点订阅信息 -->
    <h2>日日更新节点永久订阅</h2>
    <p>Clash订阅: {ripao_clash_link or '暂无订阅链接'}</p>
    <p>Clash镜像: {ripao_clash_mirror or '暂无镜像链接'}</p>
    <p>V2ray订阅: {ripao_v2ray_link or '暂无订阅链接'}</p>
    <p>V2ray镜像: {ripao_v2ray_mirror or '暂无镜像链接'}</p>
    <p>更新频率: {ripao_data.get('update_interval', '日更新') if ripao_data else '日更新'}</p>
    
    <!-- FreeV2.net 订阅信息 -->
    <h2>FreeV2.net 订阅</h2>"""
            
            # 添加FreeV2.net订阅链接信息
            if freev2_link:
                simple_html += f"    <p>订阅链接: {freev2_link}</p>\n"
            else:
                simple_html += "    <p>订阅链接: 暂无订阅链接</p>\n"
            
            update_time = "未知"
            if freev2_data and 'scrape_time' in freev2_data:
                update_time = freev2_data['scrape_time']
            
            simple_html += f"""    <p>更新时间: {update_time}</p>
    
    <!-- v2rayc.github.io 订阅信息 -->
    <h2>v2rayc.github.io 订阅</h2>"""
            
            # 获取v2rayc数据
            v2rayc_data = get_latest_v2rayc_data()
            
            # 确保v2rayc_data不为None
            if v2rayc_data is None:
                v2rayc_data = {
                    "clash_links": [],
                    "v2ray_links": [],
                    "singbox_links": [],
                    "update_time": "未知",
                    "scrape_time": "未知"
                }
            
            # 添加v2rayc订阅链接信息
            v2rayc_clash_links = v2rayc_data.get('clash_links', [])
            v2rayc_v2ray_links = v2rayc_data.get('v2ray_links', [])
            v2rayc_singbox_links = v2rayc_data.get('singbox_links', [])
            
            # Clash订阅
            if v2rayc_clash_links and len(v2rayc_clash_links) > 0:
                simple_html += f"    <p>Clash订阅: {v2rayc_clash_links[0]}</p>\n"
            else:
                simple_html += "    <p>Clash订阅: 暂无订阅链接</p>\n"
            
            # V2ray订阅
            if v2rayc_v2ray_links and len(v2rayc_v2ray_links) > 0:
                simple_html += f"    <p>V2ray订阅: {v2rayc_v2ray_links[0]}</p>\n"
            else:
                simple_html += "    <p>V2ray订阅: 暂无订阅链接</p>\n"
            
            # Sing-box订阅
            if v2rayc_singbox_links and len(v2rayc_singbox_links) > 0:
                simple_html += f"    <p>Sing-box订阅: {v2rayc_singbox_links[0]}</p>\n"
            else:
                simple_html += "    <p>Sing-box订阅: 暂无订阅链接</p>\n"
            
            v2rayc_update_time = "未知"
            if v2rayc_data and 'update_time' in v2rayc_data:
                v2rayc_update_time = v2rayc_data['update_time']
            elif v2rayc_data and 'scrape_time' in v2rayc_data:
                v2rayc_update_time = v2rayc_data['scrape_time']
            
            simple_html += f"""    <p>更新时间: {v2rayc_update_time}</p>
    
    <h2>按日期列表</h2>
    <ul>
"""
            
            # 处理日期列表
            date_keys = []
            if "dates" in results and isinstance(results["dates"], list) and results["dates"]:
                date_keys = results["dates"]
            else:
                date_keys = sorted([k for k in results.keys() 
                                   if k not in ["freev2", "bestclash", "shaoyou", "ripao", "v2rayc", "dates"] 
                                   and isinstance(results.get(k), dict)], reverse=True)
            
            for date in date_keys:
                if date not in results or not isinstance(results[date], dict):
                    continue
                
                try:
                    formatted_date = results[date].get('date', date)
                    clash_links = results[date].get('clash_links', [])
                    v2ray_links = results[date].get('v2ray_links', [])
                    clash_count = len(clash_links) if isinstance(clash_links, list) else 0
                    v2ray_count = len(v2ray_links) if isinstance(v2ray_links, list) else 0
                    
                    # 安全获取节点数量
                    node_count = 0
                    if 'nodes_info' in results[date]:
                        nodes_info = results[date]['nodes_info']
                        if isinstance(nodes_info, list):
                            node_count = len(nodes_info)
                        else:
                            node_count_str = nodes_info.get('可用节点', '0个') if isinstance(nodes_info, dict) else '0个'
                            try:
                                node_count = int(re.search(r'\d+', node_count_str).group() if re.search(r'\d+', node_count_str) else '0')
                            except:
                                node_count = 0
                    
                    simple_html += f"""        <li>
            <strong>{formatted_date}</strong>: 
            Clash订阅: {clash_count}, 
            V2Ray订阅: {v2ray_count}, 
            节点数量: {node_count}
        </li>
"""
                except Exception as e:
                    logger.warning(f"处理日期 {date} 时出错: {e}")
                    continue
            
            simple_html += """    </ul>
</body>
</html>
"""
            
            with open("web/simple.html", "w", encoding="utf-8") as f:
                f.write(simple_html)
            
            logger.info("已生成简化版HTML页面: web/simple.html")
        except Exception as e2:
            logger.exception(f"生成简化版HTML页面时也出错: {e2}")
    except Exception as e:
        logger.exception(f"生成HTML页面时出错: {e}")
        # 尝试生成简化版HTML
        try:
            simple_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Clash/V2Ray 免费节点订阅</title>
</head>
<body>
    <h1>Clash/V2Ray 免费节点订阅</h1>
    <p>数据更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <p>共收录 {len(results)} 个日期的数据</p>
    
    <!-- 日日更新节点订阅信息 -->
    <h2>日日更新节点永久订阅</h2>
    <p>Clash订阅: {ripao_clash_link or '暂无订阅链接'}</p>
    <p>Clash镜像: {ripao_clash_mirror or '暂无镜像链接'}</p>
    <p>V2ray订阅: {ripao_v2ray_link or '暂无订阅链接'}</p>
    <p>V2ray镜像: {ripao_v2ray_mirror or '暂无镜像链接'}</p>
    <p>更新频率: {ripao_data.get('update_interval', '日更新') if ripao_data else '日更新'}</p>
    
    <!-- FreeV2.net 订阅信息 -->
    <h2>FreeV2.net 订阅</h2>"""
            
            # 添加FreeV2.net订阅链接信息
            if freev2_link:
                simple_html += f"    <p>订阅链接: {freev2_link}</p>\n"
            else:
                simple_html += "    <p>订阅链接: 暂无订阅链接</p>\n"
            
            update_time = "未知"
            if freev2_data and 'scrape_time' in freev2_data:
                update_time = freev2_data['scrape_time']
            
            simple_html += f"""    <p>更新时间: {update_time}</p>
    
    <!-- v2rayc.github.io 订阅信息 -->
    <h2>v2rayc.github.io 订阅</h2>"""
            
            # 获取v2rayc数据
            v2rayc_data = get_latest_v2rayc_data()
            
            # 确保v2rayc_data不为None
            if v2rayc_data is None:
                v2rayc_data = {
                    "clash_links": [],
                    "v2ray_links": [],
                    "singbox_links": [],
                    "update_time": "未知",
                    "scrape_time": "未知"
                }
            
            # 添加v2rayc订阅链接信息
            v2rayc_clash_links = v2rayc_data.get('clash_links', [])
            v2rayc_v2ray_links = v2rayc_data.get('v2ray_links', [])
            v2rayc_singbox_links = v2rayc_data.get('singbox_links', [])
            
            # Clash订阅
            if v2rayc_clash_links and len(v2rayc_clash_links) > 0:
                simple_html += f"    <p>Clash订阅: {v2rayc_clash_links[0]}</p>\n"
            else:
                simple_html += "    <p>Clash订阅: 暂无订阅链接</p>\n"
            
            # V2ray订阅
            if v2rayc_v2ray_links and len(v2rayc_v2ray_links) > 0:
                simple_html += f"    <p>V2ray订阅: {v2rayc_v2ray_links[0]}</p>\n"
            else:
                simple_html += "    <p>V2ray订阅: 暂无订阅链接</p>\n"
            
            # Sing-box订阅
            if v2rayc_singbox_links and len(v2rayc_singbox_links) > 0:
                simple_html += f"    <p>Sing-box订阅: {v2rayc_singbox_links[0]}</p>\n"
            else:
                simple_html += "    <p>Sing-box订阅: 暂无订阅链接</p>\n"
            
            v2rayc_update_time = "未知"
            if v2rayc_data and 'update_time' in v2rayc_data:
                v2rayc_update_time = v2rayc_data['update_time']
            elif v2rayc_data and 'scrape_time' in v2rayc_data:
                v2rayc_update_time = v2rayc_data['scrape_time']
            
            simple_html += f"""    <p>更新时间: {v2rayc_update_time}</p>
    
    <h2>按日期列表</h2>
    <ul>
"""
            
            # 处理日期列表
            date_keys = []
            if "dates" in results and isinstance(results["dates"], list) and results["dates"]:
                date_keys = results["dates"]
            else:
                date_keys = sorted([k for k in results.keys() 
                                   if k not in ["freev2", "bestclash", "shaoyou", "ripao", "v2rayc", "dates"] 
                                   and isinstance(results.get(k), dict)], reverse=True)
            
            for date in date_keys:
                if date not in results or not isinstance(results[date], dict):
                    continue
                
                try:
                    formatted_date = results[date].get('date', date)
                    clash_links = results[date].get('clash_links', [])
                    v2ray_links = results[date].get('v2ray_links', [])
                    clash_count = len(clash_links) if isinstance(clash_links, list) else 0
                    v2ray_count = len(v2ray_links) if isinstance(v2ray_links, list) else 0
                    
                    # 安全获取节点数量
                    node_count = 0
                    if 'nodes_info' in results[date]:
                        nodes_info = results[date]['nodes_info']
                        if isinstance(nodes_info, list):
                            node_count = len(nodes_info)
                        else:
                            node_count_str = nodes_info.get('可用节点', '0个') if isinstance(nodes_info, dict) else '0个'
                            try:
                                node_count = int(re.search(r'\d+', node_count_str).group() if re.search(r'\d+', node_count_str) else '0')
                            except:
                                node_count = 0
                    
                    simple_html += f"""        <li>
            <strong>{formatted_date}</strong>: 
            Clash订阅: {clash_count}, 
            V2Ray订阅: {v2ray_count}, 
            节点数量: {node_count}
        </li>
"""
                except Exception as e:
                    logger.warning(f"处理日期 {date} 时出错: {e}")
                    continue
            
            simple_html += """    </ul>
</body>
</html>
"""
            
            with open("web/simple.html", "w", encoding="utf-8") as f:
                f.write(simple_html)
            
            logger.info("已生成简化版HTML页面: web/simple.html")
        except Exception as e2:
            logger.exception(f"生成简化版HTML页面时也出错: {e2}")

def check_and_process(download=True, force_update=False):
    """
    检查GitHub上的更新并处理新的日期
    
    参数:
    download (bool): 是否下载订阅文件
    force_update (bool): 是否强制更新已有数据
    
    返回:
    bool: 是否有成功处理的日期
    """
    logger.info("开始检查GitHub更新...")
    new_date_tuples = get_new_dates()
    
    if not new_date_tuples and not force_update:
        logger.info("没有发现新的日期，无需处理")
        return False
    
    date_tuples_to_process = new_date_tuples
    if force_update:
        logger.info("强制更新模式，将处理所有日期")
        date_tuples_to_process = get_all_dates_to_process()
    
    logger.info(f"需要处理 {len(date_tuples_to_process)} 个日期")
    process_results = fetch_and_process(date_tuples_to_process, download, force_update)
    
    # 获取FreeV2.net数据
    freev2_data = get_latest_freev2_data()
    logger.info("获取到FreeV2.net订阅数据")
    
    # 获取BestClash数据
    bestclash_data = get_latest_bestclash_data()
    logger.info("获取到BestClash GitHub订阅链接")
    
    # 获取周润发公益v2ray节点数据
    shaoyou_data = get_latest_shaoyou_data()
    logger.info("获取到周润发公益v2ray节点订阅链接")
    
    # 获取日日更新节点数据
    ripao_data = get_latest_ripao_data()
    logger.info("获取到日日更新节点订阅链接")
    
    # 获取v2rayc.github.io节点数据
    v2rayc_data = get_latest_v2rayc_data()
    logger.info("获取到v2rayc.github.io节点订阅链接")
    
    # 生成HTML页面
    generate_html_page({
        "dates": process_results, 
        "freev2": freev2_data,
        "bestclash": bestclash_data,
        "shaoyou": shaoyou_data,
        "ripao": ripao_data,
        "v2rayc": v2rayc_data
    })
    
    return len(process_results) > 0

def process_all_dates(download=True, force_update=False):
    """
    处理所有日期的数据
    
    参数:
    download (bool): 是否下载订阅文件
    force_update (bool): 是否强制更新已有数据
    """
    logger.info("获取所有日期...")
    all_date_tuples = get_all_dates_to_process()
    
    if not all_date_tuples:
        logger.warning("未获取到任何日期")
        return
    
    logger.info(f"获取到 {len(all_date_tuples)} 个日期")
    process_results = fetch_and_process(all_date_tuples, download, force_update)
    
    # 获取FreeV2.net数据
    freev2_data = get_latest_freev2_data()
    logger.info("获取到FreeV2.net订阅数据")
    
    # 获取BestClash数据
    bestclash_data = get_latest_bestclash_data()
    logger.info("获取到BestClash GitHub订阅链接")
    
    # 获取周润发公益v2ray节点数据
    shaoyou_data = get_latest_shaoyou_data()
    logger.info("获取到周润发公益v2ray节点订阅链接")
    
    # 获取日日更新节点数据
    ripao_data = get_latest_ripao_data()
    logger.info("获取到日日更新节点订阅链接")
    
    # 获取v2rayc.github.io节点数据
    v2rayc_data = get_latest_v2rayc_data()
    logger.info("获取到v2rayc.github.io节点订阅链接")
    
    # 生成HTML页面
    generate_html_page({
        "dates": process_results, 
        "freev2": freev2_data,
        "bestclash": bestclash_data,
        "shaoyou": shaoyou_data,
        "ripao": ripao_data,
        "v2rayc": v2rayc_data
    })
    
    if process_results:
        logger.info(f"成功处理 {len(process_results)} 个日期")
    else:
        logger.warning("未成功处理任何日期")

def run_scheduler(interval_hours=6, download=True):
    """
    运行定时任务调度器
    
    参数:
    interval_hours (int): 检查间隔小时数
    download (bool): 是否下载订阅文件
    """
    logger.info(f"启动定时监控，每 {interval_hours} 小时检查一次GitHub更新")
    
    # 设置定时任务
    schedule.every(interval_hours).hours.do(check_and_process, download=download)
    
    # 新增: 设置每天零点爬取FreeV2.net的任务
    if FREEV2_ENABLED:
        logger.info("设置每天零点爬取FreeV2.net的任务")
        schedule.every().day.at("00:00").do(fetch_freev2)
    
    # 新增: 设置每6小时爬取BestClash的任务
    logger.info("设置每6小时爬取BestClash的任务")
    schedule.every(6).hours.do(fetch_bestclash)
    
    # 新增: 设置每2小时爬取周润发公益v2ray节点的任务
    if SHAOYOU_ENABLED:
        logger.info("设置每2小时爬取周润发公益v2ray节点的任务")
        schedule.every(2).hours.do(fetch_shaoyou)
    
    # 新增: 设置每天2点爬取日日更新节点的任务
    if RIPAO_ENABLED:
        logger.info("设置每天2点爬取日日更新节点的任务")
        schedule.every().day.at("02:00").do(fetch_ripao)
    
    # 新增: 设置每天4点爬取v2rayc.github.io节点的任务
    if V2RAYC_ENABLED:
        logger.info("设置每天4点爬取v2rayc.github.io节点的任务")
        schedule.every().day.at("04:00").do(fetch_v2rayc)
    
    # 立即执行一次
    logger.info("立即执行一次检查...")
    check_and_process(download)
    
    # 如果启用了FreeV2.net爬取，也立即执行一次
    if FREEV2_ENABLED:
        logger.info("立即执行一次FreeV2.net爬取...")
        fetch_freev2()
    
    # 立即执行一次BestClash爬取
    logger.info("立即执行一次BestClash爬取...")
    fetch_bestclash()
    
    # 立即执行一次周润发公益v2ray节点爬取
    if SHAOYOU_ENABLED:
        logger.info("立即执行一次周润发公益v2ray节点爬取...")
        fetch_shaoyou()
    
    # 立即执行一次日日更新节点爬取
    if RIPAO_ENABLED:
        logger.info("立即执行一次日日更新节点爬取...")
        fetch_ripao()
    
    # 立即执行一次v2rayc.github.io节点爬取
    if V2RAYC_ENABLED:
        logger.info("立即执行一次v2rayc.github.io节点爬取...")
        fetch_v2rayc()
    
    # 循环等待定时任务执行
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次是否有待执行的任务
        except KeyboardInterrupt:
            logger.info("用户中断，定时任务结束")
            break
        except Exception as e:
            logger.exception(f"定时任务调度器出错: {e}")
            time.sleep(300)  # 出错后等待5分钟再继续

def main():
    """主函数，处理命令行参数并执行相应的操作"""
    parser = argparse.ArgumentParser(description="监控GitHub仓库并爬取datiya/FreeV2网站的订阅数据")
    parser.add_argument('--monitor', action='store_true', help='启动定时监控模式')
    parser.add_argument('--interval', type=int, default=6, help='监控间隔，单位为小时，默认为6小时')
    parser.add_argument('--all-dates', action='store_true', help='爬取所有历史日期的数据')
    parser.add_argument('--no-download', action='store_true', help='不下载订阅文件')
    parser.add_argument('--force-update', action='store_true', help='强制更新已有数据')
    parser.add_argument('--generate-html', action='store_true', help='仅生成HTML页面')
    parser.add_argument('--freev2', action='store_true', help='仅爬取FreeV2.net')
    parser.add_argument('--bestclash', action='store_true', help='仅爬取BestClash')
    parser.add_argument('--shaoyou', action='store_true', help='仅爬取周润发公益v2ray节点')
    parser.add_argument("--ripao", action="store_true", help="仅获取日日更新节点永久订阅")
    parser.add_argument("--v2rayc", action="store_true", help="仅爬取v2rayc.github.io节点订阅")
    
    args = parser.parse_args()
    
    # 仅爬取周润发公益v2ray节点
    if args.shaoyou:
        if SHAOYOU_ENABLED:
            logger.info("仅爬取周润发公益v2ray节点模式")
            fetch_shaoyou()
            # 重新生成HTML页面
            if os.path.exists("web/data.json"):
                try:
                    with open("web/data.json", "r", encoding="utf-8") as f:
                        results = json.load(f)
                    generate_html_page(results)
                except Exception as e:
                    logger.exception(f"读取数据文件并生成HTML页面时出错: {e}")
        else:
            logger.error("周润发公益v2ray节点爬取功能未启用")
        return
    
    # 仅爬取BestClash
    if args.bestclash:
        logger.info("仅爬取BestClash模式")
        fetch_bestclash()
        # 重新生成HTML页面
        if os.path.exists("web/data.json"):
            try:
                with open("web/data.json", "r", encoding="utf-8") as f:
                    results = json.load(f)
                generate_html_page(results)
            except Exception as e:
                logger.exception(f"读取数据文件并生成HTML页面时出错: {e}")
        return
    
    # 仅爬取FreeV2.net
    if args.freev2:
        if FREEV2_ENABLED:
            logger.info("仅爬取FreeV2.net模式")
            fetch_freev2()
        else:
            logger.error("FreeV2.net爬取功能未启用")
        return
    
    # 仅获取日日更新节点永久订阅
    if args.ripao:
        logger.info("仅获取日日更新节点永久订阅模式")
        ripao_data = fetch_ripao()
        freev2_data = get_latest_freev2_data()
        bestclash_data = get_latest_bestclash_data()
        shaoyou_data = get_latest_shaoyou_data()
        v2rayc_data = get_latest_v2rayc_data()
        
        # 生成HTML页面
        generate_html_page({
            "dates": [], 
            "freev2": freev2_data,
            "bestclash": bestclash_data,
            "shaoyou": shaoyou_data,
            "ripao": ripao_data,
            "v2rayc": v2rayc_data
        })
        return
    
    # 仅爬取v2rayc.github.io节点订阅
    if args.v2rayc:
        logger.info("仅爬取v2rayc.github.io节点订阅模式")
        v2rayc_data = fetch_v2rayc()
        
        # 如果获取失败，使用默认空数据
        if v2rayc_data is None:
            v2rayc_data = {
                "title": "v2rayc.github.io节点",
                "clash_links": [],
                "v2ray_links": [],
                "singbox_links": [],
                "update_time": "未知",
                "scrape_time": "未知",
                "date": "未知",
                "source_url": "https://github.com/v2rayc/v2rayc.github.io"
            }
        
        freev2_data = get_latest_freev2_data()
        bestclash_data = get_latest_bestclash_data()
        shaoyou_data = get_latest_shaoyou_data()
        ripao_data = get_latest_ripao_data()
        
        # 生成HTML页面
        generate_html_page({
            "dates": [], 
            "freev2": freev2_data,
            "bestclash": bestclash_data,
            "shaoyou": shaoyou_data,
            "ripao": ripao_data,
            "v2rayc": v2rayc_data
        })
        return
    
    # 仅生成HTML页面
    if args.generate_html:
        logger.info("仅生成HTML页面模式")
        if os.path.exists("web/data.json"):
            try:
                with open("web/data.json", "r", encoding="utf-8") as f:
                    results = json.load(f)
                generate_html_page(results)
            except Exception as e:
                logger.exception(f"读取数据文件并生成HTML页面时出错: {e}")
        else:
            logger.error("未找到数据文件 web/data.json，无法生成HTML页面")
        return
    
    # 爬取所有历史日期
    if args.all_dates:
        logger.info("爬取所有历史日期模式")
        date_tuples = get_all_dates_to_process()
        if date_tuples:
            fetch_and_process(date_tuples, not args.no_download, args.force_update)
        else:
            logger.warning("未能获取任何历史日期")
        return
    
    # 定时监控模式
    if args.monitor:
        logger.info(f"启动定时监控模式，间隔为 {args.interval} 小时")
        
        def check_and_fetch():
            """检查是否有新日期并爬取数据"""
            logger.info("开始检查新日期...")
            new_dates = get_new_dates()
            if new_dates:
                logger.info(f"发现 {len(new_dates)} 个新日期")
                fetch_and_process(new_dates, not args.no_download, args.force_update)
            else:
                logger.info("未发现新日期")
        
        # 立即执行一次
        check_and_fetch()
        
        # 如果启用了FreeV2.net爬取，也立即执行一次
        if FREEV2_ENABLED:
            fetch_freev2()
        
        # 设置定时任务
        schedule.every(args.interval).hours.do(check_and_fetch)
        
        # 新增: 设置每天零点爬取FreeV2.net的任务
        if FREEV2_ENABLED:
            logger.info("设置每天零点爬取FreeV2.net的任务")
            schedule.every().day.at("00:00").do(fetch_freev2)
        
        # 设置每天凌晨2点爬取v2rayc.github.io的任务
        if V2RAYC_ENABLED:
            logger.info("设置每天凌晨2点爬取v2rayc.github.io的任务")
            schedule.every().day.at("02:00").do(fetch_v2rayc)
        
        logger.info(f"定时任务已设置，每 {args.interval} 小时检查一次GitHub更新")
        if FREEV2_ENABLED:
            logger.info("每天零点自动爬取FreeV2.net")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次是否有待执行的任务
    
    # 默认模式：检查新日期并爬取
    else:
        logger.info("默认模式：检查新日期并爬取")
        new_dates = get_new_dates()
        if new_dates:
            logger.info(f"发现 {len(new_dates)} 个新日期")
            fetch_and_process(new_dates, not args.no_download, args.force_update)
        else:
            logger.info("未发现新日期")
        
        # 如果启用了FreeV2.net爬取，也执行一次
        if FREEV2_ENABLED:
            fetch_freev2()
        
        # 尝试获取其他订阅数据并生成HTML页面
        freev2_data = get_latest_freev2_data()
        bestclash_data = get_latest_bestclash_data()
        shaoyou_data = get_latest_shaoyou_data()
        ripao_data = get_latest_ripao_data()
        v2rayc_data = get_latest_v2rayc_data()
        
        # 读取所有日期数据
        if os.path.exists("web/data.json"):
            try:
                with open("web/data.json", "r", encoding="utf-8") as f:
                    results = json.load(f)
                
                # 生成HTML页面
                generate_html_page({
                    **results,
                    "freev2": freev2_data,
                    "bestclash": bestclash_data,
                    "shaoyou": shaoyou_data,
                    "ripao": ripao_data,
                    "v2rayc": v2rayc_data
                })
            except Exception as e:
                logger.exception(f"读取数据文件并生成HTML页面时出错: {e}")

# 添加fetch_ripao函数，放在其他fetch函数旁边（例如放在fetch_shaoyou函数后面）
def fetch_ripao():
    """
    获取日日更新节点永久订阅链接
    
    返回:
    dict: 包含订阅链接的字典
    """
    logger.info("开始获取日日更新节点订阅...")
    
    try:
        # 爬取订阅信息
        if RIPAO_ENABLED:
            result = ripao_scraper.scrape_ripao()
            
            if not result:
                logger.error("获取日日更新节点订阅失败")
                return None
            
            logger.info("成功获取日日更新节点订阅")
            
            # 下载订阅文件
            try:
                ripao_scraper.download_subscription_files(result)
                logger.info("成功下载日日更新节点订阅文件")
            except Exception as e:
                logger.exception(f"下载日日更新节点订阅文件时出错: {e}")
                
            return result
        else:
            logger.warning("日日更新节点爬取功能未启用")
            return None
    except Exception as e:
        logger.exception(f"获取日日更新节点订阅时出错: {e}")
        return None

def get_latest_ripao_data():
    """
    获取最新的日日更新节点订阅数据
    """
    json_file = "results/ripao/ripao_latest.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取最新日日更新节点数据时出错: {e}")
    
    # 如果文件不存在或读取出错，返回空数据
    return {
        "title": "日日更新节点永久订阅",
        "description": "永久固定的订阅地址，国内优先使用镜像订阅",
        "clash_link": "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash",
        "v2ray_link": "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
        "clash_mirror": "https://ghproxy.com/https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash",
        "v2ray_mirror": "https://ghproxy.com/https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
        "scrape_time": "未知",
        "update_interval": "日更新"
    }

def get_latest_freev2_data():
    """
    获取最新的FreeV2.net订阅数据
    """
    json_file = "results/freev2/freev2_latest.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取最新FreeV2.net数据时出错: {e}")
    
    # 如果文件不存在或读取出错，尝试获取一次
    if FREEV2_ENABLED:
        try:
            return fetch_freev2()
        except Exception as e:
            logger.exception(f"自动获取FreeV2.net数据时出错: {e}")
    
    # 都失败则返回空数据
    return {
        "subscription_link": "",
        "scrape_time": "未知",
        "source_url": "https://b.freev2.net/",
        "info": ""
    }

def get_latest_bestclash_data():
    """
    获取最新的BestClash订阅数据
    """
    json_file = "results/bestclash/bestclash_latest.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取最新BestClash数据时出错: {e}")
    
    # 如果文件不存在或读取出错，尝试获取一次
    try:
        return fetch_bestclash()
    except Exception as e:
        logger.exception(f"自动获取BestClash数据时出错: {e}")
    
    # 都失败则返回空数据
    return {
        "github_link": "https://github.com/PuddinCat/BestClash/raw/main/clash.yaml",
        "mirror_link": "https://fastly.jsdelivr.net/gh/PuddinCat/BestClash@main/clash.yaml",
        "scrape_time": "未知",
        "description": "免费Clash代理！自动从网上爬取最快的代理，每30分钟更新！"
    }

def get_latest_shaoyou_data():
    """
    获取最新的周润发公益v2ray节点订阅数据
    """
    json_file = "results/shaoyou/shaoyou_latest.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取最新周润发公益v2ray节点数据时出错: {e}")
    
    # 如果文件不存在或读取出错，尝试获取一次
    if SHAOYOU_ENABLED:
        try:
            return fetch_shaoyou()
        except Exception as e:
            logger.exception(f"自动获取周润发公益v2ray节点数据时出错: {e}")
    
    # 都失败则返回空数据
    return {
        "yaml_links": [],
        "base64_links": [],
        "mihomo_links": [],
        "no_proxy_links": {},
        "scrape_time": "未知",
        "description": "周润发公益v2ray节点，每2小时更新一次"
    }

def fetch_v2rayc():
    """
    获取v2rayc.github.io节点订阅链接
    
    返回:
    dict: 包含订阅链接的字典
    """
    logger.info("开始获取v2rayc.github.io节点订阅...")
    
    try:
        # 爬取订阅信息
        if V2RAYC_ENABLED:
            result = v2rayc_scraper.scrape_v2rayc()
            
            if not result:
                logger.error("获取v2rayc.github.io节点订阅失败")
                return None
            
            logger.info(f"成功获取v2rayc.github.io节点订阅，日期: {result.get('date', '未知')}")
            
            # 如果找到了链接，则尝试下载订阅文件
            if result.get('clash_links') or result.get('v2ray_links') or result.get('singbox_links'):
                try:
                    download_files = v2rayc_scraper.download_subscription_files(result)
                    if download_files:
                        logger.info(f"成功下载v2rayc.github.io节点订阅文件，共 {len(download_files)} 个文件")
                    else:
                        logger.warning("未能下载任何v2rayc.github.io节点订阅文件")
                except Exception as e:
                    logger.exception(f"下载v2rayc.github.io节点订阅文件时出错: {e}")
            else:
                logger.warning("v2rayc.github.io节点订阅中未找到任何链接")
                
            return result
        else:
            logger.warning("v2rayc.github.io节点爬取功能未启用")
            return None
    except Exception as e:
        logger.exception(f"获取v2rayc.github.io节点订阅时出错: {e}")
        return None

def download_v2rayc_files(result):
    """
    下载v2rayc.github.io的订阅文件
    
    参数:
    result (dict): 包含订阅链接的字典
    
    返回:
    list: 成功下载的文件列表
    """
    if not result:
        logger.warning("v2rayc.github.io节点订阅结果为空，无法下载文件")
        return []
    
    try:
        return v2rayc_scraper.download_subscription_files(result)
    except Exception as e:
        logger.exception(f"下载v2rayc.github.io订阅文件时出错: {e}")
        return []

def get_latest_v2rayc_data():
    """
    获取最新的v2rayc.github.io节点订阅数据
    """
    json_file = "results/v2rayc/v2rayc_latest.json"
    backup_files = []
    
    # 查找所有可能的备份文件
    if os.path.exists("results/v2rayc"):
        try:
            for file in os.listdir("results/v2rayc"):
                if file.startswith("v2rayc_") and file.endswith(".json") and file != "v2rayc_latest.json":
                    backup_files.append(os.path.join("results/v2rayc", file))
            # 按修改时间降序排序
            backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        except Exception as e:
            logger.warning(f"扫描v2rayc备份文件时出错: {e}")
    
    # 尝试读取最新文件
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取最新v2rayc.github.io数据时出错: {e}")
    
    # 如果最新文件读取失败，尝试获取一次新数据
    if V2RAYC_ENABLED:
        try:
            logger.info("尝试获取新的v2rayc.github.io数据...")
            v2rayc_data = fetch_v2rayc()
            if v2rayc_data:
                logger.info("成功获取新的v2rayc.github.io数据")
                return v2rayc_data
            else:
                logger.warning("获取新的v2rayc.github.io数据失败")
        except Exception as e:
            logger.exception(f"自动获取v2rayc.github.io数据时出错: {e}")
    
    # 如果获取新数据失败，尝试从备份文件中读取
    if backup_files:
        logger.info(f"尝试从 {len(backup_files)} 个备份文件中读取v2rayc数据...")
        for backup_file in backup_files:
            try:
                logger.info(f"尝试读取备份文件: {backup_file}")
                with open(backup_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"成功从备份文件读取v2rayc数据: {backup_file}")
                    
                    # 标记为备份数据
                    if "title" in data:
                        data["title"] = f"{data['title']}（备份数据）"
                    else:
                        data["title"] = "v2rayc.github.io节点（备份数据）"
                    
                    if "scrape_time" in data:
                        data["scrape_time"] = f"{data['scrape_time']}（备份）"
                    
                    return data
            except Exception as e:
                logger.warning(f"读取备份文件 {backup_file} 时出错: {e}")
    
    # 都失败则返回空数据
    logger.warning("无法获取v2rayc.github.io数据，返回空数据")
    return {
        "title": "v2rayc.github.io节点",
        "clash_links": [],
        "v2ray_links": [],
        "singbox_links": [],
        "update_time": "未知",
        "scrape_time": "未知",
        "date": "未知",
        "description": "v2rayc.github.io提供的免费节点",
        "source_url": "https://github.com/v2rayc/v2rayc.github.io"
    }

if __name__ == "__main__":
    main()