# 火山方舟 Responses API 适配器

from typing import List
import json
import requests
import urllib.request

from .base import BaseLLM


# #region debug-point helper:report
def _debug_report(hypothesis_id: str, location: str, msg: str, data=None):
    payload = {
        "sessionId": "ssl-eof-error",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "msg": msg,
        "data": data or {},
    }
    debug_server_url = "http://127.0.0.1:7777/event"
    debug_session_id = "ssl-eof-error"
    try:
        with open(".dbg/ssl-eof-error.env", encoding="utf-8") as env_file:
            for line in env_file:
                if line.startswith("DEBUG_SERVER_URL="):
                    debug_server_url = line.split("=", 1)[1].strip() or debug_server_url
                elif line.startswith("DEBUG_SESSION_ID="):
                    debug_session_id = line.split("=", 1)[1].strip() or debug_session_id
    except Exception:
        pass
    payload["sessionId"] = debug_session_id
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                debug_server_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            ),
            timeout=1,
        ).read()
    except Exception:
        pass
# #endregion


class ArkResponsesLLM(BaseLLM):
    """
    火山方舟 Responses API 适配器

    使用用户提供的 responses 接口：
    https://ark.cn-beijing.volces.com/api/v3/responses
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        temperature: float = 0.3
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        调用火山方舟 Responses API 生成回答
        """
        if not self.api_key:
            raise ValueError("未配置 ARK_API_KEY")

        payload = {
            "model": self.model,
            "stream": False,
            "input": self._build_input(prompt, system_prompt),
        }

        # #region debug-point A:ark-request
        _debug_report(
            "A",
            "llm/ark_llm.py:generate:pre",
            "[DEBUG] ark request about to start",
            {
                "base_url": self.base_url,
                "model": self.model,
                "timeout": self.timeout,
                "has_api_key": bool(self.api_key),
            },
        )
        # #endregion
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except Exception as exc:
            # #region debug-point B:ark-exception
            _debug_report(
                "B",
                "llm/ark_llm.py:generate:except",
                "[DEBUG] ark request raised exception",
                {
                    "base_url": self.base_url,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            # #endregion
            raise

        # #region debug-point C:ark-response
        _debug_report(
            "C",
            "llm/ark_llm.py:generate:post",
            "[DEBUG] ark request completed",
            {
                "base_url": self.base_url,
                "status_code": response.status_code,
            },
        )
        # #endregion

        if response.status_code >= 400:
            raise RuntimeError(
                f"方舟接口调用失败: HTTP {response.status_code}, {response.text}"
            )

        data = response.json()
        text = self._extract_text(data)
        if not text:
            raise RuntimeError(f"方舟接口返回内容为空: {data}")
        return text

    def _build_input(self, prompt: str, system_prompt: str = None) -> List[dict]:
        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_prompt,
                        }
                    ],
                }
            )

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            }
        )

        return messages

    def _extract_text(self, data: dict) -> str:
        # 兼容可能的直接文本字段
        if isinstance(data.get("output_text"), str) and data["output_text"].strip():
            return data["output_text"].strip()

        output_items = data.get("output", [])
        texts = []

        for item in output_items:
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

        return "\n".join(texts).strip()
