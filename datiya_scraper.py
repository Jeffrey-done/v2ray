#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime, timedelta

def scrape_datiya(date=None):
    """
    爬取 free.datiya.com 网页的订阅链接和节点信息
    
    参数:
    date (str, optional): 要爬取的日期，格式为'YYYYMMDD'，例如'20250403'。
                         如果为None，则爬取最新的页面。
    
    返回:
    dict: 包含爬取结果的字典
    """
    if date:
        # 验证日期格式
        try:
            datetime.strptime(date, '%Y%m%d')
            url = f"https://free.datiya.com/post/{date}/"
        except ValueError:
            print(f"无效的日期格式: {date}，应为'YYYYMMDD'")
            return None
    else:
        # 默认爬取最新页面
        url = "https://free.datiya.com/post/20250403/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"开始爬取页面: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        html_content = response.text
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找标题
        title = soup.find('h1').text.strip() if soup.find('h1') else "未找到标题"
        
        # 查找更新时间
        update_time_pattern = re.compile(r'更新时间.*?(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})')
        update_time_match = re.search(update_time_pattern, html_content)
        update_time = update_time_match.group(1) if update_time_match else "未找到更新时间"
        
        # 查找订阅链接
        clash_link_pattern = re.compile(r'https://free\.datiya\.com/uploads/\d+-clash\.yaml')
        clash_links = re.findall(clash_link_pattern, html_content)
        
        v2ray_link_pattern = re.compile(r'https://free\.datiya\.com/uploads/\d+-v2ray\.txt')
        v2ray_links = re.findall(v2ray_link_pattern, html_content)
        
        # 获取节点概览信息
        nodes_info = {}
        nodes_info_section = soup.find(string=re.compile('今日节点概览'))
        if nodes_info_section and nodes_info_section.parent:
            info_section = nodes_info_section.parent.find_next('ul')
            if info_section:
                for li in info_section.find_all('li'):
                    if li.text:
                        key_val = li.text.split(':', 1)
                        if len(key_val) == 2:
                            nodes_info[key_val[0].strip()] = key_val[1].strip()
        
        # 整理结果
        result = {
            "title": title,
            "update_time": update_time,
            "clash_links": list(set(clash_links)),
            "v2ray_links": list(set(v2ray_links)),
            "nodes_info": nodes_info,
            "scrape_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_url": url
        }
        
        # 保存结果
        save_result(result)
        
        return result
        
    except requests.RequestException as e:
        print(f"请求错误: {e}")
        return None
    except Exception as e:
        print(f"发生错误: {e}")
        return None

def save_result(result):
    """
    将爬取结果保存到文件
    """
    # 创建results目录(如果不存在)
    if not os.path.exists("results"):
        os.makedirs("results")
    
    # 提取日期用于文件名
    if result.get("source_url"):
        match = re.search(r'\/post\/(\d+)\/', result["source_url"])
        date_str = match.group(1) if match else datetime.now().strftime('%Y%m%d')
    else:
        date_str = datetime.now().strftime('%Y%m%d')
    
    # 保存JSON结果
    json_filename = f"results/datiya_{date_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 保存文本结果
    txt_filename = f"results/datiya_{date_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"标题: {result['title']}\n")
        f.write(f"更新时间: {result['update_time']}\n")
        f.write(f"爬取时间: {result['scrape_time']}\n")
        f.write(f"来源: {result.get('source_url', '未知')}\n\n")
        
        f.write("Clash订阅链接:\n")
        for link in result['clash_links']:
            f.write(f"- {link}\n")
        
        f.write("\nV2ray订阅链接:\n")
        for link in result['v2ray_links']:
            f.write(f"- {link}\n")
        
        f.write("\n节点信息概览:\n")
        for key, value in result['nodes_info'].items():
            f.write(f"- {key}: {value}\n")
    
    print(f"结果保存到: {json_filename}")
    print(f"结果保存到: {txt_filename}")
    
    return json_filename, txt_filename

def download_subscription_files(result):
    """
    下载订阅文件
    """
    # 创建downloads目录(如果不存在)
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    downloaded_files = []
    
    # 下载Clash配置
    for link in result.get('clash_links', []):
        try:
            filename = os.path.basename(link)
            filepath = f"downloads/{filename}"
            response = requests.get(link, headers=headers, timeout=10)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"已下载: {filename}")
            downloaded_files.append(filepath)
        except Exception as e:
            print(f"下载 {link} 时出错: {e}")
    
    # 下载V2ray配置
    for link in result.get('v2ray_links', []):
        try:
            filename = os.path.basename(link)
            filepath = f"downloads/{filename}"
            response = requests.get(link, headers=headers, timeout=10)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"已下载: {filename}")
            downloaded_files.append(filepath)
        except Exception as e:
            print(f"下载 {link} 时出错: {e}")
    
    return downloaded_files

def scrape_last_days(days=7):
    """
    爬取最近几天的数据
    
    参数:
    days (int): 要爬取的天数
    
    返回:
    list: 包含爬取结果的列表
    """
    results = []
    today = datetime.now()
    
    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y%m%d')
        print(f"\n爬取 {date_str} 的数据...")
        result = scrape_datiya(date_str)
        if result:
            results.append(result)
        else:
            print(f"无法爬取 {date_str} 的数据")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="爬取 free.datiya.com 的订阅链接和节点信息")
    parser.add_argument("--date", help="要爬取的日期，格式为YYYYMMDD，例如20250403", default=None)
    parser.add_argument("--days", type=int, help="爬取最近几天的数据", default=0)
    parser.add_argument("--download", action="store_true", help="是否下载订阅文件")
    
    args = parser.parse_args()
    
    if args.days > 0:
        print(f"爬取最近 {args.days} 天的数据...")
        results = scrape_last_days(args.days)
        if args.download:
            for result in results:
                download_subscription_files(result)
    else:
        print(f"爬取 {args.date or '最新'} 的数据...")
        result = scrape_datiya(args.date)
        
        if result:
            print("\n爬取结果:")
            print(f"标题: {result['title']}")
            print(f"更新时间: {result['update_time']}")
            
            print("\nClash订阅链接:")
            for link in result['clash_links']:
                print(f"- {link}")
            
            print("\nV2ray订阅链接:")
            for link in result['v2ray_links']:
                print(f"- {link}")
            
            print("\n节点信息概览:")
            for key, value in result['nodes_info'].items():
                print(f"- {key}: {value}")
            
            if args.download:
                print("\n开始下载订阅文件...")
                download_subscription_files(result)
                print("下载完成!")
            elif not args.days:  # 只有在非批量模式下才询问
                answer = input("\n是否下载订阅文件? (y/n): ")
                if answer.lower() == 'y':
                    download_subscription_files(result)
                    print("下载完成!")
        else:
            print("爬取失败.") 