# 03 流式与非流式对比

对比 Chat Completions API 两种请求方式的首 chunk 延迟和总耗时。

## 运行

```bash
uv run --env-file .env python examples/03_streaming_vs_non_streaming.py
```

## 请求和解析

脚本使用相同的 `model` 和 `messages` 分别发起 `stream: false` 与 `stream: true` 请求。

非流式请求从 `response.choices[0].message.content` 读取结果；流式请求拼接每个 `delta.content`，并记录第一个 chunk 到达时间和完整响应耗时。

## 输出示例

```text
non-streaming total: 2.351s
streaming first chunk: 0.830s
streaming total: 1.859s
streaming text: 深圳是中国南方毗邻香港的经济特区和超大城市，以科技创新与金融贸易闻名。这里拥有华为、腾讯等全球领先企业，被誉为“中国硅谷”。作为改革开放的窗口，深圳以高速发展、年轻活力和多元文化成为现代化国际都市的典范。
non-streaming text: 深圳是中国南部海滨的现代化大都市，也是改革开放后迅速崛起的经济特区和创新之都。这里拥有华为、腾讯等科技巨头，以高新技术、金融和物流产业为核心驱动发展。作为移民城市，深圳包容开放、充满活力，连续多年常住人口年轻化指数居全国前列。
```

耗时受网络、服务负载和输出长度影响，不能将单次测量结果视为固定性能指标。
