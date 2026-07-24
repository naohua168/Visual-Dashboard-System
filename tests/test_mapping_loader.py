"""测试部门映射与客户名单加载"""
from engine.core.config import load_config
from engine.core.mapping_loader import (
    DepartmentMapper,
    load_department_mapper,
    load_customer_list,
)


def test_load_department_mapper():
    config = load_config()
    mapper = load_department_mapper(config)
    assert isinstance(mapper, DepartmentMapper)
    # 收入版映射 4 条
    assert len(mapper.income_map) == 4
    # 回款版映射应 > 10 条
    assert len(mapper.payment_map) > 10


def test_income_dept_mapping():
    config = load_config()
    mapper = load_department_mapper(config)
    assert mapper.map_income_dept("检测工程事业部") == "检测"
    assert mapper.map_income_dept("信息智能事业部") == "信息"
    assert mapper.map_income_dept("能源动力事业部") == "能源"
    assert mapper.map_income_dept("海外事业部") == "海外"


def test_payment_dept_mapping():
    config = load_config()
    mapper = load_department_mapper(config)
    # 回款版：风洞中心 -> 检测
    assert mapper.map_payment_dept("风洞中心") == "检测"


def test_payment_dept_unknown():
    config = load_config()
    mapper = load_department_mapper(config)
    assert mapper.map_payment_dept("不存在的部门") is None
    assert mapper.map_payment_dept(None) is None


def test_is_excluded():
    config = load_config()
    mapper = load_department_mapper(config)
    # excluded_internal_companies 非空
    assert isinstance(mapper.excluded_companies, list)


def test_load_customer_list():
    config = load_config()
    customers = load_customer_list(config)
    assert len(customers) > 100  # 实际 471 个
    assert "比亚迪汽车工业有限公司" in customers
