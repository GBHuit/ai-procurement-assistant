#!/usr/bin/env python3
"""生成 双击运行.bat（GBK编码）——支持拖拽文件/文件夹"""
content = '''@echo off
title AI采购助理 - 比价演示
cd /d D:\\hermes\\profiles\\zhangliang\\projects\\ai-procurement-assistant
set PYTHONIOENCODING=gbk

where python3 >nul 2>nul && (set PY=python3) || (set PY=python)

rem 拖拽用法：把报价单文件或文件夹拖到本图标上松开即可
if "%~1"=="" (
  set INPUT=sample_data
  echo 未拖入文件，默认跑样例数据（4家供应商）
) else (
  set INPUT=%~1
  echo 已收到文件：%~nx1
)
echo.
echo ============================================
echo   AI采购助理 - 开始比价
echo ============================================
echo.
%PY% main.py --input "%INPUT%" --no-llm
echo.
echo ============================================
echo   运行完毕！报告在 output 文件夹里。
echo   （想把多家报价放一起比，就把它们放进同一个
echo     文件夹，然后整个文件夹拖进来）
echo ============================================
pause >nul
'''
with open(r"D:\hermes\profiles\zhangliang\projects\ai-procurement-assistant\双击运行.bat", "w", encoding="gbk") as f:
    f.write(content)
print("bat已生成(GBK)")
