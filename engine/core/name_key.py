# Author: naohua168 <bai_bai168@qq.com>
"""公司名 / 客户名「匹配键」— 消除全角半角、空白、大小写差异（显示名一律不变）

背景（2026-09-29 用户口径）：
    同一家公司在配置与源数据里可能写成
        `法雷奥汽车内部控制（深圳）有限公司`（全角括号）
        `法雷奥汽车内部控制(深圳)有限公司`（半角括号）
    原先各处都是「strip 后精确查表」，于是出现：
      · 销售拆分匹配不上 → 该行销售 = 待确认（金额不落到人）
      · 客户白名单匹配不上 → 该行被直接丢弃（比待确认更隐蔽）
      · 法人主体（广东汽车检测中心 / 南方韶关 / 比亚迪分流）比较失败 → 口径错配
    现在全链路统一用 `match_key()` 建索引与查询，显示名保持原样。

设计原则：
    · 只做「符号层」等价：NFKC（全角→半角：（）→() 、全角字母数字→ASCII、全角空格→空格）、
      去掉所有空白与零宽字符、英文大小写统一
    · **不做「内容层」删减**（不删「（深圳）」「有限公司」）—— 那会把不同法人合并，风险更大
    · 撞键（同一 key 多个写法）不报错：匹配照常，由 `KeyIndex.conflicts` 暴露给日志，
      人工去配置里合并；显示名以「归属表里先出现的写法」为准

用法：
    idx = KeyIndex()
    idx.add("法雷奥汽车内部控制(深圳)有限公司")
    idx.key("法雷奥汽车内部控制（深圳）有限公司")   # 同一个键 → 命中
    idx.conflicts                                  # {'…': ['半角写法', '全角写法']}
"""
from __future__ import annotations

import re
import unicodedata

# 零宽字符 / BOM：源表里肉眼看不见，却会让字符串比较失败
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)
_WS = re.compile(r"\s+")

# ── 法人主体常量（比较一律走 match_key，不再写死全角/半角）──
LEGAL_GD = "广东汽车检测中心有限公司"
LEGAL_SG = "南方（韶关）智能网联新能源汽车试验检测中心有限公司"
# 广东自有客户组里「深圳主体」判定用的子串（运营端 infer_company_type 同口径）
SZ_MARKER = "深圳"


def match_key(name) -> str:
    """公司名 / 客户名 → 匹配键（只用于比较与建索引，不用于展示）"""
    if name is None:
        return ""
    if isinstance(name, float) and name != name:  # NaN
        return ""
    s = unicodedata.normalize("NFKC", str(name))
    s = s.translate(_INVISIBLE)
    s = _WS.sub("", s)
    return s.upper()


def same_name(a, b) -> bool:
    """两个名字是否为同一个（只忽略符号/空白/大小写差异）"""
    ka = match_key(a)
    return bool(ka) and ka == match_key(b)


def is_gd_legal(name) -> bool:
    """法人主体（或核算单位/所属单位）是否 = 广东汽车检测中心有限公司"""
    return same_name(name, LEGAL_GD)


def is_sg_legal(name) -> bool:
    """法人主体是否 = 南方（韶关）智能网联新能源汽车试验检测中心有限公司"""
    return same_name(name, LEGAL_SG)


def is_sz_legal(name) -> bool:
    """法人主体是否为深圳主体（运营端口径：名字里含「深圳」）"""
    return SZ_MARKER in match_key(name)


class KeyIndex:
    """归一化键索引 —— key → 首个原写法（显示名）

    撞键（同一 key 有多个写法）不报错：匹配照常取首个写法，
    其余写法记在 `conflicts`，由调用方打印提示，人工去合并配置。
    """

    def __init__(self) -> None:
        self._canonical: dict[str, str] = {}
        self._extra: dict[str, list[str]] = {}

    def add(self, name) -> str:
        """登记一个名字，返回其匹配键（空名返回 ""，不登记）"""
        k = match_key(name)
        if not k:
            return ""
        raw = str(name).strip()
        if k not in self._canonical:
            self._canonical[k] = raw
        elif raw != self._canonical[k] and raw not in self._extra.setdefault(k, []):
            self._extra[k].append(raw)
        return k

    def key(self, name) -> str:
        return match_key(name)

    def get(self, name, default=None):
        """按匹配键取「先出现的原写法」"""
        return self._canonical.get(match_key(name), default)

    def __contains__(self, name) -> bool:
        return match_key(name) in self._canonical

    @property
    def conflicts(self) -> dict[str, list[str]]:
        """仅符号/空白/大小写不同、却被当成两个名字维护的写法"""
        return {k: [self._canonical[k]] + v for k, v in self._extra.items()}

    @property
    def size(self) -> int:
        return len(self._canonical)


def key_set(names) -> set[str]:
    """一批名字 → 匹配键集合（用于排除名单、白名单这类集合判定）"""
    return {k for k in (match_key(n) for n in names) if k}


# ══════════════════════════════════════════════════════════════
# 「父组名自带销售」的分隔符容错（2026-09-29）
#   归属表把按销售拆行的母公司写成 `母公司·销售`（如 科技公司·王海龙）；
#   指标表 / 展示规则里手填时，中间分隔符可能打成 - / 空格 / 斜杠…（甚至漏打），
#   这里统一归一到归属表里的规范写法。名字由调用方注入（本模块不读配置文件）。
# ══════════════════════════════════════════════════════════════
# 允许的分隔符（与 page_data_utils 的拆分键容错同一套字符）
SPLIT_SEP = (
    r"\s_\u00b7\u2022\u2027\u30fb\u2010-\u2015\u2212\-\uFF0D/\uFF0F\\|\uFF5C"
    r",，、;；:：.。~\uFF5E"
)

_DOTTED_RE_CACHE: dict[tuple[str, ...], tuple[tuple[str, re.Pattern], ...]] = {}


def dotted_parent_patterns(names) -> tuple[tuple[str, re.Pattern], ...]:
    """把「父组名自带销售」的名字列表 → ((规范名, 匹配器), …)（按名字集合缓存）

    匹配器 = 规范名的各段之间允许任意分隔符（含 0 个），如
    `科技公司·王海龙` → `^科技公司[分隔符]*王海龙$`。
    """
    keys = tuple(sorted({str(n).strip() for n in names if str(n).strip()},
                        key=len, reverse=True))
    if keys in _DOTTED_RE_CACHE:
        return _DOTTED_RE_CACHE[keys]
    pats: list[tuple[str, re.Pattern]] = []
    for name in keys:
        segs = [re.escape(x) for x in name.split("·") if x]
        if len(segs) < 2:
            continue
        pats.append((name, re.compile(rf"^{f'[{SPLIT_SEP}]*'.join(segs)}$")))
    _DOTTED_RE_CACHE[keys] = tuple(pats)
    return _DOTTED_RE_CACHE[keys]


def dotted_parent_names(parent_names) -> tuple[str, ...]:
    """从母公司名集合里挑出「父组名自带销售」的那些（含 `·`）"""
    return tuple(p for p in parent_names if "·" in str(p))


def normalize_known_parent(c, patterns) -> str | None:
    """客户名等于「父组名自带销售」的任意分隔符写法 → 返回规范名，否则 None

    patterns: `dotted_parent_patterns(...)` 的结果（调用方负责传入，便于缓存/测试）
    """
    s = str(c).strip()
    if not s or not patterns:
        return None
    for canonical, pat in patterns:
        if pat.match(s):
            return canonical
    return None


class KeyedLookup:
    """按匹配键查表、但**保留原写法作为键**的只读映射

    用它的意义：调用方（渲染层大量 `d.get(客户名)`）一行都不用改，
    查表自动忽略全角半角/空白/大小写差异；遍历时仍拿到配置里的原写法（显示名）。

        lookup = KeyedLookup()
        lookup.add("法雷奥汽车内部控制(深圳)有限公司", {"…": 1})
        lookup.get("法雷奥汽车内部控制（深圳）有限公司")   # 命中
        list(lookup)                                      # ['法雷奥汽车内部控制(深圳)有限公司']

    `store_key` 可换成别的键函数（如「(子公司, 销售) 二元组」的归一化）。
    """

    def __init__(self, store_key=None) -> None:
        self._store_key = store_key or match_key
        self._items: dict = {}       # key → 原写法
        self._values: dict = {}      # key → 值

    def add(self, name, value) -> None:
        """登记（同一匹配键重复时**保留先出现的写法与值**，与归属表先出现的口径一致）"""
        k = self._store_key(name)
        if not k:
            return
        if k not in self._items:
            self._items[k] = name
            self._values[k] = value

    def __setitem__(self, name, value) -> None:
        """`映射[名字] = 值` —— 与普通 dict 同语义：**后写覆盖**（写法仍保留先出现的）"""
        k = self._store_key(name)
        if not k:
            return
        self._items.setdefault(k, name)
        self._values[k] = value

    def get(self, name, default=None):
        return self._values.get(self._store_key(name), default)

    def __getitem__(self, name):
        return self._values[self._store_key(name)]

    def __contains__(self, name) -> bool:
        return self._store_key(name) in self._values

    def __iter__(self):
        return iter(self._items.values())

    def keys(self):
        return list(self._items.values())

    def values(self):
        return list(self._values.values())

    def items(self):
        return [(self._items[k], v) for k, v in self._values.items()]

    def __len__(self) -> int:
        return len(self._values)


def pair_key(pair) -> tuple[str, str]:
    """(子公司, 销售) 二元组的匹配键（用于 sub_sales_to_parent 这类复合键索引）"""
    sub, sales = pair
    return match_key(sub), match_key(sales)


def dup_name_groups(attribution: dict) -> dict[str, list[str]]:
    """找出归属表里「同一家公司写成两遍」的条目 → {匹配键: [各写法]}

    `attribution` = 客户销售归属.json 的 `客户归属`（{母公司: {"子公司": {...}}}）。

    只算**真正会打架**的情形：
      ① 同一个父组下，同一家公司出现多种写法（如一条全角括号、一条半角括号）
      ② 某公司既当**母公司组名**（自引用父组），又在别的组里当**子公司**
         —— 两条路都能命中，取哪条决定它显示成独立行还是归入父组

    不算重复：同一子公司在**不同父组**下各配一份（多组配置，如 广东自有客户 ↔ 零部件客户、
    比亚迪汽车工业 ↔ 比亚迪电池）—— 那是按法人主体分工的规则，必须保留两份。
    """
    occ: dict[str, list[tuple[str, str, bool]]] = {}
    for parent, group in (attribution or {}).items():
        pkey = match_key(parent)
        subs = list((group or {}).get("子公司", {}))
        # 自引用父组：父组名本身就是一次"出现"（父组名与子公司名写法不一致也要报）
        if any(match_key(s) == pkey for s in subs):
            occ.setdefault(pkey, []).append((pkey, parent, True))
        for sub in subs:
            key = match_key(sub)
            if not key:
                continue
            occ.setdefault(key, []).append((pkey, sub, key == pkey))

    problems: dict[str, list[str]] = {}
    for key, items in occ.items():
        names = {s for _, s, _ in items}
        if len(names) < 2:
            continue
        parent_keys = [p for p, _, _ in items]
        if all(not self_ref for _, _, self_ref in items) and len(set(parent_keys)) == len(items):
            continue  # 多组配置：各挂不同父组
        problems[key] = sorted(names)
    return problems


def format_conflicts(conflicts: dict[str, list[str]], limit: int = 8) -> str:
    """把 conflicts 拼成一行日志文案（超过 limit 组只报条数）"""
    if not conflicts:
        return ""
    shown = [" / ".join(v) for v in list(conflicts.values())[:limit]]
    text = "；".join(shown)
    more = len(conflicts) - limit
    if more > 0:
        text += f"；…另 {more} 组"
    return text
