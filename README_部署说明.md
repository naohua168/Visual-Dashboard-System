# Visual Dashboard System — 部署说明

## 目录结构

```
Visual Dashboard_system/
├── run_all.bat                          ← 双击一键运行（入口）
├── main.py                              ← 命令行调度器
│
├── data/
│   ├── raw/                             ← 【用户维护】原始Excel数据
│   │   ├── 财务端数据/                 ← 财务端收入.xlsx、回款.xlsx
│   │   ├── 运营端数据/                 ← 运营端收入.xls、回款.xls
│   │   ├── 年收入回款数据/             ← 2024年收入.xlsx、2024年回款.xlsx
│   │   └── 客户名单/                   ← 客户名单.xlsx
│   ├── sheets/
│   │   ├── 手动维护/                   ← 【用户维护】指标数据
│   │   │   ├── 总指标/总指标.xlsx
│   │   │   ├── 月度收入指标/月度收入指标.xlsx
│   │   │   └── 月度回款指标/月度回款指标.xlsx
│   │   └── 系统数据清理/               ← 【系统自动生成】运行后自动填充
│   │       ├── 当年累计收入/           ← 清洗后的收入数据
│   │       ├── 当年累计回款/           ← 清洗后的回款数据
│   │       ├── 销售收入/               ← 拆分后的销售收入
│   │       └── ...                     ← 其余数据表
│   └── mappings/                        ← 映射配置文件（无需维护）
│
├── output/                              ← 【系统输出】结果产物
│   ├── 看板_YYYYMMDD.html              ← 可视化看板（双击打开）
│   └── data_YYYYMMDD.xlsx              ← 汇总Excel数据表
│
├── engine/                              ← 清洗引擎（无需维护）
├── processors/                          ← 渲染引擎（无需维护）
├── config/                              ← 系统配置（无需维护）
└── tests/                               ← 测试套件
```

## 使用流程

### 第1步：更新原始数据

把最新的原始Excel文件放到对应目录：

| 文件 | 放到 |
|------|------|
| 财务端收入.xlsx | `data/raw/财务端数据/收入.xlsx` |
| 财务端回款.xlsx | `data/raw/财务端数据/回款.xlsx` |
| 财务端广东分.xlsx | `data/raw/财务端数据/广东公司.xlsx` |
| 财务端湖南分.xlsx | `data/raw/财务端数据/湖南公司.xlsx` |
| 运营端收入.xls | `data/raw/运营端数据/收入.xls` |
| 运营端回款.xls | `data/raw/运营端数据/回款.xls` |

### 第2步：更新手动维护指标（如需）

如果需要修改年度目标、月度指标，打开对应Excel修改：

| 文件 | 说明 |
|------|------|
| `data/sheets/手动维护/总指标/总指标.xlsx` | 各客户的年度目标（万元） |
| `data/sheets/手动维护/月度收入指标/月度收入指标.xlsx` | 月度收入指标 |
| `data/sheets/手动维护/月度回款指标/月度回款指标.xlsx` | 月度回款指标 |

### 第3步：双击运行

双击 `run_all.bat`，系统会自动：

1. ✅ 清空旧的系统数据文件
2. ✅ 清洗年基线数据
3. ✅ 清洗收入/回款（三路输出）
4. ✅ 拆分销售归属
5. ✅ 生成HTML看板 + 汇总Excel

### 第4步：查看结果

运行结束后，`output/` 文件夹会自动打开：

- `看板_YYYYMMDD.html` — 双击用浏览器打开，6页可视化看板
- `data_YYYYMMDD.xlsx` — 汇总Excel数据表

## 环境要求

| 项目 | 说明 |
|------|------|
| 操作系统 | Windows 10/11 |
| Python | 3.12.x（Conda环境：visual-dashboard-system） |
| 磁盘空间 | 至少 500 MB |
| 依赖 | pandas、openpyxl、xlrd、jinja2 |

## 常见问题

**Q: 双击 run_all.bat 闪退？**
A: 用鼠标右键 →「以管理员身份运行」，或在命令行中运行。

**Q: 运行时报错「Python 找不到」？**
A: 打开 `run_all.bat`，把第7行的 Python 路径改成你电脑上的实际路径。

**Q: 原始数据文件名变了怎么办？**
A: 覆盖同名文件即可，系统读的是 `config/cleaning_config.json` 中配置的文件名。

**Q: 能不能只跑部分流程？**
A: 可以，用命令行单独执行某一步：
```
python -m engine.yearly_baseline.run        # 仅年基线
python -m engine.income_payment.run         # 仅收入/回款清洗
python -m engine.sales.run                  # 仅销售拆分
python -m processors.run                    # 仅渲染看板
```
