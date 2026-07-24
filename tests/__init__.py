"""
Visual Dashboard System — 端到端测试套件

运行:
    python -m pytest tests/ -v           # 全部测试
    python -m pytest tests/test_config.py -v   # 单个文件
    python -m pytest tests/ -k "splitter"       # 按关键字

测试覆盖:
    - test_config.py:       配置与映射文件加载
    - test_column_resolver.py:  列名冗余匹配
    - test_customer_matcher.py: 客户白名单匹配
    - test_mapping_loader.py:   部门映射/客户名单加载
    - test_splitter.py:     销售拆分逻辑 + 总额校验
    - test_main.py:         顶层调度器参数解析与预检
    - test_e2e.py:          端到端流水线（需真实数据）

测试不依赖真实业务数据：使用合成 DataFrame 验证逻辑正确性。
"""
