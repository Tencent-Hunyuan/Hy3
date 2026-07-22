import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import type { TestQuestion } from '../../types';
import { useLang } from '../i18n/useLang';

interface FeedbackEntry {
  correct: boolean;
  score: number;
  maxScore: number;
  explanation: string;
}
type FeedbackMap = Record<string, FeedbackEntry>;

export default function TestPanel() {
  const { activeTest, setActiveTest } = useStore();
  const { t } = useLang();
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [submitted, setSubmitted] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackMap>({});
  const [grading, setGrading] = useState(false);

  if (!activeTest) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3" style={{ backgroundColor: '#FEFEFE' }}>
        <p className="text-sm font-medium" style={{ color: '#1a1a1a' }}>{t.testNoTest}</p>
        <p className="text-xs" style={{ color: '#666666' }}>{t.testNoTestHint}</p>
      </div>
    );
  }

  const questions = activeTest.questions;
  const answeredCount = Object.keys(answers).length;

  function handleMCAnswer(qId: string, value: string) {
    setAnswers((a) => ({ ...a, [qId]: value }));
  }

  function handleEssayAnswer(qId: string, value: string) {
    setAnswers((a) => ({ ...a, [qId]: value }));
  }

  async function handleSubmit() {
    setGrading(true);
    const fb: FeedbackMap = {};

    await Promise.all(questions.map(async (q) => {
      const answer = answers[q.id];

      if (q.type === 'multiple-choice') {
        const correct = answer === q.correctAnswer;
        fb[q.id] = {
          correct,
          score: correct ? q.points : 0,
          maxScore: q.points,
          explanation: q.explanation ?? (correct ? 'Correct.' : `The correct answer is ${Array.isArray(q.correctAnswer) ? q.correctAnswer.join(', ').toUpperCase() : (q.correctAnswer ?? '').toUpperCase()}.`),
        };
        return;
      }

      // Essay or code — grade with LLM
      const rubric = q.rubric ?? q.explanation ?? 'Grade based on relevance and completeness.';
      try {
        const result = await api.llm.grade({
          questionId: q.id,
          type: q.type as 'essay' | 'code',
          question: q.question,
          rubric,
          answer: typeof answer === 'string' ? answer : '',
          points: q.points,
        });
        fb[q.id] = {
          correct: result.correct,
          score: result.score,
          maxScore: result.maxScore,
          explanation: result.explanation,
        };
      } catch {
        fb[q.id] = {
          correct: false,
          score: 0,
          maxScore: q.points,
          explanation: 'Grading failed — check your connection and try again.',
        };
      }
    }));

    setFeedback(fb);
    setGrading(false);
    setSubmitted(true);
  }

  const totalScore = submitted
    ? Object.values(feedback).reduce((s, f) => s + f.score, 0)
    : 0;
  const maxScore = questions.reduce((s, q) => s + q.points, 0);

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#FEFEFE' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 shrink-0"
        style={{ borderBottom: '1px solid #E8E0D5' }}
      >
        <div>
          <h2 className="text-sm font-semibold" style={{ color: '#1a1a1a' }}>{t.testTitle}</h2>
          <p className="text-xs" style={{ color: '#666666' }}>
            {submitted
              ? `${t.testReview} — ${totalScore}/${maxScore} pts`
              : t.testProgress(answeredCount, questions.length)}
          </p>
        </div>
        <button
          onClick={() => setActiveTest(undefined)}
          className="text-xs px-2 py-1 rounded"
          style={{ color: '#666666', border: '1px solid #E8E0D5' }}
        >
          {t.testClose}
        </button>
      </div>

      {/* Questions */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {questions.map((q, idx) => (
          <QuestionBlock
            key={q.id}
            question={q}
            index={idx}
            answer={answers[q.id]}
            submitted={submitted}
            feedback={feedback[q.id]}
            onMCAnswer={handleMCAnswer}
            onEssayAnswer={handleEssayAnswer}
          />
        ))}
      </div>

      {/* Submit / grading state */}
      {!submitted && (
        <div className="px-4 py-3 shrink-0" style={{ borderTop: '1px solid #E8E0D5' }}>
          <button
            onClick={handleSubmit}
            disabled={grading}
            className="w-full py-2 rounded-lg text-sm font-medium transition-opacity"
            style={{
              backgroundColor: grading ? '#E8E0D5' : '#F4D35E',
              color: grading ? '#888' : '#1a1a1a',
              cursor: grading ? 'not-allowed' : 'pointer',
            }}
          >
            {grading ? 'Grading…' : t.testSubmit}
          </button>
          {grading && (
            <p className="text-xs text-center mt-2" style={{ color: '#999' }}>
              Grading your answers — this may take a moment…
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Question block ─────────────────────────────────────────────────────────────

interface QuestionBlockProps {
  question: TestQuestion;
  index: number;
  answer?: string | string[];
  submitted: boolean;
  feedback?: FeedbackEntry;
  onMCAnswer: (id: string, v: string) => void;
  onEssayAnswer: (id: string, v: string) => void;
}

function QuestionBlock({ question, index, answer, submitted, feedback, onMCAnswer, onEssayAnswer }: QuestionBlockProps) {
  const hasFeedback = submitted && feedback !== undefined;
  const borderColor = hasFeedback ? (feedback.correct ? '#86efac' : '#fca5a5') : '#E8E0D5';

  return (
    <div
      className="rounded-lg p-4"
      style={{ backgroundColor: '#F8F5F0', border: `1px solid ${borderColor}` }}
    >
      <div className="flex items-start gap-2 mb-3">
        <span
          className="text-xs font-semibold shrink-0 mt-0.5 w-5 h-5 rounded-full flex items-center justify-center"
          style={{ backgroundColor: '#F4D35E', color: '#1a1a1a' }}
        >
          {index + 1}
        </span>
        <p className="text-sm font-medium leading-relaxed" style={{ color: '#1a1a1a', lineHeight: 1.6 }}>
          {question.question}
        </p>
      </div>

      {question.type === 'multiple-choice' && question.options && (
        <div className="space-y-2 ml-7">
          {question.options.map((opt) => {
            const isSelected = answer === opt.id;
            const isCorrect = opt.id === question.correctAnswer;
            let bg = isSelected ? '#FEF9C3' : 'transparent';
            if (hasFeedback && isCorrect) bg = '#dcfce7';
            if (hasFeedback && isSelected && !isCorrect) bg = '#fee2e2';

            return (
              <label
                key={opt.id}
                className="flex items-start gap-3 p-2.5 rounded-lg cursor-pointer"
                style={{ border: '1px solid #E8E0D5', backgroundColor: bg }}
              >
                <input
                  type="radio"
                  name={question.id}
                  value={opt.id}
                  checked={isSelected}
                  onChange={() => onMCAnswer(question.id, opt.id)}
                  disabled={submitted}
                  className="mt-0.5"
                />
                <span className="text-sm leading-relaxed" style={{ color: '#1a1a1a', lineHeight: 1.6 }}>
                  {opt.text}
                </span>
                {hasFeedback && isCorrect && (
                  <span className="ml-auto text-xs font-medium shrink-0" style={{ color: '#166534' }}>✓</span>
                )}
              </label>
            );
          })}
        </div>
      )}

      {(question.type === 'essay' || question.type === 'code') && (
        <div className="ml-7">
          <textarea
            value={typeof answer === 'string' ? answer : ''}
            onChange={(e) => onEssayAnswer(question.id, e.target.value)}
            disabled={submitted}
            rows={4}
            className="w-full rounded-lg px-3 py-2 text-sm outline-none resize-y"
            style={{ border: '1px solid #E8E0D5', backgroundColor: '#FEFEFE', color: '#1a1a1a', lineHeight: 1.6 }}
            placeholder={question.type === 'code' ? 'Write your code here…' : 'Write your answer here…'}
          />
          <p className="text-xs mt-1 text-right" style={{ color: '#9ca3af' }}>
            {typeof answer === 'string' ? answer.trim().split(/\s+/).filter(Boolean).length : 0} words
          </p>
        </div>
      )}

      {hasFeedback && (
        <FeedbackBlock feedback={feedback} question={question} />
      )}
    </div>
  );
}

// ── Feedback block ─────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mdFeedback: Record<string, React.ComponentType<any>> = {
  p: ({ children }: { children: React.ReactNode }) => (
    <p style={{ margin: '0 0 8px', lineHeight: 1.7 }}>{children}</p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul style={{ margin: '0 0 8px', paddingLeft: 18, lineHeight: 1.7 }}>{children}</ul>
  ),
  ol: ({ children }: { children: React.ReactNode }) => (
    <ol style={{ margin: '0 0 8px', paddingLeft: 18, lineHeight: 1.7 }}>{children}</ol>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li style={{ margin: '2px 0' }}>{children}</li>
  ),
  strong: ({ children }: { children: React.ReactNode }) => (
    <strong style={{ fontWeight: 700 }}>{children}</strong>
  ),
  code: ({ children }: { children: React.ReactNode }) => (
    <code style={{ backgroundColor: 'rgba(0,0,0,0.08)', borderRadius: 3, padding: '1px 4px', fontSize: '0.9em' }}>{children}</code>
  ),
};

function FeedbackBlock({ feedback, question }: { feedback: FeedbackEntry; question: TestQuestion }) {
  const [expanded, setExpanded] = useState(false);
  const isEssayOrCode = question.type === 'essay' || question.type === 'code';

  return (
    <div
      className="mt-3 ml-7 px-3 py-2.5 rounded-lg text-xs leading-relaxed"
      style={{
        backgroundColor: feedback.correct ? '#f0fdf4' : '#fef2f2',
        color: feedback.correct ? '#166534' : '#991b1b',
        border: `1px solid ${feedback.correct ? '#bbf7d0' : '#fecaca'}`,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold">
          {feedback.correct ? '✓ Correct' : '✗ Incorrect'}
          {isEssayOrCode && ` — ${feedback.score}/${feedback.maxScore} pts`}
        </span>
        {isEssayOrCode && (
          <button
            onClick={() => setExpanded(e => !e)}
            className="text-xs underline opacity-70 hover:opacity-100 shrink-0"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontFamily: 'inherit' }}
          >
            {expanded ? 'Hide feedback' : 'See feedback'}
          </button>
        )}
      </div>

      {/* MC: always show explanation */}
      {question.type === 'multiple-choice' && (
        <div className="mt-1.5" style={{ opacity: 0.9 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdFeedback}>
            {feedback.explanation}
          </ReactMarkdown>
        </div>
      )}

      {/* Essay/code: expandable */}
      {isEssayOrCode && expanded && (
        <div className="mt-2 pt-2" style={{ borderTop: `1px solid ${feedback.correct ? '#bbf7d0' : '#fecaca'}`, opacity: 0.95 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdFeedback}>
            {feedback.explanation}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
