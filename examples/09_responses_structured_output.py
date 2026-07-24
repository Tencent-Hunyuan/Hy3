"""Generate and parse structured output with the Responses API."""

import json
import os

from openai import OpenAI


# JSON Schema that defines the expected response shape.
PERSON_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "gender": {"type": "string"},
        "age": {"type": "number"},
        "city": {"type": "string"},
    },
    "required": ["name", "gender", "age", "city"],
    "additionalProperties": False,
}


def main():
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )

    # Ask the model to return JSON matching the schema.
    response = client.responses.create(
        model="hy3",
        input="提取以下文本中的人物信息：张三，男，25岁，北京人。",
        text={
            "format": {
                "type": "json_schema",
                "name": "person_info",
                "schema": PERSON_INFO_SCHEMA,
                "strict": True,
            }
        },
    )

    # output_text is a JSON string, so parse it into a Python dictionary.
    person = json.loads(response.output_text)
    print(json.dumps(person, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
