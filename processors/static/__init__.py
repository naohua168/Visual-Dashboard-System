# Author: naohua168 <bai_bai168@qq.com>
"""静态资源模块 — 看板 CSS/JS 常量

注：chart.umd.min.js 自 2026-11-04 起**不再内联**进产物（6 个页面全是表格，
代码里从未调用 new Chart / __regChart）。保留该文件只作将来图表化的备选资源；
真要启用时必须在 processors/run.py 里做本地内联，不要走 CDN（内网/断网会静默失败）。
"""
