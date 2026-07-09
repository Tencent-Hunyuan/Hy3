import { useState, type FormEvent } from 'react';

interface Props {
  onSubmit: (url: string) => void;
  error: string;
}

export function UrlInput({ onSubmit, error }: Props) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onSubmit(trimmed);
  };

  return (
    <div className="max-w-2xl mx-auto mt-12">
      <div className="text-center mb-10">
        <div className="w-16 h-16 mx-auto mb-5 rounded-2xl icon-gradient flex items-center justify-center text-3xl shadow-sm">
          🏛️
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-3 tracking-tight">
          几分钟内理解任何代码库
        </h2>
        <p className="text-gray-500 leading-relaxed max-w-md mx-auto">
          粘贴一个 GitHub 仓库地址，Hy3 将读取所有文件、
          追踪依赖关系，并生成一份完整的架构报告。
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/user/repo"
            className="w-full pl-12 pr-4 py-3.5 border border-gray-200 rounded-xl text-gray-900
                     placeholder-gray-400 focus:ring-0 focus:border-indigo-400 bg-white
                     shadow-sm input-focus transition-all text-sm"
            autoFocus
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!url.trim()}
            className="flex-1 py-3.5 px-6 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200
                     text-white font-medium rounded-xl transition-all disabled:cursor-not-allowed
                     shadow-sm hover:shadow-md disabled:shadow-none active:scale-[0.98]"
          >
            开始分析
          </button>
          <button
            type="button"
            onClick={() => setUrl('')}
            className="px-5 py-3.5 text-gray-400 hover:text-gray-600 transition-colors text-sm"
          >
            清空
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="mt-10 grid grid-cols-3 gap-4 text-center text-sm">
        {[
          { title: '256K 上下文', desc: '单次阅读整个代码库' },
          { title: 'ReAct 智能体', desc: '自主探索与交叉分析' },
          { title: '结构化报告', desc: 'JSON 输出 · 完整可追溯' },
        ].map((c) => (
          <div key={c.title} className="p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="font-semibold text-gray-800">{c.title}</div>
            <div className="mt-1.5 text-gray-500 text-xs">{c.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
