# Visual Dashboard System

> 销售数据可视化看板生成系统 — 从原始 Excel 到 6 页交互式 HTML 看板的自动化流水线

---

## 快速开始

```bash
pip install -r requirements.txt
python main.py                           # 全流程: 年基线 → 清洗 → 拆分 → 渲染
python main.py --dry-run                 # 预检（检查 raw/mappings/config）
# 看板在 output/看板/看板_YYYYMMDD.html
```

## 目录结构

```
Visual Dashboard_system/
├── main.py                           # ★ 顶层调度器（argparse + subprocess）
├── run_all.bat                       # Windows 双击运行
├── config/
│   ├── 清洗配置/
│   │   └── cleaning_config.json      # ★ 清洗核心配置（数据源/列映射/时间/输出/映射路径指针）
│   ├── 前端展示配置/
│   │   └── 看板展示配置.json          #   页面顺序/标题/事业部配色/输出命名
│   └── 销售规则/                      #   客户统称名单.json + 客户销售对应规则.json
├── data/
│   ├── raw/                          # 【用户维护】原始 Excel（财务端/运营端/往期/客户名单）
│   ├── mappings/                     # 清洗映射（部门/客户），不上传 Git
│   │   ├── 部门事业部映射/           #   全称→简称（收入版4条 + 回款版50+条）
│   │   └── 客户名单/                 #   白名单 JSON
│   └── sheets/                       # 【系统生成】清洗输出（不上传 Git）
│       ├── 手动维护/                 # 【用户维护】总指标 / 月度收入指标 / 月度回款指标
│       └── 系统数据清理/             # 月收入/月回款 当年累计 季度累计 销售收入/回款 往年收入/回款
├── engine/                           # ★ 数据清洗引擎
│   ├── core/                         #   config / utils / column_resolver / customer_matcher / mapping_loader
│   ├── income_payment/               #   Phase 1+2: financial.py + operations.py + run.py
│   ├── sales/                        #   Phase 3: splitter.py + run.py
│   └── yearly_baseline/              #   Phase 0: cleaner.py + run.py
├── processors/                       # ★ 渲染层（6 页看板）
│   ├── base.py                       #   全站共用 CSS/JS 框架 + Hero 圆环
│   ├── utils.py                      #   格式化（fmt_wan 全局.0f / fmt_pct / fmt_yoy）
│   ├── data_loader.py                #   13 个 Sheet 统一加载 + 客户统称聚合
│   ├── page_overview.py              #   数据总览
│   ├── page_annual.py                #   年度达成
│   ├── page_monthly.py               #   月度达成
│   ├── page_quarterly.py             #   季度达成
│   ├── page_sales.py                 #   销售达成（3 卡片）
│   ├── page_yoy.py                   #   年度同比
│   └── sales_pending.py              #   待确认客户弹窗
├── tests/                            # 14 文件，93 用例（93 passed）
├── docs/                             # 设计文档
│   └── 数据系统设计.md                #   完整数据层文档
└── output/                           # ★ 看板输出（不上传 Git）
    ├── 看板/看板_YYYYMMDD.html        #   6 页可视化看板
    └── 数据/data_YYYYMMDD.xlsx        #   11 Sheet 数据总表
```

## 使用流程

### 1. 准备数据
- 将财务端 Excel 放入 `data/raw/财务端数据/`
- 将运营端 Excel 放入 `data/raw/运营端数据/`
- 将往年数据放入 `data/raw/往年收入数据/` 和 `data/raw/往年回款数据/`
- 维护 `data/sheets/手动维护/` 下的指标表

### 2. 运行

```bash
python main.py                          # 全流程
python main.py --step=yearly            # 只年基线
python main.py --step=clean             # 只清洗 Phase 1+2
python main.py --step=split             # 只销售拆分
python main.py --step=render            # 只渲染
python main.py --type=收入              # 只收入链路
python main.py --from=clean --to=render # 区间执行
python main.py --dry-run                # 预检（不写文件）
python main.py --list                   # 列出所有步骤

# 调试用（等价于对应 step）
python -m engine.yearly_baseline.run
python -m engine.income_payment.run --type=收入
python -m engine.sales.run
python -m processors.run
```

### 3. 获取结果
- `output/看板/看板_YYYYMMDD.html` — 6 页可视化看板
- `output/数据/data_YYYYMMDD.xlsx` — 11 Sheet 数据总表

### 4. 运行测试

```bash
python -m pytest tests/ -v              # 93 用例（93 passed）
python -m pytest tests/ -k "splitter"   # 按关键字
```

## 4-Phase 流水线

```
Phase 0: 年基线清洗  →  往年收入数据/*.xlsx + 往年回款数据/*.xlsx → 往年收入/往年回款（6列）
Phase 1+2: 收入/回款  →  财务端(当月) + 运营端(当年累计) → 三路输出（月/季度/当年累计）
Phase 3: 销售拆分    →  4层匹配(广东→深圳→其他规则→默认规则(统称继承)→待确认) + 总额校验 → 销售收入/回款（7列）
Phase 4: 渲染看板    →  6页HTML + Excel总表 → output/
```

## 看板 6 页（顺序由 `看板展示配置.json` 控制）

| 页面 | page_id | 内容 |
|------|---------|------|
| 数据总览 | overview | Hero 总指标+双环 / 事业部矩阵 / Top10 |
| 年度达成 | annual | Hero 总指标+双环 / 客户达成矩阵(cell-bg) |
| 月度达成 | monthly | Hero 总指标+双环 / 事业部+客户矩阵 |
| 季度达成 | quarterly | Hero 总指标+双环 / 客户达成矩阵 / 数据范围 Banner |
| 销售达成 | sales | 卡片1:mini-rate 排行 / 卡片2:事业部矩阵 / 卡片3:销售×客户矩阵 |
| 年度同比 | yoy | 与 2024 同期(4-6月)对比 / 事业部同比表 / 客户同比矩阵 |

## 核心设计

| 设计 | 说明 |
|------|------|
| 配置驱动 | 清洗参数全在 `cleaning_config.json`，页面/配色全在 `看板展示配置.json`，改日期/列名不需改代码 |
| 列名映射 | 每个字段多个备选列名，按序尝试；**回款用应收金额、收入用不含税金额**（对齐旧系统第五版） |
| 动态时间 | `cleaning_config.json` 中 `_mode: dynamic` 自动取上月/上季度/同期 |
| 5列 Hero | 左右 收入/回款 大金额+同比+还差，双环表示达成度，中间总指标 |
| 同比同期 | 年度/月度/季度同比均对比 2024 同期（4-6月窗口，不对比全年） |
| 客户统称 | 渲染层 `data_loader.CustomerUnifier` 把子公司归并母公司，看板只展示母公司维度 |
| 全局.0f | 金额统一按万元取整无小数点；零 emoji（全部用 SVG 图标） |
| 4层销售匹配 | 广东→深圳→其他规则→默认规则(统称继承)→待确认 |

## 技术栈

Python 3.12 (Conda `visual-dashboard-system`) / pandas / openpyxl / xlrd / jinja2 / Chart.js(CDN) / pytest

## 数据安全

`data/raw/` `data/mappings/` `data/sheets/` `output/` `logs/` 已通过 `.gitignore` 排除，不上传 GitHub。
