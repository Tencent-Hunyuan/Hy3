import os
import json
import time
from openai import OpenAI
from datetime import datetime

# 初始化 Hy3 客户端
client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=os.environ.get("TOKENHUB_API_KEY"),
)

def load_test_cases(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)['tasks']

def evaluate_task(task):
    """对单个任务进行评测"""
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model="hy3-preview",
            messages=[
                {"role": "system", "content": "你是一个严谨的技术专家，请根据用户要求生成准确的回答。"},
                {"role": "user", "content": task['prompt']}
            ],
            temperature=0.3,
        )
        elapsed_time = time.time() - start_time
        result = {
            "task_id": task['id'],
            "status": "success",
            "response": response.choices[0].message.content,
            "tokens": response.usage.total_tokens,
            "time_seconds": round(elapsed_time, 2)
        }
    except Exception as e:
        result = {
            "task_id": task['id'],
            "status": "error",
            "error": str(e),
            "time_seconds": round(time.time() - start_time, 2)
        }
    return result

def main():
    test_cases = load_test_cases('test_cases.json')
    results = []
    
    print(f"🔄 开始评测 {len(test_cases)} 个任务...")
    for i, task in enumerate(test_cases, 1):
        print(f"  [{i}/{len(test_cases)}] 正在评测: {task['id']} - {task['category']}")
        result = evaluate_task(task)
        results.append(result)
        print(f"     ✅ 完成 (耗时: {result.get('time_seconds', 'N/A')}s)")

    # 生成评测报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tasks": len(results),
        "success_count": sum(1 for r in results if r['status'] == 'success'),
        "error_count": sum(1 for r in results if r['status'] == 'error'),
        "total_tokens": sum(r.get('tokens', 0) for r in results),
        "avg_time": round(sum(r.get('time_seconds', 0) for r in results) / len(results), 2),
        "results": results
    }

    # 保存报告
    with open('evaluation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print("\n" + "="*50)
    print("📋 评测摘要")
    print("="*50)
    print(f"总任务数: {report['total_tasks']}")
    print(f"成功: {report['success_count']}  |  失败: {report['error_count']}")
    print(f"总 Token 消耗: {report['total_tokens']}")
    print(f"平均响应时间: {report['avg_time']}s")
    print(f"报告已保存: evaluation_report.json")
    print("="*50)

if __name__ == "__main__":
    main()
