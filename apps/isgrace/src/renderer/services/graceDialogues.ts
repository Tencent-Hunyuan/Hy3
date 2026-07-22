export const dialogues = {
  en: {
    welcome: "Hi! I'm Grace, your learning companion.",
    welcomeSub: "I'll help you understand your materials deeply — not just memorize them.",
    uploadPrompt: "Upload your learning materials to get started.",
    uploadSub: "I'll analyze them and adapt my teaching to your needs.",
    coursePrompt: "What course are you studying?",
    goalPrompt: "What's your learning goal?",
    langPrompt: "How should I explain concepts to you?",
    onboardingDone: "Perfect! I'm ready to help you learn.",
    typing: "Grace is thinking...",
  },
  zh: {
    welcome: "嗨！我是 Grace，你的學習夥伴。",
    welcomeSub: "我會幫助你深入理解學習材料——不只是死記硬背。",
    uploadPrompt: "上傳你的學習材料開始吧。",
    uploadSub: "我會分析它們並根據你的需求調整教學方式。",
    coursePrompt: "你在學習哪門課程？",
    goalPrompt: "你的學習目標是什麼？",
    langPrompt: "你希望我怎麼為你解釋概念？",
    onboardingDone: "太好了！我已準備好幫助你學習。",
    typing: "Grace 正在思考...",
  },
  ja: {
    welcome: "こんにちは！私はGrace、あなたの学習パートナーです。",
    welcomeSub: "暗記だけでなく、材料を深く理解できるよう手伝います。",
    uploadPrompt: "学習資料をアップロードして始めましょう。",
    uploadSub: "資料を分析し、あなたのニーズに合わせて指導します。",
    coursePrompt: "何の授業を勉強していますか？",
    goalPrompt: "学習目標は何ですか？",
    langPrompt: "概念をどのように説明しましょうか？",
    onboardingDone: "完璧！あなたの学習をサポートする準備ができました。",
    typing: "Graceが考えています...",
  },
};

export type SupportedLang = keyof typeof dialogues;

export function getDialogue(lang: string): typeof dialogues.en {
  const key = lang.toLowerCase().slice(0, 2) as SupportedLang;
  return dialogues[key] ?? dialogues.en;
}

export const LEARNING_GOALS = {
  en: ['Pass the exam', 'Get an A grade', 'Deep understanding', 'Quick review', 'Custom...'],
  zh: ['通過考試', '拿到 A', '深入理解', '快速複習', '自訂...'],
  ja: ['試験に合格', '優を取る', '深く理解する', '素早く復習', 'カスタム...'],
};

export function getLearningGoals(lang: string): string[] {
  const key = lang.toLowerCase().slice(0, 2) as keyof typeof LEARNING_GOALS;
  return LEARNING_GOALS[key] ?? LEARNING_GOALS.en;
}

export const LANG_OPTIONS = [
  { label: 'English', value: 'en' },
  { label: '繁體中文', value: 'zh' },
  { label: '日本語', value: 'ja' },
  { label: 'English + 繁中', value: 'en+zh' },
  { label: 'English + 日本語', value: 'en+ja' },
];
