from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from common import Hy3Config
from tests.helpers import load_example


def tool_call(call_id: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name="get_weather", arguments=arguments),
    )


class ToolCallingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_example("04_tool_calling.py")

    def test_invalid_json_is_a_structured_tool_error(self) -> None:
        result = self.module.execute_tool_call(tool_call("call_1", "{bad"))

        self.assertEqual(result["error"]["code"], "invalid_arguments")

    def test_other_tool_errors_are_structured(self) -> None:
        unknown = SimpleNamespace(
            id="call_1",
            function=SimpleNamespace(name="delete_files", arguments="{}"),
        )
        missing = tool_call("call_2", "{}")
        absent = tool_call("call_3", '{"city":"Paris"}')

        self.assertEqual(
            self.module.execute_tool_call(unknown)["error"]["code"],
            "unknown_tool",
        )
        self.assertEqual(
            self.module.execute_tool_call(missing)["error"]["code"],
            "missing_argument",
        )
        self.assertEqual(
            self.module.execute_tool_call(absent)["error"]["code"],
            "city_not_found",
        )

    def test_parallel_calls_append_one_assistant_and_two_tools(self) -> None:
        first_message = SimpleNamespace(
            role="assistant",
            content=None,
            tool_calls=[
                tool_call("call_1", '{"city":"Beijing"}'),
                tool_call("call_2", '{"city":"Shenzhen"}'),
            ],
            model_extra={
                "reasoning_details": [
                    {"type": "reasoning.text", "text": "use both tools"}
                ]
            },
        )
        first = SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=first_message,
                )
            ],
            usage=None,
        )
        second = SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        role="assistant",
                        content="Done.",
                        tool_calls=None,
                        model_extra={},
                    ),
                )
            ],
            usage=None,
        )
        client = MagicMock()
        client.chat.completions.create.side_effect = [first, second]
        messages = [{"role": "user", "content": "Compare both cities."}]

        result = self.module.run_tool_loop(
            client,
            Hy3Config.from_mapping({}),
            messages,
        )

        self.assertEqual(result["content"], "Done.")
        second_request = client.chat.completions.create.call_args_list[1].kwargs
        second_messages = second_request["messages"]
        assistant = [item for item in second_messages if item["role"] == "assistant"]
        tools = [item for item in second_messages if item["role"] == "tool"]
        self.assertEqual(len(assistant), 1)
        self.assertEqual(len(tools), 2)
        self.assertEqual(
            [item["tool_call_id"] for item in tools],
            ["call_1", "call_2"],
        )
        self.assertIn("reasoning_details", assistant[0])
        client.chat.completions.create.assert_called_with(
            model="hy3",
            messages=second_messages,
            tools=self.module.TOOLS,
            tool_choice="auto",
            temperature=0.9,
            top_p=1.0,
            max_tokens=512,
            extra_body={
                "chat_template_kwargs": {"reasoning_effort": "no_think"}
            },
        )

    def test_loop_limit_is_enforced(self) -> None:
        repeated = SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        role="assistant",
                        content=None,
                        tool_calls=[tool_call("call_1", '{"city":"Beijing"}')],
                        model_extra={},
                    ),
                )
            ],
            usage=None,
        )
        client = MagicMock()
        client.chat.completions.create.return_value = repeated

        with self.assertRaisesRegex(RuntimeError, "max_rounds=4"):
            self.module.run_tool_loop(
                client,
                Hy3Config.from_mapping({}),
                [{"role": "user", "content": "Keep calling."}],
            )

        forbidden = "eval" + "("
        self.assertNotIn(forbidden, inspect.getsource(self.module))

    def test_demo_weather_is_deterministic(self) -> None:
        self.assertEqual(
            self.module.DEMO_WEATHER,
            {
                "Beijing": {"condition": "sunny", "temperature_c": 24},
                "Shenzhen": {"condition": "rainy", "temperature_c": 29},
            },
        )


if __name__ == "__main__":
    unittest.main()
