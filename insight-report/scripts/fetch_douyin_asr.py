"""
通过 Coze SDK 以流式方式运行工作流，抓取抖音视频的 ASR 口播文本并落盘。

相比原始脚本，这里补全了「拿到 ASR 信息」的关键一步：
  - 累积所有 MESSAGE 事件的 content 字段（ASR 文本主要在这里）；
  - 运行结束后把纯文本 ASR 写入 --output 指定的文件，供后续 skill 消费。

用法示例：
  python fetch_douyin_asr.py \
      --workflow-id 75xxxxxxxxxxxx \
      --douyin-url "https://v.douyin.com/xxxxx/" \
      --output asr_raw.txt

API Token 优先级：命令行 --api-token > .env / 系统环境变量 COZE_Personal_Access_Token。
依赖：pip install python-dotenv cozepy
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

from cozepy import (
    COZE_CN_BASE_URL,
    Coze,
    TokenAuth,
    Stream,
    WorkflowEvent,
    WorkflowEventType,
)


def _build_parameters(input_text: str, douyin_url: str) -> Dict[str, Any]:
    """
    构造工作流入参。

    工作流起始节点固定接收两个 key：
      - douyinUrl：抖音视频链接（会被替换为实际值）
      - miheApiKey：始终为空字符串

    优先级：显式 --douyin-url > --input-text 里的 JSON。
    """
    if douyin_url:
        return {"douyinUrl": douyin_url, "miheApiKey": ""}

    if input_text:
        try:
            parameters = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(f"[错误] --input-text JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(parameters, dict):
            print("[错误] --input-text 解析后不是字典类型，请检查 JSON 格式", file=sys.stderr)
            sys.exit(2)
        # 强制约束：miheApiKey 始终为空
        parameters.setdefault("douyinUrl", "")
        parameters["miheApiKey"] = ""
        return parameters

    print("[错误] 请通过 --douyin-url 或 --input-text 提供抖音链接", file=sys.stderr)
    sys.exit(2)


def run_workflow_stream(
    workflow_id: str,
    api_token: str,
    parameters: Dict[str, Any],
    output_path: str,
    base_url: str = COZE_CN_BASE_URL,
    resume_data: str = "hey",
) -> str:
    """
    以流式方式执行 Coze 工作流，累积 ASR 文本并写入 output_path。
    返回抓取到的完整 ASR 文本。
    """
    coze = Coze(auth=TokenAuth(token=api_token), base_url=base_url)

    # ⭐ 关键：用列表累积每个 MESSAGE 事件的 content（ASR 文本主要落在 content 字段）
    collected: List[str] = []

    def _handle_stream(stream: Stream[WorkflowEvent]) -> None:
        for event in stream:
            if event.event == WorkflowEventType.MESSAGE:
                msg = event.message
                content = getattr(msg, "content", None)
                if content:
                    collected.append(content)
                    # 实时回显，方便观察抓取进度
                    node = getattr(msg, "node_title", "") or ""
                    print(f"[消息]{('[' + node + ']') if node else ''} {content}")
            elif event.event == WorkflowEventType.ERROR:
                print(f"[错误] {event.error}", file=sys.stderr)
            elif event.event == WorkflowEventType.INTERRUPT:
                print(
                    f"[中断] 正在自动恢复，event_id="
                    f"{event.interrupt.interrupt_data.event_id}"
                )
                resumed_stream = coze.workflows.runs.resume(
                    workflow_id=workflow_id,
                    event_id=event.interrupt.interrupt_data.event_id,
                    resume_data=resume_data,
                    interrupt_type=event.interrupt.interrupt_data.type,
                )
                _handle_stream(resumed_stream)

    initial_stream = coze.workflows.runs.stream(
        workflow_id=workflow_id,
        parameters=parameters,
    )
    _handle_stream(initial_stream)

    asr_text = "\n".join(collected).strip()

    if not asr_text:
        print(
            "[警告] 未抓取到任何 ASR 文本。可能原因：工作流输出字段名不是 content、"
            "链接失效、或工作流内部报错。请检查上方事件日志。",
            file=sys.stderr,
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(asr_text)
    print(f"\n[完成] ASR 文本已写入: {output_path}（{len(asr_text)} 字）")

    return asr_text


def parse_args() -> argparse.Namespace:
    load_dotenv(dotenv_path=".env", override=False)

    parser = argparse.ArgumentParser(
        description="以流式方式运行 Coze 工作流，抓取抖音 ASR 文本并落盘",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--workflow-id", required=True, help="Coze 工作流 ID（必填）")
    parser.add_argument(
        "--api-token",
        default=os.environ.get("COZE_Personal_Access_Token"),
        help="Coze API 访问令牌（默认从 .env 的 COZE_Personal_Access_Token 读取）",
    )
    parser.add_argument(
        "--douyin-url",
        default="",
        help="抖音视频分享链接，例如 https://v.douyin.com/xxxxx/（推荐用这个）",
    )
    parser.add_argument(
        "--input-text",
        default="",
        help=(
            '备用：直接传入工作流入参 JSON，key 固定为 "douyinUrl" 与 "miheApiKey"。'
            '示例：\'{"douyinUrl": "https://v.douyin.com/xxxxx/", "miheApiKey": ""}\''
        ),
    )
    parser.add_argument(
        "--output",
        default="asr_raw.txt",
        help="ASR 文本输出文件路径（默认 asr_raw.txt）",
    )
    parser.add_argument("--base-url", default=COZE_CN_BASE_URL, help="Coze API 端点")
    parser.add_argument(
        "--resume-data", default="hey", help='中断恢复时自动提交的数据（默认 "hey"）'
    )

    args = parser.parse_args()
    if not args.api_token:
        parser.error(
            "未提供 API Token。请通过 --api-token 传入，或在 .env 中设置 "
            "COZE_Personal_Access_Token=你的令牌"
        )
    return args


if __name__ == "__main__":
    args = parse_args()
    params = _build_parameters(args.input_text, args.douyin_url)
    run_workflow_stream(
        workflow_id=args.workflow_id,
        api_token=args.api_token,
        parameters=params,
        output_path=args.output,
        base_url=args.base_url,
        resume_data=args.resume_data,
    )
