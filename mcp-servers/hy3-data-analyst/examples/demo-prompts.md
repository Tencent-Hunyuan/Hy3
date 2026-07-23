# Demo prompts

These prompts exercise all three tools against `examples/sample_sales.csv`.

1. `Use profile_dataset on examples/sample_sales.csv and summarize its data quality.`
2. `Use analyze_dataset to identify the strongest region and explain what the sample can and cannot prove.`
3. `Use generate_data_report to create a management report focused on revenue and missing data.`

The client process must set `HY3_DATA_DIR` to this package directory. The latter two prompts require
a reachable Hy3 OpenAI-compatible endpoint.
