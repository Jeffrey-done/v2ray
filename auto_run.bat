@echo off
chcp 65001 >nul
title Clash/V2Ray 免费节点订阅爬虫

:: 设置颜色
set "GREEN=[92m"
set "BLUE=[94m"
set "RED=[91m"
set "YELLOW=[93m"
set "NC=[0m"

:: 显示标题
echo %BLUE%================================================%NC%
echo %GREEN%      Clash/V2Ray 免费节点订阅爬虫%NC%
echo %BLUE%================================================%NC%

:: 设置Python环境
set PYTHONIOENCODING=utf-8

:: 检查必要文件
if not exist "monitor_and_fetch.py" (
    echo %RED%错误: 未找到monitor_and_fetch.py文件。%NC%
    echo %YELLOW%请确保你在正确的目录下运行此脚本。%NC%
    goto :END
)

:: 显示菜单
echo.
echo %YELLOW%请选择操作:%NC%
echo %GREEN%1.%NC% 爬取所有日期并生成页面
echo %GREEN%2.%NC% 仅爬取新日期（如果有）
echo %GREEN%3.%NC% 强制更新所有日期
echo %GREEN%4.%NC% 仅重新生成HTML页面
echo %GREEN%5.%NC% 启动定时监控模式（每6小时检查一次）
echo %GREEN%6.%NC% 仅爬取FreeV2.net订阅
echo %GREEN%7.%NC% 仅爬取BestClash订阅
echo %GREEN%8.%NC% 仅爬取周润发公益v2ray节点
echo %GREEN%9.%NC% 仅爬取日日更新节点永久订阅
echo %GREEN%10.%NC% 仅爬取v2rayc.github.io节点订阅
echo %GREEN%0.%NC% 退出

:: 读取用户输入
set /p choice="请输入选项 [0-10]: "

:: 根据用户选择执行相应操作
if "%choice%"=="1" (
    echo.
    echo %BLUE%开始爬取所有日期并生成页面...%NC%
    python monitor_and_fetch.py --all-dates
    goto :COMPLETE
)

if "%choice%"=="2" (
    echo.
    echo %BLUE%开始检查新日期并爬取...%NC%
    python monitor_and_fetch.py
    goto :COMPLETE
)

if "%choice%"=="3" (
    echo.
    echo %BLUE%开始强制更新所有日期...%NC%
    python monitor_and_fetch.py --all-dates --force-update
    goto :COMPLETE
)

if "%choice%"=="4" (
    echo.
    echo %BLUE%仅重新生成HTML页面...%NC%
    python monitor_and_fetch.py --generate-html
    goto :COMPLETE
)

if "%choice%"=="5" (
    echo.
    echo %BLUE%启动定时监控模式（每6小时检查一次，每天零点自动爬取FreeV2.net）...%NC%
    echo %YELLOW%提示: 按Ctrl+C可以停止监控。%NC%
    python monitor_and_fetch.py --monitor
    goto :END
)

if "%choice%"=="6" (
    echo.
    echo %BLUE%仅爬取FreeV2.net订阅...%NC%
    python monitor_and_fetch.py --freev2
    goto :COMPLETE
)

if "%choice%"=="7" (
    echo.
    echo %BLUE%仅爬取BestClash订阅...%NC%
    python monitor_and_fetch.py --bestclash
    goto :COMPLETE
)

if "%choice%"=="8" (
    echo.
    echo %BLUE%仅爬取周润发公益v2ray节点...%NC%
    python monitor_and_fetch.py --shaoyou
    goto :COMPLETE
)

if "%choice%"=="9" (
    echo.
    echo %BLUE%仅爬取日日更新节点永久订阅...%NC%
    python monitor_and_fetch.py --ripao
    goto :COMPLETE
)

if "%choice%"=="10" (
    echo.
    echo %BLUE%仅爬取v2rayc.github.io节点订阅...%NC%
    python monitor_and_fetch.py --v2rayc
    goto :COMPLETE
)

if "%choice%"=="0" (
    echo.
    echo %GREEN%感谢使用，再见！%NC%
    goto :END
)

echo.
echo %RED%无效的选择，请重新运行脚本并选择有效的选项。%NC%
goto :END

:COMPLETE
echo.
echo %GREEN%操作已完成！%NC%

:: 如果生成了HTML页面，提示用户查看
if exist "web\index.html" (
    echo %YELLOW%提示: 你可以在web目录下查看生成的HTML页面。%NC%
    echo %BLUE%在浏览器中打开 web\index.html 以查看结果。%NC%
)

:END
pause 