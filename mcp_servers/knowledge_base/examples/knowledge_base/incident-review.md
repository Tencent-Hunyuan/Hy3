# Incident Review: Chinese Short Query Outage

On 2025-05-14, searches containing only the two-character term “退款” returned no results.
Detection occurred at 09:10 and mitigation completed at 09:37, a duration of 27 minutes.

The root cause was relying only on trigram FTS. The permanent corrective action was the
bounded LIKE fallback owned by Ren Zhao.

中文“退款”短查询事故持续 27 分钟。
Exact answer token: 27.
