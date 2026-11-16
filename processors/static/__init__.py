# Author: naohua168 <bai_bai168@qq.com>
"""静态资源模块 — 看板 CSS/JS 常量

注：chart.umd.min.js **不内联**进产物（6 个页面全是表格，代码里没有图表调用）。
保留该文件只作将来图表化的备选资源；真要启用时必须在 processors/run.py 里本地内联，
不要走 CDN（内网/断网会静默失败）。
"""
