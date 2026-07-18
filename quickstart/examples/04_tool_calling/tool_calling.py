"""Hy3 一次工具调用与多轮工具调用循环示例。"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def load_project_env() -> None:
    candidates = [Path.cwd() / ".env", Path.cwd() / "quickstart" / ".env"]
    if "__file__" in globals():
        candidates.insert(0, Path(__file__).resolve().parents[2] / ".env")
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


load_project_env()

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")
MAX_TOKENS = int(os.getenv("HY3_MAX_TOKENS", "128"))
REASONING_EFFORT = os.getenv("HY3_REASONING_EFFORT", "no_think")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "返回内置示例天气数据，不访问真实天气服务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "description": "在摄氏度与华氏度之间转换温度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                    "to_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
]


def get_weather(city: str) -> dict:
    sample_temperatures = {"深圳": 28.0, "北京": 22.0, "上海": 26.0}
    return {
        "city": city,
        "temperature": sample_temperatures.get(city, 25.0),
        "unit": "celsius",
        "condition": "晴（内置示例数据）",
    }


def convert_temperature(value: float, from_unit: str, to_unit: str) -> dict:
    if from_unit == to_unit:
        converted = value
    elif from_unit == "celsius" and to_unit == "fahrenheit":
        converted = value * 9 / 5 + 32
    elif from_unit == "fahrenheit" and to_unit == "celsius":
        converted = (value - 32) * 5 / 9
    else:
        raise ValueError("不支持的温度单位")
    return {"value": round(converted, 2), "unit": to_unit}


TOOL_HANDLERS = {
    "get_weather": get_weather,
    "convert_temperature": convert_temperature,
}


def assistant_message_to_dict(message) -> dict:
    data = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        data["tool_calls"] = [
            {
                "id": call.id,
                "type": call.type,
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return data


def execute_tool_call(tool_call) -> dict:
    name = tool_call.function.name
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"工具参数不是合法 JSON: {exc}"}

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"ok": False, "error": f"不允许调用工具: {name}"}
    try:
        return {"ok": True, "result": handler(**arguments)}
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


def print_response(round_number: int, response) -> None:
    print(f"\nround={round_number}, id={response.id}, model={response.model}")
    for choice in response.choices:
        message = choice.message
        print(f"choice[{choice.index}].finish_reason={choice.finish_reason}")
        print(f"choice[{choice.index}].content={message.content}")
        for call in message.tool_calls or []:
            print(
                f"tool_call: id={call.id}, name={call.function.name}, "
                f"arguments={call.function.arguments}"
            )
    if response.usage:
        print(
            "usage: "
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}"
        )


def run_tool_loop(client: OpenAI, messages: list[dict], max_rounds: int = 5) -> str:
    for round_number in range(1, max_rounds + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.9,
            top_p=1.0,
            max_tokens=MAX_TOKENS,
            extra_body={
                "chat_template_kwargs": {
                    "reasoning_effort": REASONING_EFFORT,
                }
            },
        )
        print_response(round_number, response)

        message = response.choices[0].message
        messages.append(assistant_message_to_dict(message))
        if not message.tool_calls:
            return message.content or ""

        for tool_call in message.tool_calls:
            result = execute_tool_call(tool_call)
            print(f"tool_result[{tool_call.id}]={result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError(f"超过最大工具调用轮数 {max_rounds}")


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    print("=== 一次工具调用 ===")
    run_tool_loop(
        client,
        [
            {
                "role": "user",
                "content": "调用 get_weather 查询深圳天气，然后根据工具结果回答。",
            }
        ],
    )

    print("\n=== 多轮工具循环 ===")
    run_tool_loop(
        client,
        [
            {
                "role": "user",
                "content": (
                    "先调用 get_weather 查询北京示例温度，再调用 "
                    "convert_temperature 把摄氏度转换为华氏度，最后总结。"
                ),
            }
        ],
    )


if __name__ == "__main__":
    main()
