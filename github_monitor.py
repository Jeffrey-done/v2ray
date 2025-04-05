#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
import logging
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_monitor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("github_monitor")

def fetch_github_dates_from_url(url="https://raw.githubusercontent.com/Jeffrey-done/clash-freenode/main/README.md"):
    """
    从GitHub仓库的原始README文件中获取节点日期信息
    
    参数:
    url (str): README原始文件的URL
    
    返回:
    list: 日期和节点数元组的列表 [(YYYYMMDD, node_count), ...]，按时间降序排列
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info(f"开始从原始README文件获取日期信息: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        readme_content = response.text
        
        # 提取日期表格部分
        dates = []
        
        # 使用正则表达式直接提取表格中的日期和节点数据
        # 匹配格式为 | 2025-04-05 | 20 | 这样的行
        date_pattern = r'\|\s*(20\d{2}-\d{2}-\d{2})\s*\|\s*(\d+)\s*\|'
        date_matches = re.findall(date_pattern, readme_content)
        
        for date_match in date_matches:
            date_str = date_match[0].replace('-', '')  # 转换为YYYYMMDD格式
            node_count = int(date_match[1])
            dates.append((date_str, node_count))
        
        # 如果没有找到日期表格，尝试查找"最后更新"字段
        if not dates:
            logger.warning("未在表格中找到日期，尝试从文本中提取")
            update_pattern = r'最后更新.*?[`"](20\d{2}-\d{2}-\d{2})[`"]'
            update_match = re.search(update_pattern, readme_content)
            if update_match:
                date_str = update_match.group(1).replace('-', '')
                dates.append((date_str, 0))  # 节点数未知，用0表示
        
        if dates:
            # 按日期降序排序
            sorted_dates = sorted(dates, key=lambda x: x[0], reverse=True)
            logger.info(f"成功获取到 {len(sorted_dates)} 个日期")
            # 打印前3个日期进行确认
            for i, date_tuple in enumerate(sorted_dates[:3]):
                formatted_date = f"{date_tuple[0][:4]}-{date_tuple[0][4:6]}-{date_tuple[0][6:8]}"
                logger.info(f"日期 {i+1}: {formatted_date}, 节点数: {date_tuple[1]}")
            return sorted_dates
        else:
            logger.warning("未找到日期信息")
            return []
            
    except requests.RequestException as e:
        logger.error(f"请求GitHub时出错: {e}")
        return []
    except Exception as e:
        logger.exception(f"获取GitHub日期信息时出错: {e}")
        return []

def extract_text_from_markdown(markdown_content):
    """
    从Markdown内容中提取文本，用于辅助解析README内容
    
    参数:
    markdown_content (str): Markdown格式的内容
    
    返回:
    str: 提取的纯文本
    """
    # 移除链接格式，保留链接文本
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', markdown_content)
    # 移除图片
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # 移除代码块
    text = re.sub(r'```[^`]*```', '', text)
    # 移除内联代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 移除标题符号
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    return text

def fetch_github_dates(repo_url="https://github.com/OpenRunner/clash-freenode"):
    """
    从GitHub仓库网页获取节点日期信息
    
    参数:
    repo_url (str): GitHub仓库的URL
    
    返回:
    list: 日期和节点数元组的列表 [(YYYYMMDD, node_count), ...]，按时间降序排列
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info(f"开始从GitHub获取日期信息: {repo_url}")
        response = requests.get(repo_url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找日期表格
        date_tuples = []
        
        # 查找表格中的日期数据
        tables = soup.find_all('table')
        for table in tables:
            for row in table.find_all('tr')[1:]:  # 跳过表头
                columns = row.find_all('td')
                if len(columns) >= 2:
                    date_text = columns[0].text.strip()
                    node_count_text = columns[1].text.strip()
                    
                    # 提取YYYY-MM-DD格式的日期
                    date_match = re.search(r'(20\d{2}-\d{2}-\d{2})', date_text)
                    if date_match:
                        node_count = int(node_count_text) if node_count_text.isdigit() else 0
                        date_str = date_match.group(1).replace('-', '')  # 转换为YYYYMMDD格式
                        date_tuples.append((date_str, node_count))
        
        # 如果没有在表格中找到日期，尝试从文本中提取
        if not date_tuples:
            logger.warning("未在表格中找到日期，尝试从文本中提取")
            # 查找日期表格的纯文本格式
            table_pattern = r'\|\s*(20\d{2}-\d{2}-\d{2})\s*\|\s*(\d+)\s*\|'
            date_matches = re.findall(table_pattern, html_content)
            for date_match in date_matches:
                date_str = date_match[0].replace('-', '')  # 转换为YYYYMMDD格式
                node_count = int(date_match[1]) if date_match[1].isdigit() else 0
                date_tuples.append((date_str, node_count))
            
            # 如果还是没找到，尝试查找更新日期文本
            if not date_tuples:
                update_patterns = [
                    r'最后更新.*?[`"](20\d{2}-\d{2}-\d{2})[`"]',
                    r'更新时间.*?(20\d{2}-\d{2}-\d{2})'
                ]
                
                for pattern in update_patterns:
                    update_match = re.search(pattern, html_content)
                    if update_match:
                        date_str = update_match.group(1).replace('-', '')  # 转换为YYYYMMDD格式
                        date_tuples.append((date_str, 0))  # 节点数未知，用0表示
                        break
        
        if date_tuples:
            # 去重并按日期降序排序
            unique_dates = []
            seen_dates = set()
            for date_tuple in date_tuples:
                if date_tuple[0] not in seen_dates:
                    unique_dates.append(date_tuple)
                    seen_dates.add(date_tuple[0])
            
            sorted_dates = sorted(unique_dates, key=lambda x: x[0], reverse=True)
            logger.info(f"成功获取到 {len(sorted_dates)} 个日期")
            # 打印前3个日期进行确认
            for i, date_tuple in enumerate(sorted_dates[:3]):
                formatted_date = f"{date_tuple[0][:4]}-{date_tuple[0][4:6]}-{date_tuple[0][6:8]}"
                logger.info(f"日期 {i+1}: {formatted_date}, 节点数: {date_tuple[1]}")
            return sorted_dates
        else:
            logger.warning("未找到日期信息")
            return []
            
    except requests.RequestException as e:
        logger.error(f"请求GitHub时出错: {e}")
        return []
    except Exception as e:
        logger.exception(f"获取GitHub日期信息时出错: {e}")
        return []

def fetch_manually_specified_dates():
    """
    手动指定日期和节点数，用于在网络请求失败时提供备选数据
    
    返回:
    list: 日期和节点数元组的列表 [(YYYYMMDD, node_count), ...]，按时间降序排列
    """
    # 根据图片中看到的表格内容手动指定日期和节点数
    dates = [
        ("20250405", 20),
        ("20250404", 23),
        ("20250403", 22),
        ("20250401", 13),
        ("20250331", 24),
        ("20250330", 21),
        ("20250329", 21),
        ("20250328", 21),
        ("20250327", 26),
        ("20250326", 22)
    ]
    logger.info(f"使用手动指定的 {len(dates)} 个日期")
    return dates

def get_all_dates():
    """
    获取所有可用的日期信息，尝试多种方式
    
    返回:
    list: 日期和节点数元组的列表 [(YYYYMMDD, node_count), ...]，按时间降序排列
    """
    # 优先从原始README文件获取
    dates = fetch_github_dates_from_url()
    
    # 如果失败，尝试从仓库页面获取
    if not dates:
        logger.warning("从原始README文件获取日期失败，尝试从仓库页面获取")
        dates = fetch_github_dates()
    
    # 如果仍然失败，使用手动指定的日期
    if not dates:
        logger.warning("从仓库页面获取日期失败，使用手动指定的日期")
        dates = fetch_manually_specified_dates()
    
    return dates

def get_last_processed_date():
    """
    获取上次处理的最新日期
    
    返回:
    str: 上次处理的最新日期，格式为YYYYMMDD，如果没有则返回None
    """
    history_file = "github_monitor_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return history.get('last_date')
        except Exception as e:
            logger.exception(f"读取历史记录文件出错: {e}")
    return None

def save_last_processed_date(date):
    """
    保存最新处理的日期
    
    参数:
    date (str): 日期，格式为YYYYMMDD
    """
    history_file = "github_monitor_history.json"
    try:
        history = {'last_date': date, 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存最新处理日期: {date}")
    except Exception as e:
        logger.exception(f"保存历史记录文件出错: {e}")

def get_new_dates():
    """
    获取需要处理的新日期
    
    返回:
    list: 需要处理的日期列表，格式为 [(YYYYMMDD, node_count), ...]，按时间降序排列
    """
    all_date_tuples = get_all_dates()
    last_date = get_last_processed_date()
    
    if not all_date_tuples:
        logger.warning("没有获取到任何日期")
        return []
    
    if not last_date:
        logger.info("没有历史记录，将处理所有日期")
        return all_date_tuples
    
    # 查找需要处理的新日期
    new_date_tuples = []
    for date_tuple in all_date_tuples:
        if date_tuple[0] > last_date:
            new_date_tuples.append(date_tuple)
        else:
            break  # 日期已按降序排列，遇到小于等于上次处理的日期时可以停止
    
    logger.info(f"找到 {len(new_date_tuples)} 个新日期需要处理")
    return new_date_tuples

def get_all_dates_to_process():
    """
    获取所有需要处理的日期，无论是否处理过
    
    返回:
    list: 所有日期和节点数元组的列表 [(YYYYMMDD, node_count), ...]，按时间降序排列
    """
    all_date_tuples = get_all_dates()
    
    if not all_date_tuples:
        logger.warning("没有获取到任何日期")
        return []
    
    logger.info(f"获取到 {len(all_date_tuples)} 个日期需要处理")
    return all_date_tuples

if __name__ == "__main__":
    # 测试代码
    print("获取GitHub日期信息...")
    dates = get_all_dates()
    print(f"找到 {len(dates)} 个日期:")
    for date_tuple in dates:
        date_str = f"{date_tuple[0][:4]}-{date_tuple[0][4:6]}-{date_tuple[0][6:8]}"
        print(f"- {date_str} (节点数: {date_tuple[1]})") 