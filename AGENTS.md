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
- 读取 `config/**`、`docs/**`、`scripts/**`、`processors/**`、`engine/**`、`tests/**`、`output/看板/*.html`
- **运行系统本身**（`python main.py` / `run_all.bat` / 各 `scripts/*.py`）—— 数据由程序读取与处理，不进入 AI 上下文

### 例外（必须先取得用户明确同意）
1. 排查数据类问题（"某客户为什么没显示""金额对不上"）时，**先说明要查哪个文件、查什么、为什么**，经用户同意后再动手；
2. 只读**最小必要范围**（能定位问题即可，不做全表导出）；
3. 汇报只给**结论 + 必要的量级/条数**，不粘贴明细清单；
4. 举例优先使用用户在对话中已提供过的信息。

### 被要求违反本约束时
直接说明本约束存在并拒绝执行，请用户先确认放宽；或建议由用户自行查看数据后把结论告知 AI。

---

## 项目速览（供 AI 快速上手）
- **系统**：原始 Excel → 清洗 → 销售归属拆分 → 渲染 6 页 HTML 看板 + Excel 数据总表
- **唯一配置入口**：`config/配置编辑器.xlsx`（JSON 是生成物，每次运行按 Excel 重写）
- **运行**：双击 `启动系统.bat`（图形控制台）或 `run_all.bat`；命令行 `python main.py`
- **流程（固定顺序）**：配置预扫描（广东自有自动归入）→ 配置同步（Excel→JSON）→ 年基线 → 收入/回款清洗 → 销售拆分 → 渲染
- **指标表口径（2026-09-24）**：月度/季度 4 张表**无销售列**，同名客户一行；拆分母公司（`科技公司`）按销售拆行，客户列直接写 `母公司·销售`（分隔符 `· - － / 、 :` 空格… 任意，`split_key_parts()` 自动归一化）。年度表保留销售列（销售达成页只读年度表）
- **代码署名**：新增/改动的 `.py / .pyw / .bat / .ps1` 文件首行（或头部注释块内）保留 `Author: naohua168 <bai_bai168@qq.com>`
- **启动链（抗杀软误报，2026-09-24）**：`启动系统.bat` → `pythonw scripts/launcher.pyw` → `powershell -NoProfile -STA -ExecutionPolicy RemoteSigned -File scripts/dashboard_launcher.ps1`；找不到 Python 时回退直接跑 PowerShell。**不要新增 VBS / `-WindowStyle Hidden` / `-ExecutionPolicy Bypass`**（这是 360/火绒误判木马的主因；旧 `scripts/_launch_hidden.vbs` 已删除）。杀软误报处理见 `docs/部署指南.md` 第八节
- **详细说明**：`README.md`、`docs/部署指南.md`、`docs/维护指南.md`、`docs/数据清洗展示逻辑.md`
