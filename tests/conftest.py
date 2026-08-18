"""pytest 共享辅助 — 统一"数据就绪"检查，避免各测试文件复制路径逻辑

三个数据依赖型测试文件（test_data_loader / test_page_renderers / test_render）
共用同一份检查，防止路径漂移导致测试静默 skip。
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SYS_DIR = BASE_DIR / "data" / "sheets" / "系统数据清理"
MAN_DIR = BASE_DIR / "data" / "sheets" / "手动维护"
OUTPUT = BASE_DIR / "output"

# 清洗引擎自动生成的必需输出表（目录下有任意 xlsx 即视为就绪）
REQUIRED_SYS = [
    "当年累计收入", "当年累计回款",
    "销售收入", "销售回款",
]

# 用户手工维护的必需指标表
REQUIRED_MAN = [
    "年度收入总指标", "年度回款总指标",
    "季度收入指标", "季度回款指标",
    "月度收入指标", "月度回款指标",
]


def missing_sheets() -> list[str]:
    """返回缺失的必需数据表相对路径；空列表 = 全部就绪"""
    missing = []
    for d in REQUIRED_SYS:
        if not list((SYS_DIR / d).glob("*.xlsx")):
            missing.append(f"data/sheets/系统数据清理/{d}/")
    for d in REQUIRED_MAN:
        if not list((MAN_DIR / d).glob("*.xlsx")):
            missing.append(f"data/sheets/手动维护/{d}/")
    return missing


def has_sheets() -> bool:
    """数据是否就绪（供 pytestmark skipif 使用）"""
    return not missing_sheets()
