#!/bin/bash
# Clash/V2Ray 免费节点订阅爬虫自动运行脚本

# 设置颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 显示标题
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}      Clash/V2Ray 免费节点订阅爬虫${NC}"
echo -e "${BLUE}================================================${NC}"

# 设置Python环境
export PYTHONIOENCODING=utf-8

# 检查依赖
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}错误: 需要Python3但未安装。${NC}" >&2; exit 1; }

# 检查必要文件
if [ ! -f "monitor_and_fetch.py" ]; then
    echo -e "${RED}错误: 未找到monitor_and_fetch.py文件。${NC}"
    echo -e "${YELLOW}请确保你在正确的目录下运行此脚本。${NC}"
    exit 1
fi

# 显示菜单
echo -e "\n${YELLOW}请选择操作:${NC}"
echo -e "${GREEN}1.${NC} 爬取所有日期并生成页面"
echo -e "${GREEN}2.${NC} 仅爬取新日期（如果有）"
echo -e "${GREEN}3.${NC} 强制更新所有日期"
echo -e "${GREEN}4.${NC} 仅重新生成HTML页面"
echo -e "${GREEN}5.${NC} 启动定时监控模式（每6小时检查一次，每天零点自动爬取FreeV2.net）"
echo -e "${GREEN}6.${NC} 仅爬取FreeV2.net订阅"
echo -e "${GREEN}7.${NC} 仅爬取BestClash订阅"
echo -e "${GREEN}8.${NC} 仅爬取周润发公益v2ray节点"
echo -e "${GREEN}9.${NC} 仅爬取日日更新节点永久订阅"
echo -e "${GREEN}10.${NC} 仅爬取v2rayc.github.io节点订阅"
echo -e "${GREEN}0.${NC} 退出"

# 读取用户输入
read -p "请输入选项 [0-10]: " choice

# 根据用户选择执行相应操作
case $choice in
    1)
        echo -e "\n${BLUE}开始爬取所有日期并生成页面...${NC}"
        python3 monitor_and_fetch.py --all-dates
        ;;
    2)
        echo -e "\n${BLUE}开始检查新日期并爬取...${NC}"
        python3 monitor_and_fetch.py
        ;;
    3)
        echo -e "\n${BLUE}开始强制更新所有日期...${NC}"
        python3 monitor_and_fetch.py --all-dates --force-update
        ;;
    4)
        echo -e "\n${BLUE}仅重新生成HTML页面...${NC}"
        python3 monitor_and_fetch.py --generate-html
        ;;
    5)
        echo -e "\n${BLUE}启动定时监控模式（每6小时检查一次，每天零点自动爬取FreeV2.net）...${NC}"
        echo -e "${YELLOW}提示: 按Ctrl+C可以停止监控。${NC}"
        python3 monitor_and_fetch.py --monitor
        ;;
    6)
        echo -e "\n${BLUE}仅爬取FreeV2.net订阅...${NC}"
        python3 monitor_and_fetch.py --freev2
        ;;
    7)
        echo -e "\n${BLUE}仅爬取BestClash订阅...${NC}"
        python3 monitor_and_fetch.py --bestclash
        ;;
    8)
        echo -e "\n${BLUE}仅爬取周润发公益v2ray节点...${NC}"
        python3 monitor_and_fetch.py --shaoyou
        ;;
    9)
        echo -e "\n${BLUE}仅爬取日日更新节点永久订阅...${NC}"
        python3 monitor_and_fetch.py --ripao
        ;;
    10)
        echo -e "\n${BLUE}仅爬取v2rayc.github.io节点订阅...${NC}"
        python3 monitor_and_fetch.py --v2rayc
        ;;
    0)
        echo -e "\n${GREEN}感谢使用，再见！${NC}"
        exit 0
        ;;
    *)
        echo -e "\n${RED}无效的选择，请重新运行脚本并选择有效的选项。${NC}"
        exit 1
        ;;
esac

# 操作完成提示
if [ $choice -ne 5 ]; then
    echo -e "\n${GREEN}操作已完成！${NC}"
    
    # 如果生成了HTML页面，提示用户查看
    if [ -f "web/index.html" ]; then
        echo -e "${YELLOW}提示: 你可以在web目录下查看生成的HTML页面。${NC}"
        echo -e "${BLUE}在浏览器中打开 web/index.html 以查看结果。${NC}"
    fi
fi

# 给予脚本执行权限
chmod +x auto_run.sh 