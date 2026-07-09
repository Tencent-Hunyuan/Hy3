from setuptools import find_packages, setup


setup(
    name="hy3-mcp-server",
    version="0.1.0",
    description="A stdio MCP server for Tencent Hunyuan Hy3 OpenAI-compatible inference APIs.",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "mcp>=1.9.0",
        "openai>=1.90.0",
        "pydantic>=2.7.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hy3-mcp-server=hy3_mcp_server.server:main",
        ],
    },
)
