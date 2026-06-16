# Debug Session: ssl-eof-error

Status: [OPEN]
Date: 2026-06-16

## User Report
- Summary: Streamlit 运行过程中出现 `httpx.ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol`
- Expected: 相关远程请求正常完成，页面不因 SSL 连接异常而失败
- Actual: 运行时在 `httpx` 请求链路中抛出 SSL EOF 异常

## Initial Hypotheses
| ID | Hypothesis | Likelihood | Effort | Expected Signal |
|----|------------|------------|--------|-----------------|
| A | 请求目标 URL 或协议配置错误，实际访问了不支持 TLS 的端点 | High | Low | 日志中出现具体目标 URL/host，且为 `https` 到非 TLS 服务 |
| B | 代理、网关或公司网络中间层中断了 TLS 握手 | Medium | Medium | 相同代码对同一 host 在不同环境/重试下表现不一致，异常发生在连接建立阶段 |
| C | 应用对某第三方 API 的 base URL、证书校验或请求头配置不兼容 | High | Low | 日志显示异常固定发生在某个 API client 调用前后 |
| D | 某处使用了错误的重定向/拼接地址，导致 `httpx` 跟随到了异常 TLS 终点 | Medium | Medium | 日志中可见请求前 URL 与最终目标 host/path 不一致 |
| E | 依赖库或 Python/OpenSSL 组合与目标服务握手存在兼容性问题 | Low | Medium | 同一 URL 在独立最小化请求下也稳定报相同 SSL EOF |

## Evidence Plan
- 定位项目中所有 `httpx`/远程 LLM/Supabase/HTTP 请求入口。
- 对最可能的请求链路增加最小埋点，记录 URL、调用模块、异常类型。
- 复现后读取 `.dbg/trae-debug-log-ssl-eof-error.ndjson` 分析根因。

## Current State
- 仅完成会话初始化，尚未修改业务逻辑。
