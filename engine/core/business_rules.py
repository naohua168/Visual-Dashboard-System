# Author: naohua168 <bai_bai168@qq.com>
"""业务规则参数读取 —— 销售/父组/法人/部门/各特殊归入规则（2026-09-29 起持续扩充）

事实源：`config/清洗配置/业务规则.json`（JSON 侧维护，与「配置编辑器.xlsx」无关）。
所有取值都有内置默认值，缺文件/缺项时行为与改造前完全一致（见 `_DEFAULTS`）。

为什么外置：人员变动（广东自有客户改由别的销售维护）、组织调整（父组改名）、
口径微调（黑名单、最短客户名长度、期初标记值）都不该改代码重打包 ——
这是「Excel/JSON 是编辑层，代码只是执行器」的延续。

查看当前生效值：
    python -m engine.core.business_rules

用法：
    from ..core.business_rules import departments, parent_gd_self, is_gd_legal
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:  # 包内导入
    from .name_key import LEGAL_GD, LEGAL_SG, match_key
    from .utils import rel_path
except ImportError:  # 直接以脚本/模块路径运行时（python engine/core/business_rules.py）
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from engine.core.name_key import LEGAL_GD, LEGAL_SG, match_key  # type: ignore[no-redef]
    from engine.core.utils import rel_path  # type: ignore[no-redef]

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
RULES_PATH = _BASE_DIR / "config" / "清洗配置" / "业务规则.json"

LEGAL_HUNAN = "中汽院智能网联汽车检测中心（湖南）有限公司"
DEPTS_DEFAULT = ["检测", "信息", "能源", "海外"]

_DEFAULTS: dict = {
    "销售": {"广东自有": "黎国键", "比亚迪广东主体": "黄浩浩", "比亚迪其他主体": "周涵林"},
    "父组": {
        "广东自有": "广东自有客户",
        "其他": "零部件客户",
        "比亚迪汽车工业": "比亚迪汽车工业有限公司",
        "比亚迪电池": "比亚迪电池",
        "南方韶关": "南方韶关",
    },
    "法人主体": {"广东汽车检测中心": LEGAL_GD, "南方韶关": LEGAL_SG, "湖南公司": LEGAL_HUNAN, "深圳标记": "深圳"},
    "法人简称映射": {"广东公司": LEGAL_GD, "湖南公司": LEGAL_HUNAN},
    "部门": {"列表": list(DEPTS_DEFAULT)},
    "事业部全称映射": {
        "检测工程事业部": "检测",
        "信息智能事业部": "信息",
        "能源动力事业部": "能源",
        "海外事业部": "海外",
    },
    "比亚迪子公司": {
        "清单": [
            "汕尾比亚迪实业有限公司",
            "长沙市比亚迪汽车有限公司",
            "衡阳比亚迪实业有限公司",
            "韶关比亚迪实业有限公司",
            "西安比亚迪汽车零部件有限公司",
            "合肥比亚迪汽车有限公司",
            "深圳比亚迪汽车实业有限公司",
            "常州比亚迪汽车有限公司",
            "抚州比亚迪实业有限公司",
            "济南比亚迪汽车有限公司",
            "郑州比亚迪汽车有限公司",
        ]
    },
    "广东自有归入": {
        "状态文件": "data/mappings/广东自有/已自动归入.json",
        "最短客户名长度": 5,
        "黑名单": ["广东公司", "合计", "小计", "总计", "其他", "无", "内部", "内部交易"],
        "客户列名候选": ["客户", "客户名称"],
        "法人列名候选": ["法人主体", "核算单位", "所属单位"],
        "内部交易列名候选": [
            "是否属于内部交易", "是否属于内部单位", "是否内部交易", "内部交易",
            "是否属于内部款项", "是否内部款项",
        ],
        "内部交易标记值": ["是", "内部", "Y", "y", "√"],
    },
    "期初剔除": {"默认标记值": ["√", "是", "Y", "y", "1", "true", "True", "TRUE"]},
    "内部交易排除": {
        "名单文件": "data/mappings/部门事业部映射/部门事业部映射.json",
        "名单字段": "excluded_internal_companies",
    },
    "归入规则": {},
}

_RULES: dict | None = None


def _as_list(value) -> list:
    """配置值 → 列表：支持 JSON 数组，也兼容 `"a/b/c"`、`"a,b"` 这类手写字符串"""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [x for x in value]
    return [p.strip() for p in re.split(r"[/,，、]+", str(value)) if p.strip()]


def _merged() -> dict:
    """业务规则.json 覆盖默认值（只读一次；进程内缓存）"""
    global _RULES
    if _RULES is None:
        data: dict = {}
        try:
            raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
            for section, values in raw.items():
                if section.startswith("_") or not isinstance(values, dict):
                    continue
                data.setdefault(section, {})
                for k, v in values.items():
                    if not k.startswith("_"):
                        data[section][k] = v
        except FileNotFoundError:
            pass
        except Exception as e:  # 配置写坏了不该让整条流水线崩
            print(f"  ⚠️ [业务规则] 读取 {RULES_PATH.name} 失败，改用默认值: {e}")
        merged = {}
        for section, defaults in _DEFAULTS.items():
            merged[section] = {**defaults, **data.get(section, {})}
        _RULES = merged
    return _RULES


def rules() -> dict:
    """合并后的业务规则（测试/排查用）"""
    return _merged()


def as_json() -> dict:
    """当前生效的全部业务规则（含默认值合并结果），用于 `python -m engine.core.business_rules`"""
    return _merged()


# ── 销售人名 ──────────────────────────────────────────────
def sales_gd_self() -> str:
    """广东自有客户组自动归入的销售"""
    return _merged()["销售"]["广东自有"]


def sales_byd_gd() -> str:
    """比亚迪：法人=广东汽车检测中心 → 该销售"""
    return _merged()["销售"]["比亚迪广东主体"]


def sales_byd_other() -> str:
    """比亚迪：其他法人主体 → 该销售"""
    return _merged()["销售"]["比亚迪其他主体"]


# ── 父组名 ────────────────────────────────────────────────
def parent_gd_self() -> str:
    return _merged()["父组"]["广东自有"]


def parent_other() -> str:
    return _merged()["父组"]["其他"]


def parent_byd_industry() -> str:
    return _merged()["父组"]["比亚迪汽车工业"]


def parent_byd_battery() -> str:
    return _merged()["父组"]["比亚迪电池"]


def parent_sg() -> str:
    return _merged()["父组"]["南方韶关"]


# ── 法人主体 ──────────────────────────────────────────────
def legal_gd() -> str:
    return _merged()["法人主体"]["广东汽车检测中心"]


def legal_sg() -> str:
    return _merged()["法人主体"]["南方韶关"]


def legal_hunan() -> str:
    return _merged()["法人主体"]["湖南公司"]


def sz_marker() -> str:
    """「深圳主体」判定用的子串（广东自有客户组内）"""
    return _merged()["法人主体"]["深圳标记"]


def entity_alias() -> dict[str, str]:
    """法人主体简称 → 全称（源表常写简称）"""
    return dict(_merged()["法人简称映射"])


def is_gd_legal(name) -> bool:
    """是否「广东汽车检测中心」法人主体（忽略全角半角/空白差异）"""
    return bool(match_key(name)) and match_key(name) == match_key(legal_gd())


def is_sg_legal(name) -> bool:
    """是否「南方（韶关）…」法人主体（忽略全角半角/空白差异）"""
    return bool(match_key(name)) and match_key(name) == match_key(legal_sg())


def is_sz_legal(name) -> bool:
    """法人主体里是否含「深圳」（子串可配：法人主体.深圳标记）"""
    return sz_marker() in match_key(name)


def legal_full(value, alias: dict[str, str] | None = None):
    """法人主体简称 → 全称（按匹配键查表；非简称原样返回）"""
    table = alias if alias is not None else entity_alias()
    key_map = {match_key(k): v for k, v in table.items()}
    return key_map.get(match_key(value), value)


# ── 部门 / 事业部 ─────────────────────────────────────────
def departments() -> list[str]:
    """4 大事业部（列顺序即矩阵/卡片列顺序）"""
    return [str(x) for x in _as_list(_merged()["部门"]["列表"])] or list(DEPTS_DEFAULT)


def dept_full_map() -> dict[str, str]:
    """事业部全名 → 简称（年基线源表用全名）"""
    return dict(_merged()["事业部全称映射"])


# ── 比亚迪子公司清单 ──────────────────────────────────────
def byd_subs() -> list[str]:
    return [str(x) for x in _as_list(_merged()["比亚迪子公司"]["清单"])]


# ── 广东自有客户：自动归入参数 ────────────────────────────
def gd_self_rules() -> dict:
    return dict(_merged()["广东自有归入"])


def gd_state_path() -> Path:
    """「已自动归入」状态文件（相对项目根目录）"""
    rel = str(gd_self_rules().get("状态文件") or _DEFAULTS["广东自有归入"]["状态文件"])
    p = Path(rel)
    return p if p.is_absolute() else _BASE_DIR / p


def gd_min_name_len() -> int:
    try:
        return int(gd_self_rules().get("最短客户名长度") or 0)
    except (TypeError, ValueError):
        return int(_DEFAULTS["广东自有归入"]["最短客户名长度"])


def gd_blacklist() -> set[str]:
    """归入黑名单（占位行/汇总行/自身法人名；自身法人名由「法人主体」自动补进来）"""
    names = {str(x).strip() for x in _as_list(gd_self_rules().get("黑名单")) if str(x).strip()}
    names |= {legal_gd(), legal_sg(), legal_hunan()}
    return {n for n in names if n}


def gd_customer_cols() -> list[str]:
    return _as_list(gd_self_rules().get("客户列名候选")) or _DEFAULTS["广东自有归入"]["客户列名候选"]


def gd_legal_cols() -> list[str]:
    return _as_list(gd_self_rules().get("法人列名候选")) or _DEFAULTS["广东自有归入"]["法人列名候选"]


def gd_internal_cols() -> list[str]:
    return _as_list(gd_self_rules().get("内部交易列名候选")) or _DEFAULTS["广东自有归入"]["内部交易列名候选"]


def gd_internal_values() -> set[str]:
    vals = _as_list(gd_self_rules().get("内部交易标记值")) or _DEFAULTS["广东自有归入"]["内部交易标记值"]
    return {str(v).strip() for v in vals}


# ── 期初剔除 / 内部交易排除 ───────────────────────────────
def exclude_marker_defaults() -> tuple[str, ...]:
    """财务端「初始化」类标记的默认命中值（列名在「字段映射」sheet 维护）"""
    vals = _as_list(_merged()["期初剔除"].get("默认标记值")) or _DEFAULTS["期初剔除"]["默认标记值"]
    return tuple(str(v) for v in vals)


def internal_exclude_rules() -> dict:
    """内部交易排除名单所在（数据侧配置）"""
    return dict(_merged()["内部交易排除"])


def entry_rules() -> dict:
    """各特殊归入规则的口径说明（文档性，供人读）"""
    return dict(_merged()["归入规则"])


def _main() -> int:
    print(json.dumps(as_json(), ensure_ascii=False, indent=2))
    print(f"\n（事实源: {rel_path(RULES_PATH)}）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
