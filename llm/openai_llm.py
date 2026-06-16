# OpenAI兼容接口的大模型适配器

from openai import OpenAI
from .base import BaseLLM

class OpenAICompatibleLLM(BaseLLM):
    """
    OpenAI兼容接口的大模型适配器

    支持：
    - OpenAI官方API
    - Azure OpenAI
    - LocalAI
    - 以及其他兼容OpenAI格式的API（如vLLM、LM Studio等）
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        temperature: float = 0.3
    ):
        """
        初始化OpenAI兼容接口

        Args:
            base_url: API基础URL
            api_key: API密钥
            model: 模型名称
            timeout: 请求超时时间（秒）
            temperature: 生成温度
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        调用大模型生成回答

        实现步骤：
        1. 构建消息列表
        2. 添加系统提示词（如有）
        3. 添加用户问题
        4. 调用API并返回回答

        Args:
            prompt: 用户Prompt
            system_prompt: 系统提示词

        Returns:
            生成的文本回答
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature
        )

        return response.choices[0].message.content
