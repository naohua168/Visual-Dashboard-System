# Author: naohua168 <bai_bai168@qq.com>
"""渲染处理器 — 从已清洗数据表生成 HTML 可视化看板

分层（自下而上）:
    data_loader    — 统一加载 data/sheets/ 下的所有数据表
    page_data      — 数据计算层（纯 pandas，零 HTML；prepare_*_data 供各页调用）
    page_data_utils— 数据层共享工具（拆分键/归并/透视/排序）

    base           — 渲染器基类 + 样式/脚本/组件汇总出口
    utils          — 渲染辅助（fmt_wan/fmt_pct/fmt_yoy）
    components     — 共享 HTML 组件（cell_bg/mini_rate/dept_card 等）
    hero           — Hero 圆环与同比小卡
    config_loader  — 展示规则加载器 + 客户筛选器

    pages/         — 页面包（每页一个模块）
        overview / annual / monthly / quarterly / sales / yoy
    page_*.py      — 兼容层：旧导入路径 re-export 到 pages/（新代码请用 processors.pages）
    sales_pending  — 待确认客户弹窗
    static/css/    — 样式包（variables/layout/kpi/tables/cards/yoy/widgets/hero/
                     annual/matrix/yoy_tables/overview/responsive/animations）
    static/js/     — 脚本包（nav/page_switch/counters/text/charts/tables/tabs）
    run            — 主入口，调用全部渲染器并合并为单个 HTML 看板
"""
