from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

import common
from common import (
    Hy3Config,
    assistant_message_to_dict,
    create_client,
    extract_reasoning,
    object_to_dict,
    reasoning_extra_body,
    summarize_completion,
)
from tests.helpers import load_example


class Hy3ConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = Hy3Config.from_mapping({})

        self.assertEqual(config.backend, "self_hosted")
        self.assertEqual(config.base_url, "http://127.0.0.1:8000/v1")
        self.assertEqual(config.api_key, "EMPTY")
        self.assertEqual(config.model, "hy3")
        self.assertEqual(config.timeout, 120.0)

    def test_openrouter_rejects_empty_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "HY3_API_KEY"):
            Hy3Config.from_mapping({"HY3_BACKEND": "openrouter", "HY3_API_KEY": "EMPTY"})

    def test_openrouter_defaults(self) -> None:
        config = Hy3Config.from_mapping(
            {"HY3_BACKEND": "openrouter", "HY3_API_KEY": "test-key"}
        )

        self.assertEqual(config.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(config.model, "tencent/hy3:free")

    def test_empty_string_settings_are_rejected(self) -> None:
        for variable in ("HY3_BASE_URL", "HY3_API_KEY", "HY3_MODEL"):
            with self.subTest(variable=variable):
                with self.assertRaisesRegex(ValueError, variable):
                    Hy3Config.from_mapping({variable: ""})

    def test_non_string_settings_are_rejected(self) -> None:
        for variable in ("HY3_BASE_URL", "HY3_API_KEY", "HY3_MODEL"):
            for value in (None, 123):
                with self.subTest(variable=variable, value=value):
                    with self.assertRaisesRegex(ValueError, variable):
                        Hy3Config.from_mapping({variable: value})

    def test_repr_redacts_api_key(self) -> None:
        secret = "sample-secret"
        config = Hy3Config.from_mapping({"HY3_API_KEY": secret})

        self.assertNotIn(secret, repr(config))

    def test_invalid_backend_and_timeouts_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "HY3_BACKEND"):
            Hy3Config.from_mapping({"HY3_BACKEND": "auto"})

        for timeout in ("0", "-1", "nan", "inf", "not-a-number"):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "HY3_TIMEOUT"):
                    Hy3Config.from_mapping({"HY3_TIMEOUT": timeout})

    def test_reasoning_mapping(self) -> None:
        self_hosted = Hy3Config.from_mapping({})
        openrouter = Hy3Config.from_mapping(
            {"HY3_BACKEND": "openrouter", "HY3_API_KEY": "test-key"}
        )

        for effort in ("no_think", "low", "high"):
            with self.subTest(backend="self_hosted", effort=effort):
                self.assertEqual(
                    reasoning_extra_body(self_hosted, effort),
                    {"chat_template_kwargs": {"reasoning_effort": effort}},
                )

        for effort, mapped_effort in (
            ("no_think", "none"),
            ("low", "low"),
            ("high", "high"),
        ):
            with self.subTest(backend="openrouter", effort=effort):
                self.assertEqual(
                    reasoning_extra_body(openrouter, effort),
                    {"reasoning": {"effort": mapped_effort}},
                )

    def test_invalid_reasoning_effort_is_rejected(self) -> None:
        config = Hy3Config.from_mapping({})

        with self.assertRaises(ValueError):
            reasoning_extra_body(config, "medium")

    def test_from_env_loads_dotenv_without_overriding_environment(self) -> None:
        environment = {
            "HY3_BACKEND": "self_hosted",
            "HY3_BASE_URL": "https://environment.example/v1",
            "HY3_API_KEY": "environment-key",
            "HY3_MODEL": "environment-model",
            "HY3_TIMEOUT": "45",
        }

        with patch.dict(os.environ, environment, clear=True):
            with patch("common.load_dotenv") as load_dotenv:
                config = Hy3Config.from_env()

        load_dotenv.assert_called_once_with(common.API_DIR / ".env", override=False)
        self.assertEqual(config.base_url, environment["HY3_BASE_URL"])
        self.assertEqual(config.api_key, environment["HY3_API_KEY"])
        self.assertEqual(config.model, environment["HY3_MODEL"])
        self.assertEqual(config.timeout, 45.0)

    def test_create_client_forwards_configuration(self) -> None:
        config = Hy3Config.from_mapping(
            {
                "HY3_BASE_URL": "https://example.test/v1",
                "HY3_API_KEY": "test-key",
                "HY3_TIMEOUT": "30",
            }
        )

        with patch("common.OpenAI") as openai:
            client = create_client(config, max_retries=7)

        self.assertIs(client, openai.return_value)
        openai.assert_called_once_with(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=7,
        )


class CompletionNormalizationTests(unittest.TestCase):
    def test_extracts_reasoning_and_structured_details(self) -> None:
        message = SimpleNamespace(
            reasoning="plan",
            reasoning_details=[{"type": "reasoning.text", "text": "plan"}],
        )

        reasoning, details = extract_reasoning(message)

        self.assertEqual(reasoning, "plan")
        self.assertEqual(
            details,
            [{"type": "reasoning.text", "text": "plan"}],
        )

    def test_falls_back_to_model_extra_reasoning_content(self) -> None:
        message = SimpleNamespace(
            model_extra={"reasoning_content": "legacy plan"}
        )

        reasoning, details = extract_reasoning(message)

        self.assertEqual(reasoning, "legacy plan")
        self.assertEqual(details, [])

    def test_falls_back_when_reasoning_is_empty(self) -> None:
        messages = (
            SimpleNamespace(reasoning="", reasoning_content="legacy plan"),
            {"reasoning": "", "reasoning_content": "legacy plan"},
        )

        for message in messages:
            with self.subTest(message=message):
                reasoning, details = extract_reasoning(message)

                self.assertEqual(reasoning, "legacy plan")
                self.assertEqual(details, [])

    def test_derives_text_from_structured_details(self) -> None:
        message = SimpleNamespace(
            model_extra={
                "reasoning_details": [
                    {"type": "reasoning.text", "text": "first "},
                    {"type": "reasoning.text", "text": "second"},
                ]
            }
        )

        reasoning, details = extract_reasoning(message)

        self.assertEqual(reasoning, "first second")
        self.assertEqual(
            details,
            [
                {"type": "reasoning.text", "text": "first "},
                {"type": "reasoning.text", "text": "second"},
            ],
        )

    def test_returns_empty_reasoning_when_absent(self) -> None:
        self.assertEqual(extract_reasoning(SimpleNamespace()), ("", []))

    def test_coerces_reasoning_fields_to_strings(self) -> None:
        messages = (
            SimpleNamespace(reasoning=123),
            SimpleNamespace(reasoning=None, reasoning_content=456),
        )

        for message, expected in zip(messages, ("123", "456")):
            with self.subTest(message=message):
                reasoning, details = extract_reasoning(message)

                self.assertEqual(reasoning, expected)
                self.assertEqual(details, [])

    def test_rejects_non_object_assistant_message(self) -> None:
        with self.assertRaisesRegex(
            TypeError, "^assistant message must serialize to an object$"
        ):
            assistant_message_to_dict("not an object")

    def test_preserves_reasoning_details_in_assistant_history(self) -> None:
        tool_calls = [
            SimpleNamespace(
                id="call_1",
                type="function",
                function=SimpleNamespace(name="lookup", arguments='{"q":"hy3"}'),
            )
        ]
        message = SimpleNamespace(
            role="assistant",
            content=None,
            tool_calls=tool_calls,
            model_extra={
                "reasoning_details": [
                    {"type": "reasoning.text", "text": "plan"}
                ]
            },
        )

        normalized = assistant_message_to_dict(message)

        self.assertEqual(normalized["role"], "assistant")
        self.assertEqual(normalized["tool_calls"], object_to_dict(tool_calls))
        self.assertEqual(
            normalized["reasoning_details"],
            [{"type": "reasoning.text", "text": "plan"}],
        )
        self.assertNotIn("content", normalized)
        self.assertNotIn("model_extra", normalized)

    def test_summarizes_first_choice_and_optional_usage(self) -> None:
        message = SimpleNamespace(
            content="answer",
            reasoning="plan",
            reasoning_details=[{"type": "reasoning.text", "text": "plan"}],
        )
        completion = SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(message=message, finish_reason="stop"),
                SimpleNamespace(
                    message=SimpleNamespace(content="ignored"),
                    finish_reason="length",
                ),
            ],
            usage=SimpleNamespace(total_tokens=7),
        )

        self.assertEqual(
            summarize_completion(completion),
            {
                "model": "hy3",
                "content": "answer",
                "reasoning": "plan",
                "reasoning_details": [
                    {"type": "reasoning.text", "text": "plan"}
                ],
                "finish_reason": "stop",
                "usage": {"total_tokens": 7},
            },
        )


class BasicChatExampleTests(unittest.TestCase):
    @staticmethod
    def _completion(content: str, reasoning: str) -> SimpleNamespace:
        return SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        role="assistant",
                        content=content,
                        reasoning=reasoning,
                        model_extra={},
                    ),
                )
            ],
            usage=SimpleNamespace(total_tokens=5),
        )

    def test_runs_single_and_multi_turn_conversation(self) -> None:
        module = load_example("01_basic_chat.py")
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self._completion("I am Hy3.", "brief plan"),
            self._completion("I can help with APIs.", ""),
        ]
        config = Hy3Config.from_mapping({})

        first, second = module.run_conversation(client, config)

        self.assertEqual(first["content"], "I am Hy3.")
        self.assertEqual(second["content"], "I can help with APIs.")
        second_request = client.chat.completions.create.call_args_list[1].kwargs
        self.assertEqual(
            second_request["messages"][-2:],
            [
                {"role": "assistant", "content": "I am Hy3."},
                {
                    "role": "user",
                    "content": "What kinds of tasks can you help me with?",
                },
            ],
        )


class ReasoningExampleTests(unittest.TestCase):
    @staticmethod
    def _completion(
        content: str,
        reasoning: str = "",
    ) -> SimpleNamespace:
        return SimpleNamespace(
            model="hy3",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        role="assistant",
                        content=content,
                        reasoning=reasoning,
                        model_extra={},
                    ),
                )
            ],
            usage=SimpleNamespace(total_tokens=7),
        )

    def test_compares_no_think_and_high_reasoning_modes(self) -> None:
        module = load_example("05_reasoning_mode.py")
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self._completion("60 km/h"),
            self._completion(
                "60 km/h",
                reasoning="distance divided by time",
            ),
        ]
        config = Hy3Config.from_mapping({})
        question = (
            "A train travels 120 km in 2 hours. What is its average speed?"
        )

        no_think = module.run_mode(
            client,
            config,
            "no_think",
            question,
            clock=iter((1.0, 1.1)).__next__,
        )
        high = module.run_mode(
            client,
            config,
            "high",
            question,
            clock=iter((2.0, 2.3)).__next__,
        )

        no_think_request = client.chat.completions.create.call_args_list[0].kwargs
        high_request = client.chat.completions.create.call_args_list[1].kwargs
        for name in ("model", "messages", "temperature", "top_p", "max_tokens"):
            with self.subTest(name=name):
                self.assertEqual(no_think_request[name], high_request[name])
        self.assertEqual(
            no_think_request["messages"],
            [{"role": "user", "content": question}],
        )
        self.assertEqual(no_think_request["temperature"], 0.9)
        self.assertEqual(no_think_request["top_p"], 1.0)
        self.assertEqual(no_think_request["max_tokens"], 512)
        self.assertEqual(
            no_think_request["extra_body"],
            {"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )
        self.assertEqual(
            high_request["extra_body"],
            {"chat_template_kwargs": {"reasoning_effort": "high"}},
        )
        self.assertEqual(no_think.reasoning, "")
        self.assertEqual(high.reasoning, "distance divided by time")
        self.assertAlmostEqual(high.elapsed, 0.3)

    def test_rejects_modes_outside_the_comparison_contract(self) -> None:
        module = load_example("05_reasoning_mode.py")
        client = MagicMock()
        config = Hy3Config.from_mapping({})
        clock = MagicMock()

        with self.assertRaisesRegex(
            ValueError,
            "effort must be no_think or high",
        ):
            module.run_mode(
                client,
                config,
                "low",
                module.QUESTION,
                clock=clock,
            )

        client.chat.completions.create.assert_not_called()
        clock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
