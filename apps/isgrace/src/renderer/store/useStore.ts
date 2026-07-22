import { create } from 'zustand';
import type {
  Material, MaterialType, CourseInfo, ChatMessage, TestSession, Module,
  OnboardingStep, Config, LLMSettings, SettingsResponse, AuthMeResponse,
  Subject, LayoutMode, CheatsheetEntry, TestEntry,
} from '../../types';
import { DEFAULT_LLM_SETTINGS } from '../../types';
import type { Lang } from '../i18n/translations';

const LOCAL_KEY_OVERRIDE_STORAGE_KEY = 'isgrace:localKeyOverride';

function loadLocalKeyOverride(): LLMSettings | null {
  try {
    const raw = localStorage.getItem(LOCAL_KEY_OVERRIDE_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as LLMSettings) : null;
  } catch { return null; }
}

function computeLlmReady(mode: 'local' | 'hosted', apiKey: string, hasDefaultKey: boolean, localOverride: LLMSettings | null): boolean {
  if (mode === 'hosted') return hasDefaultKey || !!localOverride?.apiKey;
  return !!apiKey;
}

interface AppState {
  // Onboarding
  onboardingComplete: boolean;
  onboardingStep: OnboardingStep;

  // User
  userName: string;

  // Subjects (multi-course support)
  subjects: Subject[];
  activeSubjectId: string | null;
  sidebarOpen: boolean;

  // Active subject's flat state
  courseInfo: CourseInfo;
  learningGoal: string;
  languagePreference: string;
  detectedLanguage: string;
  uploadedMaterials: Material[];
  studyGuide: string;
  cheatsheets: CheatsheetEntry[];

  // Chat
  chatMessages: ChatMessage[];
  isGraceTyping: boolean;

  // Modules & Tests
  modules: Module[];
  activeModuleId: string | null;
  tests: TestEntry[];
  activeTest: TestSession | undefined;

  // UI
  activePanel: 'folder' | 'test';
  settingsOpen: boolean;
  layoutMode: LayoutMode;

  // LLM
  llmSettings: LLMSettings;
  llmReady: boolean;
  settingsMode: 'local' | 'hosted';
  hasDefaultKey: boolean;
  localKeyOverride: LLMSettings | null;

  // Auth (hosted-mode email gate — no-op fields in local mode)
  authChecked: boolean;
  authRequired: boolean;
  authEmail: string | null;

  // UI Language
  uiLanguage: Lang;

  // ── Actions ──────────────────────────────────────────────────────────────

  setUiLanguage: (lang: Lang) => void;
  loadFromConfig: (config: Config) => void;
  loadLLMSettings: (settings: SettingsResponse) => void;
  saveLLMSettings: (settings: Partial<LLMSettings>) => void;
  setLocalKeyOverride: (settings: LLMSettings | null) => void;
  loadAuth: (me: AuthMeResponse) => void;

  setOnboardingComplete: (val: boolean) => void;
  setOnboardingStep: (step: OnboardingStep) => void;
  setUserName: (name: string) => void;
  setCourseInfo: (info: Partial<CourseInfo>) => void;
  setLearningGoal: (goal: string) => void;
  setLanguagePreference: (lang: string) => void;
  setDetectedLanguage: (lang: string) => void;

  switchSubject: (id: string) => void;
  createNewSubject: () => void;
  deleteSubject: (id: string) => void;
  togglePinSubject: (id: string) => void;
  setSidebarOpen: (val: boolean) => void;

  addMaterial: (m: Material) => void;
  removeMaterial: (id: string) => void;
  updateMaterialType: (id: string, type: MaterialType) => void;
  setStudyGuide: (c: string) => void;
  addCheatsheet: (entry: CheatsheetEntry) => void;

  addChatMessage: (msg: ChatMessage) => void;
  updateLastMessage: (id: string, content: string) => void;
  clearChatMessages: () => void;
  setGraceTyping: (val: boolean) => void;

  setModules: (modules: Module[]) => void;
  updateModule: (id: string, patch: Partial<Module>) => void;
  setActiveModuleId: (id: string | null) => void;
  addTest: (entry: TestEntry) => void;
  setActiveTest: (t?: TestSession) => void;
  setActivePanel: (p: 'folder' | 'test') => void;
  setSettingsOpen: (val: boolean) => void;
  setLayoutMode: (mode: LayoutMode) => void;

  reset: () => void;
}

const INIT: Omit<AppState,
  'loadFromConfig' | 'loadLLMSettings' | 'saveLLMSettings' | 'setLocalKeyOverride' | 'loadAuth' |
  'setOnboardingComplete' | 'setOnboardingStep' | 'setUserName' |
  'setCourseInfo' | 'setLearningGoal' | 'setLanguagePreference' | 'setDetectedLanguage' |
  'switchSubject' | 'createNewSubject' | 'deleteSubject' | 'togglePinSubject' | 'setSidebarOpen' |
  'addMaterial' | 'removeMaterial' | 'updateMaterialType' | 'setStudyGuide' | 'addCheatsheet' |
  'addChatMessage' | 'updateLastMessage' | 'clearChatMessages' | 'setGraceTyping' |
  'setModules' | 'updateModule' | 'setActiveModuleId' | 'addTest' | 'setActiveTest' | 'setActivePanel' | 'setSettingsOpen' | 'reset' |
  'setUiLanguage' | 'setLayoutMode'
> = {
  onboardingComplete: false,
  onboardingStep: 0 as OnboardingStep,
  userName: '',
  subjects: [],
  activeSubjectId: null,
  sidebarOpen: true,
  courseInfo: { name: '', language: 'en' },
  learningGoal: '',
  languagePreference: '',
  detectedLanguage: 'en',
  uploadedMaterials: [],
  studyGuide: '',
  cheatsheets: [],
  chatMessages: [],
  isGraceTyping: false,
  modules: [],
  activeModuleId: null,
  tests: [],
  activeTest: undefined,
  activePanel: 'folder',
  settingsOpen: false,
  layoutMode: 'normal' as LayoutMode,
  llmSettings: { ...DEFAULT_LLM_SETTINGS },
  llmReady: false,
  settingsMode: 'local',
  hasDefaultKey: false,
  localKeyOverride: loadLocalKeyOverride(),
  authChecked: false,
  authRequired: false,
  authEmail: null,
  uiLanguage: 'en' as Lang,
};

function mkid(): string {
  return `sub_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`;
}

export const useStore = create<AppState>((set) => ({
  ...INIT,

  loadFromConfig: (config) => set(() => {
    let subjects = config.subjects ?? [];
    let activeSubjectId = config.activeSubjectId ?? null;

    // Migrate old single-course configs to subjects
    if (subjects.length === 0 && (config.uploadedMaterials?.length ?? 0) > 0) {
      const legacy: Subject = {
        id: 'sub_legacy',
        name: config.courseInfo?.name || 'My Course',
        materials: config.uploadedMaterials ?? [],
        courseInfo: config.courseInfo ?? { name: '', language: 'en' },
        learningGoal: config.learningGoal ?? '',
        createdAt: new Date().toISOString(),
      };
      subjects = [legacy];
      activeSubjectId = 'sub_legacy';
    }

    const active = subjects.find(s => s.id === activeSubjectId);
    return {
      onboardingComplete: config.onboardingComplete ?? false,
      userName: config.userName ?? '',
      subjects,
      activeSubjectId,
      courseInfo: active?.courseInfo ?? { name: '', language: 'en' },
      learningGoal: active?.learningGoal ?? '',
      uploadedMaterials: active?.materials ?? [],
      chatMessages: active?.chatMessages ?? [],
      modules: active?.modules ?? [],
      languagePreference: config.languagePreference ?? '',
      detectedLanguage: config.detectedLanguage ?? 'en',
      ...(config.uiLanguage ? { uiLanguage: config.uiLanguage } : {}),
    };
  }),

  setUiLanguage: (lang) => set({ uiLanguage: lang }),

  loadLLMSettings: (settings) => set((s) => ({
    llmSettings: settings,
    settingsMode: settings.mode,
    hasDefaultKey: settings.hasDefaultKey,
    llmReady: computeLlmReady(settings.mode, settings.apiKey, settings.hasDefaultKey, s.localKeyOverride),
  })),

  saveLLMSettings: (partial) => set((s) => {
    const merged = { ...s.llmSettings, ...partial };
    return { llmSettings: merged, llmReady: computeLlmReady(s.settingsMode, merged.apiKey, s.hasDefaultKey, s.localKeyOverride) };
  }),

  setLocalKeyOverride: (settings) => set((s) => {
    if (settings) localStorage.setItem(LOCAL_KEY_OVERRIDE_STORAGE_KEY, JSON.stringify(settings));
    else localStorage.removeItem(LOCAL_KEY_OVERRIDE_STORAGE_KEY);
    return {
      localKeyOverride: settings,
      llmReady: computeLlmReady(s.settingsMode, s.llmSettings.apiKey, s.hasDefaultKey, settings),
    };
  }),

  loadAuth: (me) => set({ authChecked: true, authRequired: me.authRequired, authEmail: me.email }),

  setOnboardingComplete: (val) => set({ onboardingComplete: val }),
  setOnboardingStep: (step) => set({ onboardingStep: step }),
  setUserName: (name) => set({ userName: name }),
  setCourseInfo: (info) => set((s) => ({ courseInfo: { ...s.courseInfo, ...info } })),
  setLearningGoal: (goal) => set({ learningGoal: goal }),
  setLanguagePreference: (lang) => set({ languagePreference: lang }),
  setDetectedLanguage: (lang) => set({ detectedLanguage: lang }),

  switchSubject: (id) => set((s) => {
    // Save current chat messages into the departing subject first
    const subjectsWithSaved = s.activeSubjectId
      ? s.subjects.map(sub =>
          sub.id === s.activeSubjectId
            ? { ...sub, chatMessages: s.chatMessages }
            : sub
        )
      : s.subjects;

    const subject = subjectsWithSaved.find(sub => sub.id === id);
    if (!subject) return {};
    return {
      subjects: subjectsWithSaved,
      activeSubjectId: id,
      uploadedMaterials: subject.materials,
      courseInfo: subject.courseInfo,
      learningGoal: subject.learningGoal,
      chatMessages: subject.chatMessages ?? [],
      modules: subject.modules ?? [],
      activeModuleId: null,
      studyGuide: '',
      cheatsheets: subject.cheatsheets ?? [],
      tests: subject.tests ?? [],
      activeTest: undefined,
    };
  }),

  createNewSubject: () => set({
    activeSubjectId: null,
    uploadedMaterials: [],
    chatMessages: [],
    modules: [],
    activeModuleId: null,
    studyGuide: '',
    cheatsheets: [],
    tests: [],
    activeTest: undefined,
    courseInfo: { name: '', language: 'en' },
    learningGoal: '',
  }),

  deleteSubject: (id) => set((s) => {
    const subjects = s.subjects.filter(sub => sub.id !== id);
    if (s.activeSubjectId !== id) return { subjects };
    // Deleted the active subject — switch to most recent remaining, or null
    const next = subjects[subjects.length - 1];
    if (!next) return { subjects, activeSubjectId: null, uploadedMaterials: [], chatMessages: [], modules: [], activeModuleId: null, studyGuide: '', cheatsheets: [], tests: [], activeTest: undefined, courseInfo: { name: '', language: 'en' }, learningGoal: '' };
    return {
      subjects,
      activeSubjectId: next.id,
      uploadedMaterials: next.materials,
      courseInfo: next.courseInfo,
      learningGoal: next.learningGoal,
      chatMessages: next.chatMessages ?? [],
      modules: next.modules ?? [],
      activeModuleId: null,
      studyGuide: '',
      cheatsheets: next.cheatsheets ?? [],
      tests: next.tests ?? [],
      activeTest: undefined,
    };
  }),

  togglePinSubject: (id) => set((s) => ({
    subjects: s.subjects.map(sub =>
      sub.id === id ? { ...sub, pinned: !sub.pinned } : sub
    ),
  })),

  setSidebarOpen: (val) => set({ sidebarOpen: val }),

  addMaterial: (m) => set((s) => {
    if (s.activeSubjectId === null) {
      const id = mkid();
      const name = m.name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ');
      const newSub: Subject = {
        id, name, materials: [m],
        courseInfo: { name, language: 'en' },
        learningGoal: '',
        createdAt: new Date().toISOString(),
      };
      return {
        subjects: [...s.subjects, newSub],
        activeSubjectId: id,
        uploadedMaterials: [m],
        courseInfo: { name, language: 'en' },
      };
    }
    const newMaterials = [...s.uploadedMaterials, m];
    const subjects = s.subjects.map(sub =>
      sub.id === s.activeSubjectId ? { ...sub, materials: newMaterials } : sub
    );
    return { subjects, uploadedMaterials: newMaterials };
  }),

  removeMaterial: (id) => set((s) => {
    const newMaterials = s.uploadedMaterials.filter(m => m.id !== id);
    const subjects = s.subjects.map(sub =>
      sub.id === s.activeSubjectId ? { ...sub, materials: newMaterials } : sub
    );
    return { subjects, uploadedMaterials: newMaterials };
  }),

  updateMaterialType: (id, type) => set((s) => {
    const newMaterials = s.uploadedMaterials.map(m => m.id === id ? { ...m, type } : m);
    const subjects = s.subjects.map(sub =>
      sub.id === s.activeSubjectId ? { ...sub, materials: newMaterials } : sub
    );
    return { subjects, uploadedMaterials: newMaterials };
  }),

  setStudyGuide: (c) => set({ studyGuide: c }),
  addCheatsheet: (entry) => set((s) => {
    const cheatsheets = [...s.cheatsheets, entry];
    const subjects = s.activeSubjectId
      ? s.subjects.map(sub =>
          sub.id === s.activeSubjectId ? { ...sub, cheatsheets } : sub
        )
      : s.subjects;
    return { cheatsheets, subjects };
  }),

  addChatMessage: (msg) => set((s) => {
    const newMessages = [...s.chatMessages, msg];
    // Sync into subjects so auto-save in App.tsx picks it up
    const subjects = s.activeSubjectId
      ? s.subjects.map(sub =>
          sub.id === s.activeSubjectId ? { ...sub, chatMessages: newMessages } : sub
        )
      : s.subjects;
    return { chatMessages: newMessages, subjects };
  }),

  // Note: updateLastMessage is called for every streaming token — do NOT sync subjects here
  updateLastMessage: (id, content) => set((s) => ({
    chatMessages: s.chatMessages.map((m) => m.id === id ? { ...m, content } : m),
  })),

  clearChatMessages: () => set((s) => {
    const subjects = s.activeSubjectId
      ? s.subjects.map(sub =>
          sub.id === s.activeSubjectId ? { ...sub, chatMessages: [] } : sub
        )
      : s.subjects;
    return { chatMessages: [], subjects };
  }),

  // Sync subjects when stream ends (typing → false), so the completed response is persisted
  setGraceTyping: (val) => set((s) => {
    if (!val && s.activeSubjectId) {
      const subjects = s.subjects.map(sub =>
        sub.id === s.activeSubjectId ? { ...sub, chatMessages: s.chatMessages } : sub
      );
      return { isGraceTyping: false, subjects };
    }
    return { isGraceTyping: val };
  }),

  setModules: (modules) => set((s) => {
    const subjects = s.activeSubjectId
      ? s.subjects.map(sub => sub.id === s.activeSubjectId ? { ...sub, modules } : sub)
      : s.subjects;
    return { modules, subjects };
  }),

  updateModule: (id, patch) => set((s) => {
    const modules = s.modules.map(m => m.id === id ? { ...m, ...patch } : m);
    const subjects = s.activeSubjectId
      ? s.subjects.map(sub => sub.id === s.activeSubjectId ? { ...sub, modules } : sub)
      : s.subjects;
    return { modules, subjects };
  }),

  setActiveModuleId: (id) => set({ activeModuleId: id }),

  addTest: (entry) => set((s) => {
    const tests = [...s.tests, entry];
    const subjects = s.activeSubjectId
      ? s.subjects.map(sub =>
          sub.id === s.activeSubjectId ? { ...sub, tests } : sub
        )
      : s.subjects;
    return { tests, subjects };
  }),

  setActiveTest: (t) => set({ activeTest: t, activePanel: t ? 'test' : 'folder', layoutMode: t ? 'cowork' : 'normal' }),
  setActivePanel: (p) => set({ activePanel: p }),
  setSettingsOpen: (val) => set({ settingsOpen: val }),
  setLayoutMode: (mode) => set({ layoutMode: mode }),

  reset: () => set({ ...INIT }),
}));
