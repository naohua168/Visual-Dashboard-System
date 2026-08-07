"""展示规则加载器 — 读取 config/前端渲染/展示规则.json + 客户销售归属.json

提供统一的客户筛选/排序/行数控制 API，所有 page_data 函数调用此模块。

核心能力：
- 加载展示规则 (JSON)
- 加载客户归属 (JSON)
- 客户筛选器 (白名单 + 排序 + 截断)
- 母公司组名 → 子客户列表 展开（"广汽系" → 7 个子公司名）
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_RULES: dict | None = None
_OWNERSHIP: dict | None = None


# ═══════════════════════════════════════════════════════════
# 基础加载函数
# ═══════════════════════════════════════════════════════════
def _load_rules(base_dir: Path) -> dict:
    """加载展示规则（缓存）"""
    global _RULES
    if _RULES is None:
        path = base_dir / "config" / "前端渲染" / "展示规则.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _RULES = json.load(f)
        else:
            _RULES = {}
    return _RULES


def _load_ownership(base_dir: Path) -> dict:
    """加载客户销售归属（缓存）"""
    global _OWNERSHIP
    if _OWNERSHIP is None:
        path = base_dir / "config" / "清洗配置" / "客户销售归属.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _OWNERSHIP = json.load(f)
        else:
            _OWNERSHIP = {}
    return _OWNERSHIP


def get_parent_names(base_dir: Path) -> list[str]:
    """获取所有母公司名称（从客户销售归属.json）"""
    ownership = _load_ownership(base_dir)
    return list(ownership.get("客户归属", {}).keys())


def get_page_config(base_dir: Path, page_key: str) -> dict:
    """获取指定页面的展示规则配置"""
    rules = _load_rules(base_dir)
    return rules.get(page_key, {})


def get_value(base_dir: Path, page_key: str, key: str, default=None):
    """从展示规则中读取顶层标量值（如 销售TopN、最大行数）

    支持嵌套读取（用 "." 分隔）：
        get_value(base, "数据总览", "销售TopN")         -> 10
        get_value(base, "年度达成", "客户矩阵.最大行数")  -> 20
    """
    cfg = get_page_config(base_dir, page_key)
    parts = key.split(".")
    for p in parts:
        if isinstance(cfg, dict) and p in cfg:
            cfg = cfg[p]
        else:
            return default
    return cfg


# ═══════════════════════════════════════════════════════════
# 组名展开：母公司组名 → 子公司客户名列表
# ═══════════════════════════════════════════════════════════
def expand_to_customer_names(base_dir: Path, names: list[str]) -> set[str]:
    """将混合的【母公司组名 + 客户名】展开成所有底层子客户名集合

    逻辑：
    1. 名字若在 ownership 中作为母公司存在 → 加入其全部子公司名
    2. 否则作为叶子客户名直接加入

    Args:
        base_dir: 项目根
        names: 含母公司组名（如 "广汽系"）和/或客户名（如 "华为数字能源技术有限公司"）的列表

    Returns:
        所有底层子客户名的 set（不含母公司组名本身，除非它就是叶子）
    """
    ownership = _load_ownership(base_dir).get("客户归属", {})
    parents = set(ownership.keys())
    result: set[str] = set()
    for n in names:
        n = (n or "").strip()
        if not n:
            continue
        if n in parents:
            for sub_name in ownership[n].get("子公司", {}).keys():
                result.add(sub_name)
        else:
            # 叶子客户名：直接保留
            result.add(n)
    return result


# ═══════════════════════════════════════════════════════════
# 客户筛选引擎
# ═══════════════════════════════════════════════════════════
@dataclass
class CustomerFilter:
    """客户筛选器 — 根据配置过滤/排序/截断客户列表"""

    include: list[str] = field(default_factory=list)  # 白名单（母公司名 + 客户名混合）
    priority: list[str] = field(default_factory=list)  # 优先展示（母公司名 + 客户名混合）
    max_rows: int = 0     # 0 = 不限
    sort_by: str = "目标合计降序"  # 排序方式
    known_parents: list[str] = field(default_factory=list)  # 从归属文件加载的所有母公司

    @classmethod
    def from_config(cls, base_dir: Path, page_key: str,
                    section: str | None = None) -> "CustomerFilter":
        """从展示规则配置创建筛选器

        Args:
            base_dir: 项目根
            page_key: 页面键名，如 "年度达成"
            section: 子段名（如 "客户矩阵"），None 时整页配置当作 section
        """
        page_cfg = get_page_config(base_dir, page_key)
        cfg = page_cfg.get(section, page_cfg) if section else page_cfg
        if isinstance(cfg, dict):
            return cls(
                include=cfg.get("客户筛选", []),
                priority=cfg.get("优先展示", []),
                max_rows=cfg.get("最大行数", 0),
                sort_by=cfg.get("排序", "目标合计降序"),
                known_parents=get_parent_names(base_dir),
            )
        return cls(known_parents=get_parent_names(base_dir))

    def is_empty(self) -> bool:
        """是否未启用筛选（白名单为空）"""
        return len(self.include) == 0

    def has_priority(self) -> bool:
        """是否配置了优先展示列表"""
        return len(self.priority) > 0

    def get_priority_names(self, base_dir: Path) -> set[str]:
        """获取展开后的优先展示客户名集合（母公司名→子公司展开）"""
        return expand_to_customer_names(base_dir, self.priority)

    def apply(self, customers: list[str],
              piv: Any = None, tgt: Any = None,
              base_dir: Path | None = None) -> list[str]:
        """应用筛选+排序+截断，返回最终客户列表

        母公司组名（如 "广汽系"）会自动展开为所有子公司客户名。
        展开需要 base_dir（用于读 客户销售归属.json）。

        Args:
            customers: 原始客户列表（已排序）
            piv: pivot DataFrame（"合计" 列 = 实际金额）
            tgt: target DataFrame（"合计" 列 = 目标金额）
            base_dir: 项目根，启用组名展开时必填

        Returns:
            筛选后的客户列表
        """
        result = list(customers)

        # ① 白名单过滤（母公司名自动展开）
        if self.include:
            if base_dir is None:
                # 无 base_dir 时退化为精确匹配
                allowed = set(self.include)
            else:
                allowed = expand_to_customer_names(base_dir, self.include)
            result = [c for c in result if c in allowed]

        # ② 排序
        if self.sort_by == "实际金额降序" and piv is not None:
            result.sort(
                key=lambda c: (float(piv.loc[c, "合计"]) if c in piv.index else 0),
                reverse=True,
            )
        elif self.sort_by == "达成率降序" and piv is not None and tgt is not None:
            def _rate(c: str) -> float:
                act = float(piv.loc[c, "合计"]) if c in piv.index else 0
                tg = float(tgt.loc[c, "合计"]) if c in tgt.index else 0
                return act / tg if tg > 0 else 0
            result.sort(key=_rate, reverse=True)
        # 默认 "目标合计降序" 保持原顺序（调用方已按目标降序排好）

        # ③ 截断
        if self.max_rows > 0 and len(result) > self.max_rows:
            result = result[:self.max_rows]

        return result
