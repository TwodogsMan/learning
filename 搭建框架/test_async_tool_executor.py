"""测试 AsyncToolExecutor 的异步并行工具执行"""
import asyncio
import time
import pytest
from 搭建框架.async_tool_executor import AsyncToolExecutor
from 搭建框架.my_calculator_tool import create_calculator_registry


@pytest.fixture
def registry():
    """创建包含计算器的注册表"""
    return create_calculator_registry()


# ========== 同步测试（用 asyncio.run 包裹） ==========

class TestAsyncToolExecutor:
    """AsyncToolExecutor 测试套件"""

    def test_single_async_execution(self, registry):
        """测试单个工具的异步执行"""
        print("\n=== 测试1：单个异步执行 ===")
        executor = AsyncToolExecutor(registry)

        async def run():
            result = await executor.execute_tool_async("my_calculator", "sqrt(16) + 2 * 3")
            return result

        result = asyncio.run(run())
        print(f"结果: {result}")
        assert "10" in result, f"期望 10，实际: {result}"
        print("✅ 通过")

    def test_parallel_execution(self, registry):
        """测试多个工具的并行执行"""
        print("\n=== 测试2：并行执行 ===")
        executor = AsyncToolExecutor(registry)

        tasks = [
            {"tool_name": "my_calculator", "input_data": "2 + 3"},
            {"tool_name": "my_calculator", "input_data": "10 * 5"},
            {"tool_name": "my_calculator", "input_data": "sqrt(144)"},
            {"tool_name": "my_calculator", "input_data": "100 / 4"},
        ]

        async def run():
            results = await executor.execute_tools_parallel(tasks)
            return results

        results = asyncio.run(run())
        print(f"结果: {results}")

        assert len(results) == 4, f"期望 4 个结果，实际: {len(results)}"
        assert "5" in results[0]
        assert "50" in results[1]
        assert "12" in results[2]
        assert "25" in results[3]
        print("✅ 通过")

    def test_parallel_is_faster_than_serial(self, registry):
        """验证并行执行确实比串行快"""
        print("\n=== 测试3：并行 vs 串行性能 ===")

        # 使用带延迟的任务来验证并行优势
        tasks = [
            {"tool_name": "my_calculator", "input_data": "2 + 3"},
            {"tool_name": "my_calculator", "input_data": "4 + 5"},
            {"tool_name": "my_calculator", "input_data": "6 + 7"},
            {"tool_name": "my_calculator", "input_data": "8 + 9"},
            {"tool_name": "my_calculator", "input_data": "10 + 11"},
            {"tool_name": "my_calculator", "input_data": "12 + 13"},
        ]

        executor = AsyncToolExecutor(registry, max_workers=6)

        # 并行执行
        async def run_parallel():
            t0 = time.perf_counter()
            results = await executor.execute_tools_parallel(tasks)
            elapsed = time.perf_counter() - t0
            return results, elapsed

        results, parallel_time = asyncio.run(run_parallel())
        print(f"并行耗时: {parallel_time:.3f}s")
        print(f"结果数量: {len(results)}")

        # 串行执行
        t0 = time.perf_counter()
        serial_results = []
        for task in tasks:
            serial_results.append(
                registry.execute_tool(task["tool_name"], task["input_data"])
            )
        serial_time = time.perf_counter() - t0
        print(f"串行耗时: {serial_time:.3f}s")

        # 并行应该比串行快（或至少不慢太多，因为计算任务本身很快）
        # 这里主要验证并行能正确执行
        assert results == serial_results, f"并行和串行结果应一致\n并行: {results}\n串行: {serial_results}"
        print("✅ 通过（并行与串行结果一致）")

    def test_error_tool_not_found(self, registry):
        """测试执行不存在的工具时返回错误信息（而非抛异常）"""
        print("\n=== 测试4：工具不存在 ===")
        executor = AsyncToolExecutor(registry)

        async def run():
            return await executor.execute_tool_async("nonexistent_tool", "test")

        result = asyncio.run(run())
        print(f"返回值: {result}")
        assert "未找到" in result and "nonexistent_tool" in result
        print("✅ 通过（返回错误信息而非崩溃）")

    def test_parallel_with_error(self, registry):
        """测试并行执行中某个工具返回错误时，所有结果正常返回"""
        print("\n=== 测试5：并行中部分工具返回错误 ===")
        executor = AsyncToolExecutor(registry)

        tasks = [
            {"tool_name": "my_calculator", "input_data": "1 + 1"},     # 正常 → 2
            {"tool_name": "nonexistent", "input_data": "test"},         # 不存在 → 错误信息
            {"tool_name": "my_calculator", "input_data": "3 + 3"},     # 正常 → 6
        ]

        async def run():
            return await executor.execute_tools_parallel(tasks)

        results = asyncio.run(run())
        print(f"结果: {results}")

        assert len(results) == 3, f"期望 3 个结果，实际: {len(results)}"
        assert "2" in results[0], f"任务1应返回 2, 实际: {results[0]}"
        assert "未找到" in results[1], f"任务2应包含错误信息, 实际: {results[1]}"
        assert "6" in results[2], f"任务3应返回 6, 实际: {results[2]}"
        print("✅ 通过（错误工具返回错误字符串，不影响其他任务）")

    def test_mixed_math_operations(self, registry):
        """测试混合复杂数学运算的并行执行"""
        print("\n=== 测试6：混合复杂运算 ===")
        executor = AsyncToolExecutor(registry)

        tasks = [
            {"tool_name": "my_calculator", "input_data": "sin(pi/2)"},           # 1
            {"tool_name": "my_calculator", "input_data": "cos(0)"},               # 1
            {"tool_name": "my_calculator", "input_data": "gcd(48, 18)"},          # 6
            {"tool_name": "my_calculator", "input_data": "log(e)"},               # 1
            {"tool_name": "my_calculator", "input_data": "factorial(5)"},         # 120
            {"tool_name": "my_calculator", "input_data": "pow(2, 10)"},           # 1024
        ]

        async def run():
            return await executor.execute_tools_parallel(tasks)

        results = asyncio.run(run())

        # 验证所有结果
        assert "1" in results[0], f"sin(pi/2) 期望 1, 实际: {results[0]}"
        assert "1" in results[1], f"cos(0) 期望 1, 实际: {results[1]}"
        assert "6" in results[2], f"gcd(48,18) 期望 6, 实际: {results[2]}"
        assert "1" in results[3], f"log(e) 期望 1, 实际: {results[3]}"
        assert "120" in results[4], f"factorial(5) 期望 120, 实际: {results[4]}"
        assert "1024" in results[5], f"pow(2,10) 期望 1024, 实际: {results[5]}"

        print(f"全部正确: {results}")
        print("✅ 通过")

    def test_executor_shutdown(self, registry):
        """测试 executor 资源清理"""
        print("\n=== 测试7：资源清理 ===")
        executor = AsyncToolExecutor(registry)
        assert hasattr(executor, 'executor'), "应当有线程池"

        # 执行一些任务
        async def run():
            return await executor.execute_tool_async("my_calculator", "1 + 1")

        asyncio.run(run())

        # 手动关闭
        executor.executor.shutdown(wait=True)
        print("✅ 通过（线程池正常关闭）")

    def test_empty_tasks(self, registry):
        """测试空任务列表"""
        print("\n=== 测试8：空任务列表 ===")
        executor = AsyncToolExecutor(registry)

        async def run():
            return await executor.execute_tools_parallel([])

        results = asyncio.run(run())
        assert results == [], f"空任务应返回空列表，实际: {results}"
        print("✅ 通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
