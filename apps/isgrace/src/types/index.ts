export type MaterialType = 'textbook' | 'syllabus' | 'guide' | 'exam' | 'other';
export type ContextTier = 1 | 2 | 3;

export interface Material {
  id: string;
  name: string;
  type: MaterialType;
  path: string;
  uploadedAt: string;
  size: number;
  tier: ContextTier;
  content?: string;
  sourceUrl?: string; // set for URL-imported materials
}

export interface CourseInfo {
  name: string;
  language: string;
}

export interface Config {
  onboardingComplete: boolean;
  userName: string;
  subjects: Subject[];
  activeSubjectId: string | null;
  languagePreference: string;
  detectedLanguage: string;
  uiLanguage?: 'en' | 'zh';
  // Legacy fields kept for migration
  courseInfo?: CourseInfo;
  learningGoal?: string;
  uploadedMaterials?: Material[];
}

export type ModuleStage = 'not-started' | 'hs-explained' | 'college-explained' | 'quiz-ready';

export interface Module {
  id: string;
  title: string;
  textbookSectionRef: string;
  stage: ModuleStage;
  /** Verbatim excerpt of just this section, sliced from the textbook via anchor matching. Undefined if slicing failed — callers fall back to sending the whole textbook. */
  sectionText?: string;
  cheatsheetId?: string;
  testEntryId?: string;
}

export interface TestQuestion {
  id: string;
  type: 'multiple-choice' | 'essay' | 'code';
  question: string;
  options?: { id: string; text: string }[];
  correctAnswer?: string | string[];
  explanation?: string;   // shown after MC grading
  maxWords?: number;      // essay word limit
  rubric?: string;        // AI grading rubric for essay
  language?: string;      // code question: 'python' | 'javascript' etc.
  starterCode?: string;   // code question starter
  points: number;
}

export type LayoutMode = 'normal' | 'cowork';

export interface TestSession {
  id: string;
  moduleId?: string;
  questions: TestQuestion[];
  answers: Record<string, string | string[]>;
  submittedAt?: string;
  score?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'grace';
  content: string;
  timestamp: string;
  moduleId?: string;
}

export type OnboardingStep = 0 | 1 | 2;

export interface CheatsheetEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
}

export interface TestEntry {
  id: string;
  title: string;
  session: TestSession;
  createdAt: string;
}

/** A subject = one study session / course with its own materials */
export interface Subject {
  id: string;
  name: string;
  materials: Material[];
  courseInfo: CourseInfo;
  learningGoal: string;
  createdAt: string;
  chatMessages?: ChatMessage[];
  cheatsheets?: CheatsheetEntry[];
  tests?: TestEntry[];
  modules?: Module[];
  pinned?: boolean;
}

// ── Phase 2: LLM ──────────────────────────────────────────────────────────────

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export type LLMProvider =
  | 'openrouter'
  | 'openai'
  | 'anthropic'
  | 'gemini'
  | 'deepseek'
  | 'qwen'
  | 'kimi';

export interface LLMSettings {
  apiKey: string;
  model: string;
  temperature: number;
  provider: LLMProvider;
}

/** GET /api/settings response — in hosted mode apiKey is always redacted to ''. */
export interface SettingsResponse extends LLMSettings {
  mode: 'local' | 'hosted';
  hasDefaultKey: boolean;
}

export interface AuthMeResponse {
  authRequired: boolean;
  email: string | null;
}

export interface StreamChunk {
  id: string;       // stream session id
  delta: string;    // text fragment
  done: boolean;    // true on final chunk
  error?: string;   // set if streaming errored
}

export interface LLMModel {
  id: string;
  label: string;
  description: string;
  fast?: boolean;
  largeCtx?: boolean;   // model has a very large context window (≥200k tokens)
  ctxLabel?: string;    // display label e.g. "200k ctx"
  maxOutputTokens?: number; // per-model completion cap; falls back to a conservative default if unset
}

/** Per-provider config — shared between main process and renderer */
export interface LLMProviderConfig {
  id: LLMProvider;
  label: string;
  placeholder: string;    // API key input hint
  docsURL: string;        // URL to create key
  docsLabel: string;      // short display label for docsURL
  /** 'openai' = OpenAI-compatible SSE; 'anthropic' = Anthropic Messages API */
  apiFormat: 'openai' | 'anthropic';
  chatURL: string;        // full endpoint
  models: LLMModel[];
}

export const PROVIDER_CONFIGS: LLMProviderConfig[] = [
  {
    id: 'openrouter',
    label: 'OpenRouter',
    placeholder: 'sk-or-v1-…',
    docsURL: 'https://openrouter.ai/keys',
    docsLabel: 'openrouter.ai/keys',
    apiFormat: 'openai',
    chatURL: 'https://openrouter.ai/api/v1/chat/completions',
    models: [
      { id: 'tencent/hy3',                label: 'Tencent Hy3',       description: 'Hunyuan · Hackathon default', fast: true, largeCtx: true, ctxLabel: '256k ctx', maxOutputTokens: 32000 },
      { id: 'anthropic/claude-sonnet-4-5', label: 'Claude Sonnet 4.5', description: 'Best quality · Recommended', largeCtx: true, ctxLabel: '200k ctx' },
      { id: 'anthropic/claude-haiku-4-5',  label: 'Claude Haiku 4.5',  description: 'Fast & affordable', fast: true, largeCtx: true, ctxLabel: '200k ctx' },
      { id: 'openai/gpt-4o-mini',          label: 'GPT-4o mini',       description: 'OpenAI · Fast', fast: true },
      { id: 'google/gemini-2.0-flash-001', label: 'Gemini 2.0 Flash',  description: 'Google · Very fast', fast: true, largeCtx: true, ctxLabel: '1M ctx' },
      { id: 'deepseek/deepseek-chat',      label: 'DeepSeek V3',       description: 'Open-source · Efficient' },
    ],
  },
  {
    id: 'openai',
    label: 'OpenAI',
    placeholder: 'sk-…',
    docsURL: 'https://platform.openai.com/api-keys',
    docsLabel: 'platform.openai.com',
    apiFormat: 'openai',
    chatURL: 'https://api.openai.com/v1/chat/completions',
    models: [
      { id: 'gpt-4o',      label: 'GPT-4o',      description: 'Flagship model' },
      { id: 'gpt-4o-mini', label: 'GPT-4o mini', description: 'Fast & cost-effective', fast: true },
      { id: 'o1-mini',     label: 'o1 mini',      description: 'Reasoning model' },
    ],
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    placeholder: 'sk-ant-…',
    docsURL: 'https://console.anthropic.com/keys',
    docsLabel: 'console.anthropic.com',
    apiFormat: 'anthropic',
    chatURL: 'https://api.anthropic.com/v1/messages',
    models: [
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', description: 'Best quality · Recommended', largeCtx: true, ctxLabel: '200k ctx' },
      { id: 'claude-haiku-4-5',  label: 'Claude Haiku 4.5',  description: 'Fast & affordable', fast: true, largeCtx: true, ctxLabel: '200k ctx' },
    ],
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    placeholder: 'AIza…',
    docsURL: 'https://aistudio.google.com/apikey',
    docsLabel: 'aistudio.google.com',
    apiFormat: 'openai',
    chatURL: 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    models: [
      { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', description: 'Fastest', fast: true, largeCtx: true, ctxLabel: '1M ctx' },
      { id: 'gemini-1.5-pro',   label: 'Gemini 1.5 Pro',   description: 'Best quality', largeCtx: true, ctxLabel: '2M ctx' },
      { id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash', description: 'Fast & cheap', fast: true, largeCtx: true, ctxLabel: '1M ctx' },
    ],
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    placeholder: 'sk-…',
    docsURL: 'https://platform.deepseek.com/api_keys',
    docsLabel: 'platform.deepseek.com',
    apiFormat: 'openai',
    chatURL: 'https://api.deepseek.com/chat/completions',
    models: [
      { id: 'deepseek-chat',     label: 'DeepSeek V3', description: 'Latest · Recommended' },
      { id: 'deepseek-reasoner', label: 'DeepSeek R1', description: 'Reasoning model' },
    ],
  },
  {
    id: 'qwen',
    label: 'Qwen',
    placeholder: 'sk-…',
    docsURL: 'https://dashscope.console.aliyun.com/apiKey',
    docsLabel: 'dashscope.console.aliyun.com',
    apiFormat: 'openai',
    chatURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    models: [
      { id: 'qwen-max',   label: 'Qwen Max',   description: 'Best quality' },
      { id: 'qwen-plus',  label: 'Qwen Plus',  description: 'Balanced' },
      { id: 'qwen-turbo', label: 'Qwen Turbo', description: 'Fast & cost-effective', fast: true },
    ],
  },
  {
    id: 'kimi',
    label: 'Kimi',
    placeholder: 'sk-…',
    docsURL: 'https://platform.moonshot.cn/console/api-keys',
    docsLabel: 'platform.moonshot.cn',
    apiFormat: 'openai',
    chatURL: 'https://api.moonshot.cn/v1/chat/completions',
    models: [
      { id: 'moonshot-v1-8k',   label: 'Moonshot 8k',   description: 'Fast & efficient', fast: true },
      { id: 'moonshot-v1-32k',  label: 'Moonshot 32k',  description: 'Balanced' },
      { id: 'moonshot-v1-128k', label: 'Moonshot 128k', description: 'Long context' },
    ],
  },
];

export const DEFAULT_LLM_SETTINGS: LLMSettings = {
  apiKey: '',
  model: 'tencent/hy3',
  temperature: 0.7,
  provider: 'openrouter',
};

/** OpenRouter model list — convenience alias */
export const OPENROUTER_MODELS: LLMModel[] =
  PROVIDER_CONFIGS.find(p => p.id === 'openrouter')!.models;
