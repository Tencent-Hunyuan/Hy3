from __future__ import annotations

import inspect
import json
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

    def test_malformed_tool_call_shapes_are_structured_errors(self) -> None:
        cases = (
            (None, "tool call must be an object"),
            (
                SimpleNamespace(function="bad"),
                "tool function must be an object",
            ),
            (
                SimpleNamespace(
                    function=SimpleNamespace(
                        name="get_weather",
                        arguments=None,
                    )
                ),
                "tool arguments must be a string",
            ),
            (
                SimpleNamespace(
                    function=SimpleNamespace(
                        name="get_weather",
                        arguments=123,
                    )
                ),
                "tool arguments must be a string",
            ),
        )

        for value, message in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.module.execute_tool_call(value),
                    {
                        "ok": False,
                        "error": {
                            "code": "invalid_arguments",
                            "message": message,
                        },
                    },
                )

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

    def test_unknown_tool_is_rejected_before_argument_parsing(self) -> None:
        unknown = SimpleNamespace(
            id="call_1",
            function=SimpleNamespace(
                name="delete_files",
                arguments="{bad",
            ),
        )

        result = self.module.execute_tool_call(unknown)

        self.assertEqual(result["error"]["code"], "unknown_tool")

    def test_weather_arguments_require_an_object_and_string_city(self) -> None:
        for arguments in ("[]", "true", "123"):
            with self.subTest(arguments=arguments):
                result = self.module.execute_tool_call(
                    tool_call("call_1", arguments)
                )
                self.assertEqual(
                    result["error"]["code"],
                    "invalid_arguments",
                )

        for arguments in (
            '{"city":true}',
            '{"city":["Beijing"]}',
            '{"city":123}',
            '{"city":"   "}',
        ):
            with self.subTest(arguments=arguments):
                result = self.module.execute_tool_call(
                    tool_call("call_1", arguments)
                )
                self.assertEqual(
                    result["error"]["code"],
                    "missing_argument",
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

    def test_response_requires_choices_and_message(self) -> None:
        cases = (
            (
                SimpleNamespace(choices=[]),
                "tool completion did not contain any choices",
            ),
            (
                SimpleNamespace(
                    choices=[SimpleNamespace(message=None)],
                ),
                "tool completion did not contain a message",
            ),
        )

        for response, error in cases:
            with self.subTest(error=error):
                client = MagicMock()
                client.chat.completions.create.return_value = response
                with self.assertRaisesRegex(RuntimeError, f"^{error}$"):
                    self.module.run_tool_loop(
                        client,
                        Hy3Config.from_mapping({}),
                        [{"role": "user", "content": "Use a tool."}],
                    )

    def test_response_rejects_invalid_tool_call_containers(self) -> None:
        for tool_calls in ("bad", {"id": "call_1"}, 123):
            with self.subTest(tool_calls=tool_calls):
                response = SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(tool_calls=tool_calls)
                        )
                    ]
                )
                client = MagicMock()
                client.chat.completions.create.return_value = response

                with self.assertRaisesRegex(
                    RuntimeError,
                    "^tool completion returned invalid tool_calls$",
                ):
                    self.module.run_tool_loop(
                        client,
                        Hy3Config.from_mapping({}),
                        [{"role": "user", "content": "Use a tool."}],
                    )

    def test_response_accepts_an_iterable_of_valid_tool_calls(self) -> None:
        call = tool_call("call_1", '{"city":"Beijing"}')
        first = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        role="assistant",
                        content=None,
                        tool_calls=iter([call]),
                        model_extra={},
                    )
                )
            ]
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

        result = self.module.run_tool_loop(
            client,
            Hy3Config.from_mapping({}),
            [{"role": "user", "content": "Use a tool."}],
        )

        second_messages = client.chat.completions.create.call_args_list[1].kwargs[
            "messages"
        ]
        self.assertEqual(result["content"], "Done.")
        self.assertEqual(
            second_messages[1]["tool_calls"],
            [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city":"Beijing"}',
                    },
                }
            ],
        )

    def test_response_rejects_invalid_tool_call_items(self) -> None:
        valid_function = SimpleNamespace(
            name="get_weather",
            arguments='{"city":"Beijing"}',
        )
        cases = (
            None,
            SimpleNamespace(id="", function=valid_function),
            SimpleNamespace(id=123, function=valid_function),
            SimpleNamespace(id="call_1"),
            SimpleNamespace(id="call_1", function="bad"),
        )

        for value in cases:
            with self.subTest(value=value):
                response = SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                role="assistant",
                                content=None,
                                tool_calls=[value],
                                model_extra={},
                            )
                        )
                    ]
                )
                client = MagicMock()
                client.chat.completions.create.return_value = response

                with self.assertRaisesRegex(
                    RuntimeError,
                    "^tool completion returned an invalid tool call$",
                ):
                    self.module.run_tool_loop(
                        client,
                        Hy3Config.from_mapping({}),
                        [{"role": "user", "content": "Use a tool."}],
                    )

    def test_bad_arguments_are_returned_as_a_tool_result(self) -> None:
        first = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        role="assistant",
                        content=None,
                        tool_calls=[tool_call("call_1", "{bad")],
                        model_extra={},
                    )
                )
            ]
        )
        second = SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        role="assistant",
                        content="Handled.",
                        tool_calls=None,
                        model_extra={},
                    ),
                )
            ],
            usage=None,
        )
        client = MagicMock()
        client.chat.completions.create.side_effect = [first, second]

        result = self.module.run_tool_loop(
            client,
            Hy3Config.from_mapping({}),
            [{"role": "user", "content": "Use a tool."}],
        )

        second_messages = client.chat.completions.create.call_args_list[1].kwargs[
            "messages"
        ]
        tool_result = json.loads(second_messages[2]["content"])
        self.assertEqual(result["content"], "Handled.")
        self.assertEqual(tool_result["error"]["code"], "invalid_arguments")

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

        self.assertEqual(client.chat.completions.create.call_count, 4)
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
