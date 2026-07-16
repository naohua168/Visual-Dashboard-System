# Visual Dashboard System

> 销售数据可视化看板生成系统 —— 从原始 Excel 数据到可视化看板的自动化处理流水线

## 项目简介

本项目是一套面向销售运营场景的数据可视化看板生成系统。系统从财务端与运营端的原始 Excel 数据出发，经过数据清洗、字段映射、规则匹配、聚合计算等处理流程，最终生成可视化的 HTML 看板页面。

## 目录结构

```
Visual Dashboard_system/
├── config/                # 配置与模板
│   └── templates/         # HTML 渲染模板
├── data/                  # 数据目录
│   ├── mappings/          # 业务规则映射（客户/部门/事业部对应关系）
│   ├── raw/               # 原始数据输入（财务端 + 运营端 Excel）
│   └── sheets/            # 系统处理后的数据表（运行时生成）
├── docs/                  # 设计文档
│   ├── 数据文件方案.md
│   ├── 数据清理逻辑设计.md
│   └── 原始数据字段详情.md
├── engine/                # 渲染引擎
├── processors/            # 数据处理器
└── scripts/               # 辅助脚本
    └── health_check.py    # 数据健康度检查
```

## 数据流

```
财务端 Excel ─┐
              ├─→ 数据清洗 ─→ 字段映射 ─→ 规则匹配 ─→ 聚合计算 ─→ 渲染看板
运营端 Excel ─┘                  (mappings/)                (templates/)
```

## 数据说明

- `data/raw/`：原始 Excel 输入数据，**含真实业务信息，已通过 `.gitignore` 排除**，不会上传至仓库。
- `data/mappings/`：客户名单、客户统称、销售对应规则等业务规则配置，**同样已排除**。
- 本仓库仅包含代码框架、文档与辅助脚本。使用前请将本地数据放入对应目录。

## 健康检查

```bash
python scripts/health_check.py
```

检查 `data/mappings/` 下各映射文件的完整性与格式正确性。

## 技术栈

- **语言**：Python
- **数据源**：Excel（.xlsx / .xls）
- **配置格式**：JSON
- **输出**：HTML 看板

## 许可证

本项目仅用于内部业务，未公开授权。
