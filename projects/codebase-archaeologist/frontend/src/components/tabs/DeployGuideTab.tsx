import { useState, useEffect, useRef } from 'react';
import type { ArchitectureReport } from '../../types';

interface Props { report: ArchitectureReport; }

export function DeployGuideTab({ report }: Props) {
  const [activeSection, setActiveSection] = useState<string>('overview');

  // Derive deployment recommendations from the report
  const language = report.overview.language || '';
  const framework = report.overview.framework || '';
  const modules = report.modules;
  const hasDb = modules.some(m => m.responsibility.toLowerCase().includes('database') || m.responsibility.toLowerCase().includes('数据') || m.responsibility.toLowerCase().includes('db'));
  const hasApi = modules.some(m => m.responsibility.toLowerCase().includes('api') || m.responsibility.toLowerCase().includes('http') || m.responsibility.toLowerCase().includes('请求') || m.responsibility.toLowerCase().includes('路由'));
  const hasConfig = modules.some(m => m.path.toLowerCase().includes('config') || m.path.toLowerCase().includes('env'));
  const entryFiles = modules.filter(m => m.depended_by.length >= 2 || m.path.match(/(main|app|index|server|entry)/i));

  const isPython = language.toLowerCase().includes('python');
  const isJS = language.toLowerCase().includes('javascript') || language.toLowerCase().includes('typescript');
  const isGo = language.toLowerCase().includes('go');

  const sections = [
    { id: 'overview', label: '部署概览', icon: '📋' },
    { id: 'env', label: '环境要求', icon: '⚙️' },
    { id: 'steps', label: '部署步骤', icon: '🚀' },
    { id: 'config', label: '配置说明', icon: '🔧' },
    { id: 'monitor', label: '监控运维', icon: '📊' },
  ];

  return (
    <div className="space-y-6">
      {/* Section nav */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="flex overflow-x-auto border-b border-gray-100">
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-all
                ${activeSection === s.id
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/50'
                  : 'text-gray-500 hover:text-gray-700'}
              `}
            >
              <span className="mr-1.5">{s.icon}</span>
              {s.label}
            </button>
          ))}
        </div>

        {/* Content panels */}
        <div className="p-6">
          {activeSection === 'overview' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-gray-800">部署概览</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                基于对仓库架构的分析，以下信息总结了该项目的部署方式与推荐基础设施。
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InfoCard icon="🖥" label="语言 / 框架" value={`${language} / ${framework}`} />
                <InfoCard icon="📦" label="模块数量" value={`${modules.length} 个模块`} />
                <InfoCard icon="🔗" label="入口文件" value={entryFiles.map(f => f.name).join(', ') || '未检测到'} />
                <InfoCard icon="🗄" label="数据库依赖" value={hasDb ? '需要数据库' : '未检测到数据库依赖'} />
                <InfoCard icon="🌐" label="API 服务" value={hasApi ? '包含 Web API' : '非 Web 服务'} />
                <InfoCard icon="⚙️" label="配置文件" value={hasConfig ? '包含配置文件' : '未检测到显式配置'} />
              </div>

              {isPython && (
                <DeployCard type="python" framework={framework} />
              )}
              {isJS && (
                <DeployCard type="js" framework={framework} />
              )}
              {isGo && (
                <DeployCard type="go" framework={framework} />
              )}
              {!isPython && !isJS && !isGo && (
                <DeployCard type="generic" framework={framework} />
              )}
            </div>
          )}

          {activeSection === 'env' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-gray-800">环境要求</h3>
              {isPython && (
                <div className="space-y-4">
                  <RequirementBlock title="Python 版本" items={['Python >= 3.10', 'pip 包管理器', '推荐使用虚拟环境 (venv / conda)']} />
                  <RequirementBlock title="系统依赖" items={['Git（用于拉取代码）', hasDb ? 'PostgreSQL / MySQL / SQLite' : '无额外数据库要求']} />
                  <RequirementBlock title="推荐基础设施" items={['Linux 服务器 (Ubuntu 22.04+)', '至少 2GB RAM', '1 核 CPU 起步']} />
                </div>
              )}
              {isJS && (
                <div className="space-y-4">
                  <RequirementBlock title="Node.js 版本" items={['Node.js >= 18', 'npm / yarn / pnpm 包管理器']} />
                  <RequirementBlock title="系统依赖" items={['Git', hasDb ? 'PostgreSQL / MySQL / MongoDB' : '无额外数据库要求']} />
                  <RequirementBlock title="推荐基础设施" items={['Linux 服务器 (Ubuntu 22.04+)', '至少 1GB RAM', '推荐使用 PM2 或 systemd 管理进程']} />
                </div>
              )}
              {isGo && (
                <div className="space-y-4">
                  <RequirementBlock title="Go 版本" items={['Go >= 1.21', 'GOPATH 已配置']} />
                  <RequirementBlock title="系统依赖" items={['Git', '编译产物为静态二进制文件，无运行时依赖']} />
                  <RequirementBlock title="推荐基础设施" items={['Linux 服务器', '最小 256MB RAM', '可直接部署二进制文件']} />
                </div>
              )}
            </div>
          )}

          {activeSection === 'steps' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-gray-800">部署步骤</h3>
              <p className="text-sm text-gray-500">以下为推荐的部署流程，请根据实际情况调整。</p>

              {isPython && <PythonDeploySteps framework={framework} hasDb={hasDb} />}
              {isJS && <JSDeploySteps framework={framework} hasDb={hasDb} />}
              {isGo && <GoDeploySteps framework={framework} hasDb={hasDb} />}
              {!isPython && !isJS && !isGo && <GenericDeploySteps />}
            </div>
          )}

          {activeSection === 'config' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-gray-800">配置说明</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                根据分析结果，以下配置项需要关注：
              </p>

              {report.overview.framework === 'FastAPI' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
                  <strong>FastAPI 部署提示：</strong> 推荐使用 Uvicorn + Gunicorn 的组合部署方式。
                  设置 <code className="bg-blue-100 px-1.5 py-0.5 rounded">--workers</code> 为 CPU 核数的 2-4 倍。
                </div>
              )}

              {report.overview.framework === 'Django' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
                  <strong>Django 部署提示：</strong> 确认 <code className="bg-blue-100 px-1.5 py-0.5 rounded">ALLOWED_HOSTS</code>、
                  <code className="bg-blue-100 px-1.5 py-0.5 rounded">SECRET_KEY</code> 和
                  <code className="bg-blue-100 px-1.5 py-0.5 rounded">DEBUG=False</code> 已在生产环境正确配置。
                </div>
              )}

              <div className="space-y-3">
                <ConfigBlock title="环境变量" items={[
                  { key: 'PORT', desc: '服务监听端口 (默认: 8000)', required: true },
                  { key: 'HOST', desc: '绑定的主机地址 (默认: 0.0.0.0)', required: false },
                  { key: 'LOG_LEVEL', desc: '日志级别 (INFO / WARNING / ERROR)', required: false },
                  hasDb ? { key: 'DATABASE_URL', desc: '数据库连接字符串', required: true } : null,
                  { key: 'API_KEY', desc: 'API 密钥（如适用）', required: false },
                ].filter(Boolean) as { key: string; desc: string; required: boolean }[]} />

                {hasConfig && (
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <h5 className="text-sm font-medium text-gray-700 mb-2">已检测到的配置文件</h5>
                    <div className="flex flex-wrap gap-2">
                      {report.modules.filter(m => m.path.toLowerCase().includes('config') || m.path.toLowerCase().includes('env')).map(m => (
                        <code key={m.path} className="px-2.5 py-1 bg-gray-50 text-gray-600 rounded text-xs border border-gray-200 font-mono">
                          {m.path}
                        </code>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeSection === 'monitor' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-gray-800">监控与运维</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">🔍 健康检查</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>· 定期检查 <code className="bg-gray-50 px-1.5 py-0.5 rounded text-xs">/api/health</code> 端点</li>
                    <li>· 关注服务响应时间趋势</li>
                    <li>· 设置告警阈值（如 5xx {'>'} 1%）</li>
                  </ul>
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">📋 日志管理</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>· 使用结构化日志格式 (JSON)</li>
                    <li>· 按日轮转日志文件</li>
                    <li>· 保留至少 30 天历史日志</li>
                  </ul>
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">📊 性能监控</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>· 追踪模块间调用延迟</li>
                    <li>· 监控关键调用链的吞吐量</li>
                    <li>· 关注上帝类候选模块的性能瓶颈</li>
                  </ul>
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">🔄 备份与恢复</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>· 每日自动备份数据库</li>
                    <li>· 保留最近 7 天的全量备份</li>
                    <li>· 定期演练恢复流程</li>
                  </ul>
                </div>
              </div>

              {report.risks.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-amber-700 mb-2">⚠️ 部署注意事项</h4>
                  <p className="text-xs text-amber-600 mb-2">
                    分析发现了 {report.risks.length} 个潜在风险，部署前建议优先处理高危和严重风险：
                  </p>
                  <ul className="space-y-1">
                    {report.risks.filter(r => r.severity === 'critical' || r.severity === 'high').slice(0, 3).map((r, i) => (
                      <li key={i} className="text-xs text-amber-700">
                        [{r.severity === 'critical' ? '严重' : '高危'}] {r.risk_type} — {Array.isArray(r.location) ? r.location.join(', ') : r.location}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────

function InfoCard({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg border border-gray-100">
      <span className="text-xl">{icon}</span>
      <div>
        <div className="text-xs text-gray-400 uppercase tracking-wider">{label}</div>
        <div className="text-sm font-medium text-gray-700 mt-0.5">{value}</div>
      </div>
    </div>
  );
}

function DeployCard({ type, framework }: { type: string; framework: string }) {
  const suggestions: Record<string, { title: string; items: string[] }> = {
    python: {
      title: 'Python 部署建议',
      items: [
        '使用 Docker 容器化部署（推荐 python:3.12-slim 基础镜像）',
        framework === 'FastAPI' ? '使用 Gunicorn + Uvicorn workers 提高并发' : '',
        framework === 'Django' ? '使用 Gunicorn + WSGI + Nginx 反向代理' : '',
        framework === 'Flask' ? '使用 Gunicorn + Nginx 反向代理' : '',
        '在生产环境中使用生产级 ASGI/WSGI 服务器，不要使用开发服务器',
        '使用 pip-tools 或 Poetry 锁定依赖版本',
      ].filter(Boolean),
    },
    js: {
      title: 'Node.js 部署建议',
      items: [
        '使用 Docker 容器化部署（推荐 node:20-alpine 基础镜像）',
        framework === 'Next.js' ? '使用 next start 启动生产模式' : '',
        framework === 'Express' ? '使用 PM2 或 systemd 管理进程' : '',
        '使用 npm ci 安装依赖以确保一致性',
        '设置 NODE_ENV=production',
      ].filter(Boolean),
    },
    go: {
      title: 'Go 部署建议',
      items: [
        '编译为静态二进制文件：CGO_ENABLED=0 go build -o app',
        '使用 scratch 或 alpine 基础镜像构建最小 Docker 镜像',
        '二进制文件可直接部署，无需额外运行时',
        '使用 systemd 或 supervisord 管理进程',
      ],
    },
    generic: {
      title: '通用部署建议',
      items: [
        '使用 Docker 容器化确保环境一致性',
        '通过 CI/CD 流水线自动化构建与部署',
        '部署前在预发布环境充分测试',
      ],
    },
  };

  const s = suggestions[type] || suggestions.generic;
  return (
    <div className="bg-indigo-50/50 border border-indigo-100 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-indigo-700 mb-2">{s.title}</h4>
      <ul className="space-y-1.5">
        {s.items.map((item, i) => (
          <li key={i} className="text-sm text-indigo-600 flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">▸</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RequirementBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-gray-700 mb-2">{title}</h4>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ConfigBlock({ title, items }: { title: string; items: { key: string; desc: string; required: boolean }[] }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-gray-700 mb-3">{title}</h4>
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.key} className="flex items-center gap-3 text-sm">
            <code className="px-2 py-0.5 bg-gray-50 text-gray-700 rounded text-xs font-mono border border-gray-200 min-w-[120px]">
              {item.key}
            </code>
            <span className="text-gray-500">{item.desc}</span>
            {item.required && (
              <span className="px-1.5 py-0.5 bg-red-50 text-red-500 text-[10px] font-medium rounded border border-red-200">必填</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Language-specific step guides ──────────────────────────────

function StepItem({ num, title, code }: { num: number; title: string; code?: string }) {
  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-indigo-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 shadow-sm">
        {num}
      </div>
      <div className="flex-1">
        <p className="text-sm text-gray-700">{title}</p>
        {code && (
          <pre className="mt-2 bg-gray-800 text-gray-200 text-xs p-3 rounded-lg overflow-x-auto">{code}</pre>
        )}
      </div>
    </div>
  );
}

function PythonDeploySteps({ framework, hasDb }: { framework: string; hasDb: boolean }) {
  return (
    <div className="space-y-4">
      <StepItem num={1} title="克隆仓库到服务器" code="git clone <仓库地址> /opt/app\ncd /opt/app" />
      <StepItem num={2} title="创建虚拟环境并安装依赖" code="python3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt" />
      {hasDb && <StepItem num={3} title="初始化数据库（如有迁移）" code="python manage.py migrate  # Django\nalembic upgrade head       # SQLAlchemy" />}
      <StepItem num={hasDb ? 4 : 3} title="启动生产服务" code={framework === 'FastAPI'
        ? 'gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000'
        : framework === 'Django'
        ? 'gunicorn config.wsgi:application --bind 0.0.0.0:8000'
        : 'gunicorn app:app --bind 0.0.0.0:8000'} />
      <StepItem num={hasDb ? 5 : 4} title="配置 Nginx 反向代理（可选）"
        code="server {\n  listen 80;\n  server_name example.com;\n  location / {\n    proxy_pass http://127.0.0.1:8000;\n  }\n}" />
    </div>
  );
}

function JSDeploySteps({ framework, hasDb }: { framework: string; hasDb: boolean }) {
  return (
    <div className="space-y-4">
      <StepItem num={1} title="克隆仓库到服务器" code="git clone <仓库地址> /opt/app\ncd /opt/app" />
      <StepItem num={2} title="安装依赖" code="npm ci --production" />
      {framework === 'Next.js' && <StepItem num={3} title="构建生产版本" code="npm run build" />}
      <StepItem num={framework === 'Next.js' ? 4 : 3} title="启动生产服务" code={framework === 'Next.js'
        ? 'npm start'
        : 'node app.js  # 或使用 PM2: pm2 start app.js --name myapp'} />
      <StepItem num={framework === 'Next.js' ? 5 : 4} title="配置反向代理" code="location / {\n  proxy_pass http://127.0.0.1:3000;\n  proxy_set_header Host $host;\n}" />
    </div>
  );
}

function GoDeploySteps({ framework, hasDb }: { framework: string; hasDb: boolean }) {
  return (
    <div className="space-y-4">
      <StepItem num={1} title="克隆仓库到服务器" code="git clone <仓库地址> /opt/app\ncd /opt/app" />
      <StepItem num={2} title="编译二进制" code="CGO_ENABLED=0 go build -ldflags='-s -w' -o app ." />
      <StepItem num={3} title="运行服务" code="./app  # 或使用 systemd 管理" />
      <StepItem num={4} title="配置 systemd 服务（推荐）"
        code={`[Unit]\nDescription=App Service\nAfter=network.target\n\n[Service]\nType=simple\nExecStart=/opt/app/app\nRestart=always\n\n[Install]\nWantedBy=multi-user.target`} />
    </div>
  );
}

function GenericDeploySteps() {
  return (
    <div className="space-y-4">
      <StepItem num={1} title="准备运行环境（安装所需运行时）" />
      <StepItem num={2} title="克隆代码到目标服务器" code="git clone <仓库地址> /opt/app" />
      <StepItem num={3} title="安装项目依赖" />
      <StepItem num={4} title="配置环境变量和配置文件" />
      <StepItem num={5} title="启动服务并使用进程管理器守护" />
      <StepItem num={6} title="配置反向代理和 SSL 证书" />
    </div>
  );
}
