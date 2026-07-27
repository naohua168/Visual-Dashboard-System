# Visual Dashboard System

> 销售数据可视化看板生成系统 —— 从原始 Excel 数据到可视化看板的自动化处理流水线

## 项目简介

本项目是一套面向销售运营场景的数据可视化看板生成系统。系统从财务端与运营端的原始 Excel 数据出发，经过年基线清洗、收入/回款清洗、销售拆分等处理流程，最终生成 6 页交互式 HTML 可视化看板。

核心特点：**全部配置驱动，清洗参数与代码分离，列名冗余匹配防错位。**

## 流水线总览

```
原始数据（8+ 文件）                配置与映射
├── 财务端收入.xlsx                ├── cleaning_config.json
├── 财务端回款.xlsx                ├── 部门事业部映射.json
├── 广东公司.xlsx                  ├── 客户名单.json (471 个)
├── 湖南公司.xlsx                  ├── 客户统称名单.json (13 组母公司 + 307 子公司)
├── 运营端收入.xls                 └── 客户销售对应规则.json (480 条)
├── 运营端回款.xls
├── 2024年收入.xlsx  ← 年基线
└── 2024年回款.xlsx   ← 年基线
         │
         ▼
  Phase 0: 年基线清洗（engine/yearly_baseline/）
  2024年收入/回款 → 年收入/年回款（6 列标准表，用于同比页面）
         │
         ▼
  Phase 1+2: 收入/回款清洗（engine/income_payment/）
  三路输出：月 / 季度累计 / 当年累计
         │
         ├── 月收入/月回款        ← 仅财务端（当月）
         ├── 季度累计收入/回款    ← 财务端 + 运营端截止当季末
         └── 当年累计收入/回款    ← 财务端 + 运营端全部
         │
         ▼
  Phase 3: 销售拆分（engine/sales/）
  4 层匹配：广东(7) → 深圳(2) → 其他(140) → 默认(331) → 待确认
  总额校验：拆分前后完全一致
         │
         ▼
  Phase 4: 渲染 HTML 看板（processors/）
  6 页分页：数据总览 / 年度达成 / 月度达成 / 销售达成 / 年度同比 / 季度分析
```

## 目录结构

```
Visual Dashboard_system/
├── config/                         # 系统配置
│   └── cleaning_config.json        # ★ 核心配置（数据源/列映射/时间范围/客户匹配/渲染输出）
├── data/
│   ├── raw/                        # 原始数据（只读，含敏感信息已 gitignore）
│   ├── mappings/                   # 业务规则映射（4个JSON，已 gitignore）
│   └── sheets/                     # 输出数据表（13 个文件，已 gitignore）
│       ├── 月收入/
│       ├── 月回款/
│       ├── 当年累计收入/
│       ├── 当年累计回款/
│       ├── 季度累计收入/
│       ├── 季度累计回款/
│       ├── 销售收入/               # （7列，含销售列）
│       ├── 销售回款/
│       ├── 年收入/                 # ★ 2024 年基线数据
│       ├── 年回款/
│       ├── 总指标/                 # 手工维护
│       ├── 月度收入指标/           # 手工维护
│       └── 月度回款指标/           # 手工维护
├── engine/                         # ★ 数据清洗引擎
│   ├── core/                       #   公共基础模块
│   │   ├── config.py               #   配置加载 + 动态时间模板
│   │   ├── column_resolver.py      #   列名冗余匹配（多候选降级）
│   │   ├── customer_matcher.py     #   客户白名单匹配
│   │   ├── mapping_loader.py       #   部门映射 + 排除名单
│   │   └── utils.py                #   日期筛选 + 列标准化
│   ├── income_payment/             #   收入/回款清洗（三路输出）
│   │   ├── financial.py            #   财务端清洗（主表+广东+湖南）
│   │   ├── operations.py           #   运营端清洗
│   │   └── run.py                  #   主入口
│   ├── sales/                      #   销售拆分
│   │   ├── splitter.py             #   4层匹配 + 总额校验
│   │   └── run.py                  #   主入口
│   └── yearly_baseline/            #   年基线清洗（2024年收入/回款）
│       ├── cleaner.py              #   清洗逻辑
│       └── run.py                  #   主入口
├── docs/                           # 设计文档
│   ├── 数据文件方案.md
│   ├── 数据清理逻辑设计.md
│   └── 原始数据字段详情.md
├── processors/                     # ★ 渲染层（HTML 看板生成）
│   ├── data_loader.py              #   统一加载 13 张表 + 客户统称映射
│   ├── base.py                     #   渲染器基类 + Excel 仪表盘主题 CSS/JS
│   ├── utils.py                    #   金额/百分比格式化
│   ├── page_overview.py            #   P1: 数据总览（6 KPI + 事业部条 + TOP5 + 趋势）
│   ├── page_annual.py              #   P2: 年度达成（目标块 + 进度条 + 客户矩阵）
│   ├── page_monthly.py             #   P3: 月度达成（当月 KPI + 客户月度明细）
│   ├── page_sales.py               #   P4: 销售达成（3 卡片 + KPI + 待确认分析）
│   ├── page_yoy.py                 #   P5: 年度同比（事业部同比 + 重要客户同比）
│   ├── page_quarterly.py           #   P6: 季度分析（季度趋势 + 事业部对比）
│   └── run.py                      #   渲染主入口（6 页合并 + Chart.js）
├── scripts/                        # 辅助脚本
├── tests/                          # ★ 测试套件（pytest）
│   ├── test_config.py              #   配置与映射加载（9 用例）
│   ├── test_column_resolver.py     #   列名冗余匹配（8 用例）
│   ├── test_customer_matcher.py    #   客户白名单匹配（7 用例）
│   ├── test_mapping_loader.py      #   部门/客户名单加载（6 用例）
│   ├── test_splitter.py            #   销售拆分 + 总额校验（10 用例）
│   ├── test_utils.py               #   通用工具函数（7 用例）
│   ├── test_data_loader.py         #   渲染数据加载（6 用例）
│   ├── test_render_utils.py        #   渲染辅助工具（16 用例）
│   ├── test_render.py              #   端到端渲染生成 HTML（2 用例）
│   ├── test_main.py                #   顶层调度器（7 用例）
│   ├── test_e2e.py                 #   端到端流水线（5 用例，依赖真实数据）
│   ├── test_yearly_baseline.py     #   年基线清洗（9 用例）
│   └── test_page_renderers.py      #   渲染页面测试（6×页面渲染，依赖真实数据）
├── main.py                         # ★ 顶层调度器（argparse + subprocess + 日志）
├── pytest.ini                      # pytest 配置
└── requirements.txt                # Python 依赖清单
```

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# ── 顶层调度器（推荐）──
python main.py                              # 全流程：年基线→清洗→拆分→渲染
python main.py --type=收入                   # 只处理收入链路
python main.py --step=yearly                 # 只年基线
python main.py --step=clean                  # 只清洗（Phase 1+2）
python main.py --step=split                  # 只销售拆分（Phase 3）
python main.py --step=render                 # 只渲染（Phase 4，生成 HTML 看板）
python main.py --from=clean --to=split       # 区间执行
python main.py --dry-run                     # 预检模式（不写文件，仅检查依赖）
python main.py --list                        # 列出所有可用步骤

# ── 直接调用清洗引擎 ──
python -m engine.yearly_baseline.run         # 年基线清洗 → data/sheets/年收入/年回款
python -m engine.income_payment.run          # 收入+回款清洗 → 三路输出
python -m engine.income_payment.run --type=收入
python -m engine.sales.run                   # 销售拆分 → data/sheets/销售收入/销售回款

# ── 直接调用渲染引擎 ──
python -m processors.run                     # 生成 output/看板_YYYYMMDD.html
python -m processors.run --output=自定义.html

# ── 运行测试 ──
python -m pytest tests/ -v                   # 全部测试（90+ 用例）
python -m pytest tests/test_render.py -v      # 渲染测试
python -m pytest tests/ -k "yearly"           # 按关键字
```

## 标准表结构

### 收入/回款（6列）

| 列名 | 类型 | 说明 |
|------|------|------|
| 事业部 | str | 检测/信息/能源/海外 |
| 金额 | float | 原始元值（清洗阶段不÷10000） |
| 客户 | str | 白名单匹配后的标准客户名 |
| 日期 | datetime | 财务端=真实日期，运营端=固定日期 |
| 是否为广东公司 | str | "是" 或 空 |
| 是否为深圳公司 | str | "是" 或 空 |

### 销售收入/销售回款（7列）

6列 + `销售` 列（销售人员姓名，一行可拆为多行）。

## 看板页面导航

| # | 页面 | 导航名 | 内容 |
|---|------|--------|------|
| P1 | 数据总览 | `overview` | 6 KPI + 事业部分布 + 销售 TOP5 + 月度趋势 |
| P2 | 年度达成 | `annual` | 总目标块 + 收入/回款进度条 + 4 事业部子条 + 客户矩阵 |
| P3 | 月度达成 | `monthly` | 当月 KPI（收入+回款）+ 客户月度明细表 |
| P4 | 销售达成 | `sales` | 3 卡片 + KPI：销售排名 / 事业部矩阵 / 销售人员×各公司指标达成度 |
| P5 | 年度同比 | `yoy` | 去年→今年 KPI + 事业部同比表 + 重要客户同比表 |
| P6 | 季度分析 | `quarterly` | 季度累计趋势 + 事业部季度对比 + 季度 Top 客户 |

UI 风格：Excel 仪表盘蓝白主题，条件格式数据条，纯色无渐变。

## 核心设计

| 设计 | 说明 |
|------|------|
| **列名冗余匹配** | 每个字段配置多个备选列名，按序尝试，全失败报错。源文件列名微调也能自动适配 |
| **配置驱动** | 数据源路径、列映射、金额除数、时间范围全部在 `cleaning_config.json` 中配置 |
| **映射外置** | 部门映射、客户白名单、销售规则全部在 `data/mappings/` 的 JSON 文件中 |
| **金额不÷10000** | 清洗阶段保留原始元值，单位转换放到计算阶段，避免浮点精度损失 |
| **4 层销售匹配** | 广东→深圳→其他→默认→待确认，默认规则 331 条覆盖统称名单兜底 |
| **总额校验** | 销售拆分后总额与拆分前完全一致（原始元值不四舍五入） |
| **三路输出** | 清洗阶段同时输出月（财务端仅当月）、季度累计、当年累计三份数据 |
| **年基线同比** | P6 同比页面依赖 2024 年基线数据，用于当年 vs 去年对比 |

## 动态时间配置

配置中时间范围默认使用 `{"_mode": "dynamic"}` 模式：
- **7 月运行时**：自动取上月（6 月）财务端数据，运营端固定日期 = 2026-06-01
- **无需手动改配置**，每月自动适配
- 支持 `{"_mode": "static"}` 固定月份模式

## 数据安全

- `data/raw/`：原始 Excel 输入数据，**含真实业务信息，已通过 `.gitignore` 排除**
- `data/mappings/`：业务规则配置，**同样已排除**
- `data/sheets/`：输出的标准数据表，**已排除**
- 本仓库仅包含代码、配置模板与文档。使用前请将本地数据放入对应目录

## 技术栈

- **语言**：Python 3.8+
- **数据处理**：pandas, openpyxl, xlrd
- **配置格式**：JSON
- **前端**：Chart.js 4.4（CDN 加载）
- **依赖**：见 `requirements.txt`

## 许可证

本项目仅用于内部业务，未公开授权。
