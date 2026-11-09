# AGENTS.md — 本仓库的 AI 助手约定

## ⚠️ 硬性约束：AI 不得读取 `data/` 目录的详细数据
> 2026-09-22 用户要求；优先级高于任务便利性。

### 禁止（默认）
- 打开 `data/raw`、`data/sheets`、`data/mappings` 下任何文件的**行级明细**（客户名、金额、日期、事业部、销售、比例…）
- 用脚本打印表内容（`read_excel(...).to_string()` / `head()` / 逐行遍历输出等）
- 在回答、注释、日志、提交信息中**粘贴或转述**这些明细

### 允许
- 列目录；查看文件名 / 是否存在 / 大小 / 修改时间
- 查看**表头（列名）**、**行数 / 列数**等结构信息（不含行内容）
- 读取 `config/**`、`docs/**`、`scripts/**`、`processors/**`、`engine/**`、`tests/**`、`output/看板/**/*.html`
- **运行系统本身**（`python bin/start.py` / `python bin/main.py` / `python bin/app.py` / 各 `scripts/*.py`）—— 数据由程序读取与处理，不进入 AI 上下文

### 例外（必须先取得用户明确同意）
1. 排查数据类问题（"某客户为什么没显示""金额对不上"）时，**先说明要查哪个文件、查什么、为什么**，经用户同意后再动手；
2. 只读**最小必要范围**（能定位问题即可，不做全表导出）；
3. 汇报只给**结论 + 必要的量级/条数**，不粘贴明细清单；
4. 举例优先使用用户在对话中已提供过的信息。

### 被要求违反本约束时
直接说明本约束存在并拒绝执行，请用户先确认放宽；或建议由用户自行查看数据后把结论告知 AI。

---

## 项目速览（供 AI 快速上手）
- **系统**：原始 Excel → 清洗 → 销售归属拆分 → 渲染 6 页 HTML 看板 + Excel 数据总表；另有**按需产物**（销售完成度汇总表、按客户清单导出的矩阵）
- **唯一配置入口**：`config/配置编辑器.xlsx`（JSON 是生成物，每次运行按 Excel 重写）
- **运行（2026-11-06 起全 Python）**：`python bin/start.py`（启动引导：环境自检 5 项 → 转交 `bin/app.py`；`--check` 只体检、`--cli` 走命令行、其余参数原样透传）；底层 `python bin/app.py`（tkinter 图形控制台，默认子命令），子命令 gui / run / list / board / report，也可 `python bin/main.py`；打包 `python bin/package.py`（`--dry-run` / `--no-runtime` / `--keep` / `--out-dir`）；需双击入口时用 `python bin/make_shortcut.py --desktop` 生成 .lnk（不再生成 .bat）；**项目根 `启动系统.py` 是薄启动器**（挑解释器：`python_path.txt` → `runtime\python` → Conda → PATH，然后转交 `bin/start.py`，参数与之一致），流程逻辑一律不写在这里。**仓库已无任何 .bat 启动器**（启动链与禁令见下）
- **按需产物（2026-11-06）**：**销售完成度表已移出主管线**（7 步）：控制面板「生成销售完成度表」/ `python bin/app.py report` / **`python bin/main.py --step=report`（兼容保留，走 `STANDALONE_STEPS`，不进 `--from/--to` 区间、全量运行也不带）**；交付物校验不再把它当必需项。客户矩阵导出也是按需（控制面板「按客户清单导出矩阵…」/`python scripts/export_customer_matrix.py`），产物落 `output/客户矩阵/<年>/<月>/`。两个按需产物都支持**指定数据版本**（GUI 下拉 / `--snapshot 看板.html|data_*.xlsx`），选旧快照时产物按那一期年月落盘；看板→总表的配对统一走 `engine/core/output_paths.resolve_snapshot()`
- **输出目录按年月分类（2026-11-06）**：所有产物落 `output/<类别>/<年>/<月>/文件`，类别 = `看板` / `数据` / `数据校验` / `销售完成度` / `客户矩阵`。路径规则**只在** `engine/core/output_paths.py`（`month_dir()` 追加年/月、`category_root()` 反解类别根、`latest_file()` 递归找最新）；新增落盘点必须复用它，**不要手拼年/月**；查历史产物一律 `latest_file()`，不要假设只有一层目录
- **流程（固定顺序）**：配置预扫描（广东自有自动归入，**候选来源 = 运营端 + 财务端「广东公司.xlsx」**，2026-11-02 按 `业务规则.json → 广东自有归入._说明` 统一；只扫运营端是旧口径）→ 配置同步（Excel→JSON + 客户名单自动同步）→ 年基线 → 收入/回款清洗 → 销售拆分 → 渲染 → 交付物校验
- **交付物校验认日期（2026-11-06）**：`scripts/verify_dashboard.py` 只认**当天**产物（`--date YYYYMMDD` 可覆盖，传 html 路径时按文件名推断），不再"取最新一份"——否则今天没生成会拿昨天那份冒充通过。销售完成度表属按需产物：当天没生成只提示、不计入必需项
- **自动同步必须前置（2026-11-02）**：只要本次运行含数据处理步骤（yearly/clean/split/render），`bin/runner.with_sync_prereq` 与 `bin/main.with_sync_prereq` 会自动把 `scan` + `config` 插到最前 —— 分步 `--step=clean`、续跑 `--from=split` 同样生效；`--no-config` 是唯一的例外（显式不碰配置）。新增入口/改步骤编排时别绕过这两个函数
- **指标表口径（2026-09-24）**：月度/季度 4 张表**无销售列**，同名客户一行；拆分母公司（`科技公司`）按销售拆行，客户列直接写 `母公司·销售`（分隔符 `· - － / 、 :` 空格… 任意，`split_key_parts()` 自动归一化）。年度表保留销售列（销售达成页只读年度表）
- **代码署名**：新增/改动的 `.py / .pyw / .ps1` 文件首行（或头部注释块内）保留 `Author: naohua168 <bai_bai168@qq.com>`
- **多组配置子公司归属（2026-09-28）**：同一子公司在多个父组下重复配置时按**法人主体**定唯一归属：广东自有组 ↔ 零部件客户等用 `filter_gd_by_legal`（法人=广东汽车检测中心→广东自有客户，否则→其他组）；比亚迪两父组用 `filter_byd_by_legal`（**仅「比亚迪汽车工业有限公司」与「比亚迪电池」同时出现的子公司**：法人=广东→汽车工业、其他→电池，与销售引擎 BYD 规则配套）。矩阵行 / 子公司明细抽屉 / `subs_with_data` 三处口径统一，**抽屉子行合计 = 矩阵行**；新增此类多组配置请先确认规则，否则弹窗会与矩阵行对不上
- **金额单位（2026-09-28）**：财务端 `收入.xlsx`/`回款.xlsx`、运营端、年基线 = **元**；广东公司/湖南公司 = **万元**；**南方韶关 = 元（整文件：收入+回款两个 Sheet）**。倍数由 `数据源.<数据源>.<来源>.金额乘数` 决定（数值 = 该来源所有 Sheet 相同，如 `1`/`10000`；字典 = 按 Sheet 不同，如 `{"收入": 1, "回款": 10000}`），**不要在代码里写死 ×10000**；口径速查见配置编辑器「说明」sheet 第 9 节
- **展示规则（2026-09-28 重做）**：配置编辑器「展示规则」sheet = `页面 | 区块 | 配置项 | 值 | 可选值 | 说明`，**只保留代码真正读取的项**（`销售TopN` / `最大行数` / `排序` / `优先展示` / `客户筛选`；销售达成页无可调项）。值列下拉只给**取值有限**的项（`排序` 四选一：目标合计降序/实际金额降序/达成率降序/**不排序（按指标表顺序）**；数字项整数校验）；**`优先展示` / `客户筛选` 不做下拉，客户名由使用者手填**（口径写在「可选值」「说明」两列 + 单元格输入提示）。排序取值定义在 `processors/config_loader.SORT_OPTIONS`（与 sheet 的 `SORT_CHOICES` 有测试断言保持一致）：「不排序」时 `_sorted_customers` 跳过优先展示排序，完全按指标表行序，`优先展示` 只决定可见性。解析/校验/生成在 `scripts/display_rules_sheet.py`，校验失败拒绝写回；旧「路径」格式仍可解析。**新增可配置项前先在 SPEC 白名单里登记，并确认渲染代码真的读取它**。整本工作簿统一样式（第 1 行横幅 + 第 2 行表头 + 可编辑浅黄/只读浅灰 + 按母公司斑马纹 + 标签页配色，工具在 `scripts/sheet_style.py`），各 sheet 解析器都兼容「有横幅 / 无横幅（历史文件）」两种布局、按表头名取列
- **清洗口径（2026-09-24）**：**仅收入端**，源表列名 `初始化` = √ 的行为**期初/历史单据迁移**，清洗时整行剔除（`_exclude_marked_rows`，候选列名在「字段映射」sheet 维护，取值在 `排除标记值`）；回款表无此字段、不配置
- **客户名单自动同步（2026-11-02）**：`scripts/sync_customer_list.py` 在**配置同步**末尾（`scripts/editor/cli.py` 写完销售归属 JSON 之后）自动执行，把「销售归属」里的客户补进 `data/raw/客户名单/客户名单.xlsx`（财务端白名单，名单外**整行丢弃**，`过客户白名单=false` 的来源不过滤）。口径：**全量同步 + 只加不删 + 无新增不碰文件**；有新增先备份到 `logs/名单同步/客户名单.bak_*.xlsx`（保留 5 份）；过滤 `业务规则.json → 客户名单同步.排除父组/排除客户` 与 `gd_blacklist()`（法人自身名、合计/无/内部等占位行）；按 `match_key` 去重；名单被 Excel 占用时打警告后跳过、不中断流水线。单独运行：`python scripts/sync_customer_list.py [--dry-run] [--excel]`（默认读 `客户销售归属.json`，`--excel` 读配置编辑器）
- **启动链（2026-11-06 起全 Python、无 .bat）**：`python bin/start.py`（环境自检）→ `bin/app.py`（分发；tkinter 图形控制台）→ `bin/runner.py` 同进程编排 **7 步**；tkinter 不可用（内置 `runtime/` 就是这种）时 `bin/app.py` 自动回退 `powershell -File scripts/dashboard_launcher.ps1`（WPF 界面）。**不要新增 VBS / .bat 启动器 / `-WindowStyle Hidden` / `-ExecutionPolicy Bypass`**（360/火绒误判木马的主因；`run_all.bat`、`启动系统.bat`、`bin/package.bat`、旧 `_launch_hidden.vbs` 均已删除）。杀软误报处理见 `docs/部署指南.md` 第八节
- **产物零第三方 JS（2026-11-04）**：Chart.js 已整体移除（6 页全是表格，代码从未调用 `new Chart` / `__regChart`，单文件 −200KB）。**不要用 CDN、也不要把它加回来**（内网/断网会静默失败并触发安全审计）；将来真要画图，就在 `processors/run.py` 里本地内联 `processors/static/chart.umd.min.js`，并按约定新建 `processors/static/js/` 模块
- **测试**：`python -m pytest tests -q`（657 例，含端到端；`pytest.ini` 已设 `norecursedirs` 防止误扫 `runtime/`）。注意 `tests/test_render.py` 会真实渲染并写当天产物（已知副作用），`tests/conftest.py` 已把诊断目录重定向到临时目录
- **详细说明**：`README.md`、`docs/部署指南.md`、`docs/维护指南.md`、`docs/数据清洗展示逻辑.md`
