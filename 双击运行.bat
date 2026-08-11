@echo off
title AI采购助理 - 比价演示
cd /d D:\hermes\profiles\zhangliang\projectsi-procurement-assistant
set PYTHONIOENCODING=gbk

where python3 >nul 2>nul && (set PY=python3) || (set PY=python)
echo ============================================
echo   AI采购助理 - 自动跑通四家供应商比价
echo   （CSV / 邮件 / Excel / PDF 四种格式）
echo ============================================
echo.
%PY% main.py --input sample_data/ --no-llm
echo.
echo ============================================
echo   运行完毕！上面的输出就是结果。
echo   报告文件在 output 文件夹里，用记事本打开 .md 文件即可。
echo ============================================
pause >nul
