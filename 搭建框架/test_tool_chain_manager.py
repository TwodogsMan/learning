"""测试 ToolChain 和 ToolChainManager"""
from 搭建框架.tool_chain_manager import ToolChain, ToolChainManager, create_research_chain
from 搭建框架.my_calculator_tool import create_calculator_registry


def test_single_step_chain():
    """测试单步工具链"""
    print("=== 测试1：单步工具链 ===")
    registry = create_calculator_registry()

    chain = ToolChain(name="简单计算", description="只有一个计算步骤")
    chain.add_step(
        tool_name="my_calculator",
        input_template="{input}",
        output_key="result"
    )

    result = chain.execute(registry, initial_input="sqrt(16) + 2 * 3")
    print(f"结果: {result}")
    assert "10" in result, f"期望结果包含 10，实际: {result}"
    print("✅ 通过\n")


def test_multi_step_chain():
    """测试多步工具链（变量在步骤间传递）"""
    print("=== 测试2：多步工具链 ===")
    registry = create_calculator_registry()

    chain = ToolChain(name="分步计算", description="分两步计算")
    chain.add_step(
        tool_name="my_calculator",
        input_template="{input}",
        output_key="step1"
    )
    chain.add_step(
        tool_name="my_calculator",
        input_template="{step1} * 2",  # 引用第一步的结果
        output_key="final"
    )

    result = chain.execute(registry, initial_input="3 + 4")
    print(f"第一步: 3+4=7, 第二步: 7*2=14 → 最终结果: {result}")
    assert "14" in result, f"期望结果包含 14，实际: {result}"
    print("✅ 通过\n")


def test_chain_manager():
    """测试 ToolChainManager 注册和执行"""
    print("=== 测试3：工具链管理器 ===")
    registry = create_calculator_registry()
    manager = ToolChainManager(registry)

    chain1 = ToolChain(name="加10", description="输入+10")
    chain1.add_step("my_calculator", "{input} + 10", "r")

    chain2 = ToolChain(name="乘2", description="输入*2")
    chain2.add_step("my_calculator", "{input} * 2", "r")

    manager.register_chain(chain1)
    manager.register_chain(chain2)

    # 列出所有链
    chains = manager.list_chains()
    print(f"已注册的工具链: {chains}")
    assert "加10" in chains and "乘2" in chains

    # 执行指定链
    r1 = manager.execute_chain("加10", "5")
    print(f"加10(5) = {r1}")
    assert "15" in r1

    r2 = manager.execute_chain("乘2", "5")
    print(f"乘2(5) = {r2}")
    assert "10" in r2

    print("✅ 通过\n")


def test_unknown_chain():
    """测试执行不存在的工具链"""
    print("=== 测试4：不存在的工具链 ===")
    registry = create_calculator_registry()
    manager = ToolChainManager(registry)

    result = manager.execute_chain("不存在的链", "test")
    assert "不存在" in result
    print(f"错误信息: {result}")
    print("✅ 通过\n")


def test_missing_variable():
    """测试模板变量缺失时的错误处理"""
    print("=== 测试5：模板变量缺失 ===")
    registry = create_calculator_registry()

    chain = ToolChain(name="缺少变量", description="引用了不存在的变量")
    chain.add_step(
        tool_name="my_calculator",
        input_template="{不存在的变量} + 1",
        output_key="r"
    )

    result = chain.execute(registry, initial_input="test")
    assert "未找到" in result
    print(f"错误信息: {result}")
    print("✅ 通过\n")


def test_context_override():
    """测试传入 context 覆盖/补充变量"""
    print("=== 测试6：外部 context 传参 ===")
    registry = create_calculator_registry()

    chain = ToolChain(name="外部变量", description="使用外部传入的变量")
    chain.add_step(
        tool_name="my_calculator",
        input_template="{x} + {y}",
        output_key="r"
    )

    result = chain.execute(registry, initial_input="unused", context={"x": "10", "y": "20"})
    print(f"x=10, y=20 → 结果: {result}")
    assert "30" in result
    print("✅ 通过\n")


def test_math_functions_chain():
    """测试复杂数学运算链"""
    print("=== 测试7：复杂数学链 ===")
    registry = create_calculator_registry()

    chain = ToolChain(name="三角函数链", description="sin + cos 组合")
    chain.add_step("my_calculator", "sin(pi/6)", "sin_val")        # 0.5
    chain.add_step("my_calculator", "cos(pi/3)", "cos_val")        # 0.5
    chain.add_step("my_calculator", "{sin_val} + {cos_val}", "sum")  # 1.0

    result = chain.execute(registry, initial_input="")
    print(f"sin(π/6) + cos(π/3) = {result}")
    assert "1" in result, f"期望 1，实际: {result}"
    print("✅ 通过\n")


if __name__ == "__main__":
    test_single_step_chain()
    test_multi_step_chain()
    test_chain_manager()
    test_unknown_chain()
    test_missing_variable()
    test_context_override()
    test_math_functions_chain()
    print("🎉 全部测试通过！")
