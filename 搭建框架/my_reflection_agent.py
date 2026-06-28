DEFAULT_PROMPTS = {
    "initial": """
请根据以下要求完成任务:

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间:

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答:

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
"""
}

from typing import Optional, List
from hello_agents import HelloAgentsLLM, Config, Message, ToolRegistry, ReflectionAgent

class MyReflectionAgent(ReflectionAgent):
    """
    重写的Reflection Agent - 反思和改进的智能体
    """
    def __init__(
            self,
            name: str,
            llm: HelloAgentsLLM,
            tool_registry: Optional[ToolRegistry] = None,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            max_steps: int = 5,
            prompts: Optional[dict] = None,
            custom_prompts: Optional[dict[str, str]] = None
        ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.prompts = prompts or DEFAULT_PROMPTS
        self.current_history: List[str] = []
        self.prompt_template = custom_prompts if custom_prompts else self.prompts["initial"]
        print(f"✅ {name} 初始化完成，最大步数: {max_steps}")

    def run(self, input_text: str, **kwargs) -> str:
        """运行Reflection Agent"""
        self.current_history = []

        print(f"\n🤖 {self.name} 开始处理任务: {input_text}")

        # --- 1. 初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = self.prompts["initial"].format(task=input_text)
        messages = [{"role": "user", "content": initial_prompt}]
        current_result = self.llm.invoke(messages, **kwargs) or ""
        self.current_history.append(f"初始回答: {current_result}")

        # --- 2. 迭代循环：反思与优化 ---
        for i in range(self.max_steps):
            print(f"\n--- 第 {i+1}/{self.max_steps} 轮迭代 ---")

            # a. 反思
            print("\n-> 正在进行反思...")
            reflect_prompt = self.prompts["reflect"].format(
                task=input_text,
                content=current_result
            )
            messages = [{"role": "user", "content": reflect_prompt}]
            feedback = self.llm.invoke(messages, **kwargs) or ""
            self.current_history.append(f"反思反馈: {feedback}")

            # b. 检查是否需要停止
            if "无需改进" in feedback:
                print("\n✅ 反思认为结果已无需改进，任务完成。")
                break

            # c. 优化
            print("\n-> 正在进行优化...")
            refine_prompt = self.prompts["refine"].format(
                task=input_text,
                last_attempt=current_result,
                feedback=feedback
            )
            messages = [{"role": "user", "content": refine_prompt}]
            current_result = self.llm.invoke(messages, **kwargs) or ""
            self.current_history.append(f"第{i+1}轮优化结果: {current_result}")

        # --- 3. 返回最终结果 ---
        final_answer = current_result or ""
        print(f"\n--- 任务完成 ---")
        print(f"最终结果:\n{final_answer}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))

        return final_answer
