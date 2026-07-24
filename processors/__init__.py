"""
渲染处理器 — 从已清洗数据表生成 HTML 可视化看板

模块:
    data_loader  — 统一加载 data/sheets/ 下的所有数据表
    base         — 渲染器基类（页面通用框架）
    utils        — 渲染辅助（金额格式化等）
    p1_overview  — P1: 总指标 + 年度达成
    p2_monthly   — P2: 月度指标 + 月度达成
    p3_sales     — P3: 销售排名 + 饼图
    p4_yoy       — P4: 同比分析（年基线数据存在时显示）
    run          — 主入口，调用全部渲染器并合并为单个 HTML 看板
"""
