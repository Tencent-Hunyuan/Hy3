import { useState, useRef, useEffect, type FormEvent } from 'react';
import type { ArchitectureReport } from '../../types';
import { askQuestion } from '../../api';

interface Props { jobId: string; report: ArchitectureReport; }

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

export function QATab({ jobId, report }: Props) {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions: string[] = [];
  if (report.risks.length > 0) suggestions.push('最严重的风险是什么？如何修复？');
  if (report.modules.length > 0) {
    const core = report.modules.find((m) => m.stability === 'high');
    if (core) suggestions.push(`${core.name} 是如何工作的？谁依赖它？`);
  }
  if (report.call_chains.length > 0) suggestions.push(`详述「${report.call_chains[0].name}」这条调用链`);
  if (report.design_patterns.length > 0) suggestions.push(`为什么这里使用了 ${report.design_patterns[0].pattern} 模式？`);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: q };
    const assistantId = (Date.now() + 1).toString();
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setQuestion('');
    setLoading(true);

    try {
      const response = await askQuestion(jobId, q);
      setMessages((prev) => prev.map((m) =>
        m.id === assistantId ? { ...m, content: response.answer, streaming: false } : m
      ));
    } catch (err: any) {
      setMessages((prev) => prev.map((m) =>
        m.id === assistantId ? { ...m, content: `请求失败: ${err.message || '未知错误'}`, streaming: false } : m
      ));
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[560px]">
      {/* 消息区 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-5 pr-2 mb-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <p className="text-gray-400 mb-5">基于分析结果，向 Hy3 追问任何架构细节</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setQuestion(s)}
                  className="px-3.5 py-2 bg-gray-50 hover:bg-gray-100 text-gray-500
                           hover:text-gray-700 text-sm rounded-xl transition-all border border-gray-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[82%] rounded-2xl px-5 py-3.5 ${
              msg.role === 'user'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-50 text-gray-700 border border-gray-100'
            }`}>
              <div className="text-sm leading-relaxed whitespace-pre-wrap">
                {msg.content}
                {msg.streaming && <span className="typing-cursor" />}
              </div>
            </div>
          </div>
        ))}

        {loading && messages.length === 0 && (
          <div className="flex justify-start">
            <div className="bg-gray-50 border border-gray-100 rounded-2xl px-5 py-3.5">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <div className="w-2 h-2 bg-indigo-300 rounded-full animate-bounce [animation-delay:150ms]" />
                <div className="w-2 h-2 bg-indigo-200 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 输入框 */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="追问代码库的任何细节..."
          disabled={loading}
          className="flex-1 px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm
                   text-gray-700 placeholder-gray-400 input-focus transition-all
                   disabled:opacity-50 disabled:bg-gray-50"
        />
        <button
          type="submit"
          disabled={!question.trim() || loading}
          className="px-5 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200
                   text-white text-sm font-medium rounded-xl transition-all
                   disabled:text-gray-400 disabled:cursor-not-allowed shadow-sm hover:shadow-md
                   disabled:shadow-none"
        >
          {loading ? '...' : '追问'}
        </button>
      </form>

      <p className="text-[11px] text-gray-400 mt-2.5 text-center">
        Hy3 流式推理 · 混合检索 · 上下文感知
      </p>
    </div>
  );
}
