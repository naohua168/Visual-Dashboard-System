"""
渲染处理器 — 从已清洗数据表生成 HTML 可视化看板

模块:
    page_data      — 数据计算层（纯 pandas，零 HTML）
    data_loader    — 统一加载 data/sheets/ 下的所有数据表
    base           — 渲染器基类（CSS/JS/Hero圆环/页面框架）
    utils          — 渲染辅助（fmt_wan/fmt_pct/fmt_yoy）
    components     — 共享 HTML 组件（cell_bg/mini_rate/dept_card等）
    config_loader  — 展示规则加载器 + 客户筛选器
    page_overview  — 数据总览页
    page_annual    — 年度达成页
    page_monthly   — 月度达成页
    page_quarterly — 季度达成页
    page_sales     — 销售达成页
    page_yoy       — 年度同比页
    sales_pending  — 待确认客户弹窗
    run            — 主入口，调用全部渲染器并合并为单个 HTML 看板
"""
