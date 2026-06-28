import os
from typing import Optional
from openai import OpenAI
from hello_agents import HelloAgentsLLM
from dotenv import load_dotenv

load_dotenv()

class MyLLM(HelloAgentsLLM):
    def __init__(self,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 provider: Optional[str] = None,
                 **kwargs
                 ):
        # 检查provider是否为我们想处理的'dashscope'
        if provider == "dashscope":
            print("正在使用自定义的 DashScope Provider")
            self.provider = "dashscope"

            # 解析 DashScope 的凭证
            self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
            self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

            # 验证凭证是否存在
            if not self.api_key:
                raise ValueError("DashScope API key not found. Please set DASHSCOPE_API_KEY environment variable.")

            # 设置默认模型和其他参数
            self.model = model or os.getenv("DASHSCOPE_MODEL_NAME") or "qwen3.6-plus"
            self.temperature = kwargs.get("temperature", 0.7)
            self.max_tokens = kwargs.get("max_tokens")
            self.timeout = kwargs.get("timeout", 60)

            # 使用获取的参数创建OpenAI客户端实例
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

        else:
            # 如果不是 modelscope, 则完全使用父类的原始逻辑来处理
            super().__init__(model=model, api_key=api_key, base_url=base_url, provider=provider, **kwargs)