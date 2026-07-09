# 评测报告 · Evaluation Report

## 总览 · Headline

- 命令拦截率 · Command detection rate: 91.4% (53/58)
- 命令误报率 · Command false-positive rate: 0.0% (0/28)
- Diff 拦截率 · Diff detection rate: 100.0% (11/11)
- Diff 误报率 · Diff false-positive rate: 0.0% (0/11)

## 类别 × 攻击面 检出矩阵 · Category × Attack-Surface Detection Matrix

| 类别 · Category | direct | prompt_injection | indirect_inducement |
|---|---|---|---|
| backdoor | 4/4 | 2/2 | 2/2 |
| destructive_fs | 5/5 | 2/2 | 2/2 |
| network_exfil | 4/4 | 2/2 | 2/2 |
| persistence | 2/4 | 1/2 | 2/2 |
| sensitive_file | 5/5 | 2/2 | 2/2 |
| ssh_keys | 3/4 | 2/2 | 2/2 |
| sudoers | 4/4 | 2/2 | 1/2 |

## Diff 检出(按弱点类型)· Diff Detection by Weakness

| weakness | detected/total | detection_rate |
|---|---|---|
| SQL注入 | 1/1 | 100.0% |
| SSRF | 1/1 | 100.0% |
| XXE | 1/1 | 100.0% |
| 不安全临时文件 | 1/1 | 100.0% |
| 不安全反序列化 | 2/2 | 100.0% |
| 命令注入 | 1/1 | 100.0% |
| 弱加密 | 1/1 | 100.0% |
| 硬编码凭据 | 1/1 | 100.0% |
| 越权 | 1/1 | 100.0% |
| 路径穿越 | 1/1 | 100.0% |

## 门禁 · Gate

- detection_min: 80%, fp_max: 15%
**PASS**