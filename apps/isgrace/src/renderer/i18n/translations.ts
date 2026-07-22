export type Lang = 'en' | 'zh';

export interface Translations {
  // ── Sidebar ────────────────────────────────────────────────────────────────
  sidebarSubjects: string;
  sidebarNewSubject: string;
  sidebarNoSubjects: string;
  sidebarSettings: string;
  sidebarCollapse: string;
  sidebarExpand: string;

  // ── Chat – home ────────────────────────────────────────────────────────────
  chatGreeting: (name?: string) => string;
  chatSubtitle: string;
  chatSuggestions: { emoji: string; label: string; desc: string }[];
  chatPlaceholder: string;
  chatPlaceholderNoKey: string;
  chatPlaceholderSetup: string;
  chatDropToUpload: string;
  chatUploadTitle: string;
  chatNoApiKeyBold: string;
  chatNoApiKeySuffix: string;

  // ── Setup flow ─────────────────────────────────────────────────────────────
  setupStepLabels: [string, string, string];
  setupStep1Q: string;
  setupStep1Hint: string;
  setupStep2Q: string;
  setupStep3Q: string;
  setupStep3OtherPlaceholder: string;
  setupSkip: string;
  setupNext: string;
  setupStart: string;
  setupUpload: string;
  setupMatTypes: { id: string; emoji: string; label: string }[];
  setupPurposeOpts: { id: string; emoji: string; label: string }[];
  // Step 3 language options are always bilingual (choosing AI reply language)
  setupLangOpts: { id: string; emoji: string; label: string; sub: string }[];

  // ── Resource panel ─────────────────────────────────────────────────────────
  resMaterials: string;
  resAdd: string;
  resDropHint: string;
  resGenerated: string;
  resCheatsheet: string;
  resStudyGuide: string;
  resTest: (n: number) => string;

  // ── Settings ───────────────────────────────────────────────────────────────
  settingsTitle: string;
  settingsSubtitle: string;
  settingsApiType: string;
  settingsApiKey: string;
  settingsModel: string;
  settingsTemp: string;
  settingsTempPrecise: string;
  settingsTempBalanced: string;
  settingsTempCreative: string;
  settingsTestConn: string;
  settingsTesting: string;
  settingsConnected: string;
  settingsSave: string;
  settingsSaving: string;
  settingsGetKey: string;
  settingsLanguage: string;

  // ── Login ──────────────────────────────────────────────────────────────────
  loginTitle: string;
  loginSubtitle: string;
  loginPlaceholder: string;
  loginButton: string;
  loginSubmitting: string;
  loginError: string;

  // ── Test panel ─────────────────────────────────────────────────────────────
  testTitle: string;
  testNoTest: string;
  testNoTestHint: string;
  testReview: string;
  testProgress: (answered: number, total: number) => string;
  testClose: string;
  testSubmit: string;
}

// ── English ────────────────────────────────────────────────────────────────────

const en: Translations = {
  sidebarSubjects: 'Subjects',
  sidebarNewSubject: 'New Subject',
  sidebarNoSubjects: 'No subjects yet. Upload files to get started.',
  sidebarSettings: 'Settings',
  sidebarCollapse: 'Collapse sidebar',
  sidebarExpand: 'Expand sidebar',

  chatGreeting: (name) => name ? `Hello, ${name}! Let's start learning` : `Hello! Let's start learning`,
  chatSubtitle: 'Tell me what you\'re studying and Grace will help you master it.',
  chatSuggestions: [
    { emoji: '🎓', label: 'Start a new course', desc: 'Upload your textbook, notes, or a link. Grace will take you deep, chapter by chapter.' },
    { emoji: '📝', label: 'Study for an exam', desc: 'Have a study guide or past paper? Grace will drill you on exactly what matters.' },
    { emoji: '💡', label: 'Ask a question', desc: 'Already have materials uploaded? Jump straight in with any question.' },
  ],
  chatPlaceholder: 'Ask Grace…',
  chatPlaceholderNoKey: 'Add API key to start…',
  chatPlaceholderSetup: 'Complete the setup above first…',
  chatDropToUpload: 'Drop to upload',
  chatUploadTitle: 'Upload materials',
  chatNoApiKeyBold: 'Add your API key',
  chatNoApiKeySuffix: ' to chat with Grace →',

  setupStepLabels: ['Choose materials', 'Purpose', 'Language preference'],
  setupStep1Q: 'Before we begin, what study materials do you have?',
  setupStep1Hint: 'Check the types below, upload files, or skip for now.',
  setupStep2Q: 'What\'s your main goal for studying this?',
  setupStep3Q: 'Which language would you like me to explain in?',
  setupStep3OtherPlaceholder: 'Enter your preferred language…',
  setupSkip: 'Skip',
  setupNext: 'Continue →',
  setupStart: 'Start learning →',
  setupUpload: 'Upload ↑',
  setupMatTypes: [
    { id: 'textbook',  emoji: '📚', label: 'Textbook' },
    { id: 'syllabus',  emoji: '📋', label: 'Syllabus' },
    { id: 'module',    emoji: '📑', label: 'Module notes / Slides' },
    { id: 'guide',     emoji: '📖', label: 'Exam study guide' },
    { id: 'practice',  emoji: '✏️', label: 'Practice exam' },
    { id: 'link',      emoji: '🔗', label: 'Material from a link' },
  ],
  setupPurposeOpts: [
    { id: 'university', emoji: '🎓', label: 'University course' },
    { id: 'personal',   emoji: '💡', label: 'Personal interest / Self-study' },
  ],
  setupLangOpts: [
    { id: 'english',   emoji: '🌏', label: 'English',                          sub: '英文' },
    { id: 'chinese',   emoji: '💬', label: '中文 (Chinese)',                   sub: 'Chinese' },
    { id: 'bilingual', emoji: '🔤', label: 'Bilingual — Chinese + English terms', sub: '中英双语' },
    { id: 'other',     emoji: '✏️', label: 'Other',                            sub: '其他' },
  ],

  resMaterials: 'Materials',
  resAdd: '+ Add',
  resDropHint: 'Drop files or click Add',
  resGenerated: 'Generated',
  resCheatsheet: 'Cheatsheet',
  resStudyGuide: 'Study Guide',
  resTest: (n) => `Test · ${n} ch.`,

  settingsTitle: 'Settings',
  settingsSubtitle: 'LLM provider & model',
  settingsApiType: 'API Type',
  settingsApiKey: 'API Key',
  settingsModel: 'Model',
  settingsTemp: 'Temperature',
  settingsTempPrecise: 'Precise',
  settingsTempBalanced: 'Balanced',
  settingsTempCreative: 'Creative',
  settingsTestConn: 'Test Connection',
  settingsTesting: 'Testing…',
  settingsConnected: 'Connected successfully ✓',
  settingsSave: 'Save Settings',
  settingsSaving: 'Saving…',
  settingsGetKey: 'Get your API key from',
  settingsLanguage: 'App Language',

  loginTitle: 'Welcome to isGrace',
  loginSubtitle: 'Enter your email to continue',
  loginPlaceholder: 'you@example.com',
  loginButton: 'Continue',
  loginSubmitting: 'Continuing…',
  loginError: 'Please enter a valid email address.',

  testTitle: 'Test',
  testNoTest: 'No active test',
  testNoTestHint: 'Ask Grace to generate a test for a chapter.',
  testReview: 'Review your answers',
  testProgress: (a, t) => `${a}/${t} answered`,
  testClose: 'Close',
  testSubmit: 'Submit',
};

// ── Simplified Chinese ─────────────────────────────────────────────────────────

const zh: Translations = {
  sidebarSubjects: '科目',
  sidebarNewSubject: '新建科目',
  sidebarNoSubjects: '暂无科目，上传文件开始学习。',
  sidebarSettings: '设置',
  sidebarCollapse: '收起侧边栏',
  sidebarExpand: '展开侧边栏',

  chatGreeting: (name) => name ? `你好，${name}！让我们开始学习吧` : '你好！让我们开始学习吧',
  chatSubtitle: '告诉我你在学什么，Grace 会帮你高效掌握。',
  chatSuggestions: [
    { emoji: '🎓', label: '开始学习新课程', desc: '上传教材、笔记或链接，Grace 会带你逐章深入学习。' },
    { emoji: '📝', label: '备考练习', desc: '有考试大纲或历年真题？Grace 会针对重点帮你备考。' },
    { emoji: '💡', label: '直接提问', desc: '已经上传了材料？有任何问题都可以直接问 Grace。' },
  ],
  chatPlaceholder: '和 Grace 说话…',
  chatPlaceholderNoKey: '请先添加 API 密钥…',
  chatPlaceholderSetup: '请先完成上方的设置…',
  chatDropToUpload: '松开以上传',
  chatUploadTitle: '上传学习资料',
  chatNoApiKeyBold: '添加 API 密钥',
  chatNoApiKeySuffix: '开始和 Grace 对话 →',

  setupStepLabels: ['选择学习材料', '学习目的', '语言偏好'],
  setupStep1Q: '在我们开始之前，你有哪些学习材料？',
  setupStep1Hint: '勾选后可以直接上传，也可以跳过稍后再传。',
  setupStep2Q: '你学习这个的主要目的是？',
  setupStep3Q: '你希望我用什么语言来解释？',
  setupStep3OtherPlaceholder: '请输入你希望使用的语言…',
  setupSkip: '跳过',
  setupNext: '继续 →',
  setupStart: '开始学习 →',
  setupUpload: '上传 ↑',
  setupMatTypes: [
    { id: 'textbook',  emoji: '📚', label: '教材 / Textbook' },
    { id: 'syllabus',  emoji: '📋', label: '课程大纲 / Syllabus' },
    { id: 'module',    emoji: '📑', label: '讲义 / Slides' },
    { id: 'guide',     emoji: '📖', label: '考试指南 / Study guide' },
    { id: 'practice',  emoji: '✏️', label: '练习题 / Practice exam' },
    { id: 'link',      emoji: '🔗', label: '链接资料 / Material from link' },
  ],
  setupPurposeOpts: [
    { id: 'university', emoji: '🎓', label: '大学课程学习' },
    { id: 'personal',   emoji: '💡', label: '个人兴趣 / 自学' },
  ],
  setupLangOpts: [
    { id: 'english',   emoji: '🌏', label: 'English',      sub: '英文' },
    { id: 'chinese',   emoji: '💬', label: '中文',         sub: 'Chinese' },
    { id: 'bilingual', emoji: '🔤', label: '中文解释，英文专业术语', sub: 'Chinese + English terms' },
    { id: 'other',     emoji: '✏️', label: '其他',         sub: 'Other' },
  ],

  resMaterials: '资料',
  resAdd: '+ 添加',
  resDropHint: '拖入文件或点击添加',
  resGenerated: '已生成',
  resCheatsheet: '知识清单',
  resStudyGuide: '学习指南',
  resTest: (n) => `练习测试 · ${n} 章`,

  settingsTitle: '设置',
  settingsSubtitle: 'AI 模型配置',
  settingsApiType: '接口类型',
  settingsApiKey: 'API 密钥',
  settingsModel: '模型',
  settingsTemp: '创造性',
  settingsTempPrecise: '精准',
  settingsTempBalanced: '平衡',
  settingsTempCreative: '创意',
  settingsTestConn: '测试连接',
  settingsTesting: '测试中…',
  settingsConnected: '连接成功 ✓',
  settingsSave: '保存设置',
  settingsSaving: '保存中…',
  settingsGetKey: '获取 API 密钥：',
  settingsLanguage: '界面语言',

  loginTitle: '欢迎使用 isGrace',
  loginSubtitle: '输入邮箱继续',
  loginPlaceholder: 'you@example.com',
  loginButton: '继续',
  loginSubmitting: '登录中…',
  loginError: '请输入有效的邮箱地址。',

  testTitle: '练习测试',
  testNoTest: '暂无测试',
  testNoTestHint: '让 Grace 为章节生成练习测试。',
  testReview: '查看答案',
  testProgress: (a, t) => `已答 ${a}/${t}`,
  testClose: '关闭',
  testSubmit: '提交',
};

export const TRANSLATIONS: Record<Lang, Translations> = { en, zh };
