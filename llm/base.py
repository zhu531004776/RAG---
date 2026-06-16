# 大模型接口基类

from abc import ABC, abstractmethod

class BaseLLM(ABC):
    """
    大模型接口抽象基类

    定义大模型接口规范，所有适配器需实现generate方法
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        生成回答

        Args:
            prompt: 用户Prompt
            system_prompt: 系统提示词（可选）

        Returns:
            生成的文本回答
        """
        pass
