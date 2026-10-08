import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";
type Question = {
  id: number;
  question_type: string;
  prompt: string;
  options: string[];
  source: { source_type: string; section_number: string; source_page: number };
};
type Attempt = { id: number; score: number; total_questions: number; passed: number; created_at: string };
type Result = {
  score: number;
  passed: boolean;
  total_questions: number;
  feedback: { question_id: number; correct: boolean; feedback: string }[];
};

class QuizRequestError extends Error {
  canRetryCreation: boolean;
  constructor(message: string, canRetryCreation = false) {
    super(message);
    this.canRetryCreation = canRetryCreation;
  }
}

async function request(path: string, body?: object) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new QuizRequestError(
      typeof data.detail === "string" ? data.detail : data.detail?.message || "Could not complete the quiz request.",
      data.detail?.can_retry_creation === true,
    );
  }
  return data;
}

export default function ConceptCheck({ sectionId, completed, onPass }: {
  sectionId: number;
  completed: boolean;
  onPass: () => void;
}) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [passingScore, setPassingScore] = useState(2);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [canRetryCreation, setCanRetryCreation] = useState(false);
  const path = `/sections/${sectionId}/concept-check`;

  useEffect(() => {
    let active = true;
    request(`${path}/attempts`).then((data) => {
      if (active) setAttempts(data);
    }).catch(() => { if (active) setError("Could not load attempt history."); });
    return () => { active = false; };
  }, [path]);

  async function start(retryFailed = false) {
    setBusy(true);
    setError("");
    setCanRetryCreation(false);
    try {
      const quiz = await request(path, { retry_failed: retryFailed });
      setQuestions(quiz.questions);
      setPassingScore(quiz.passing_score);
      setAnswers({});
      setResult(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not open Concept Check.");
      setCanRetryCreation(error instanceof QuizRequestError && error.canRetryCreation);
    } finally { setBusy(false); }
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const data: Result = await request(`${path}/attempts`, { answers });
      setResult(data);
      if (data.passed) onPass();
      setAttempts(await request(`${path}/attempts`));
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not submit Concept Check.");
    } finally { setBusy(false); }
  }

  return <div className="concept-check">
    <p>{completed ? "✓ Section questions completed." : questions.length
      ? `Answer ${questions.length} questions. Pass with ${passingScore}/${questions.length}.`
      : "Every section has at least two questions. Selected checkpoints have four."}</p>
    {error && <p className="path-error" role="alert">{error}</p>}
    {canRetryCreation && !questions.length && <div>
      <p>No quiz attempt was recorded. Retrying creation sends one new OpenAI request and may incur an API charge.</p>
      <button className="start-concept-button" disabled={busy} onClick={() => void start(true)}>
        Retry Quiz Creation (new API request)
      </button>
    </div>}
    {!questions.length && !canRetryCreation && <button className="start-concept-button" disabled={busy} onClick={() => void start()}>
      {busy ? "Preparing your Concept Check…" : completed ? "Review Concept Check →" : "Start Concept Check →"}
    </button>}
    {!!questions.length && <form onSubmit={(event) => { event.preventDefault(); void submit(); }}>
      {questions.map((question, index) => {
        const feedback = result?.feedback.find((item) => item.question_id === question.id);
        return <fieldset className={`quiz-question ${feedback ? feedback.correct ? "question-correct" : "question-incorrect" : ""}`} key={question.id} disabled={busy || !!result}>
          <legend><span className="question-number">Question {index + 1} of {questions.length}</span><span className="question-prompt">{question.prompt}</span></legend>
          <p className="quiz-source">{question.source.source_type === "textbook"
            ? `📖 From textbook questions · PDF page ${question.source.source_page}`
            : `✨ Generated from Section ${question.source.section_number}`}</p>
          {question.options.map((option, optionIndex) => <label className={`quiz-option ${feedback && answers[question.id] === optionIndex ? feedback.correct ? "answer-correct" : "answer-incorrect" : ""}`} key={optionIndex}>
            <input type="radio" name={`question-${question.id}`} value={optionIndex}
              checked={answers[question.id] === optionIndex}
              onChange={() => setAnswers((previous) => ({ ...previous, [question.id]: optionIndex }))} />
            <span>{option}</span>
            {feedback && answers[question.id] === optionIndex && <strong className="answer-status">{feedback.correct ? "✓ Correct" : "✕ Incorrect"}</strong>}
          </label>)}
          {feedback && <p className={`quiz-feedback ${feedback.correct ? "feedback-correct" : "feedback-incorrect"}`}>{feedback.correct ? "✓ Correct. " : "✕ Review needed. "}{feedback.feedback}</p>}
        </fieldset>;
      })}
      {!result && <button className="start-concept-button" type="submit"
        disabled={busy || Object.keys(answers).length !== questions.length}>{busy ? "Saving result…" : "Submit Answers"}</button>}
    </form>}
    {result && <div className="quiz-result" role="status">
      <h4>{result.score}/{result.total_questions} ({Math.round(result.score / result.total_questions * 100)}%) · {result.passed ? "Passed ✓" : "Try again"}</h4>
      <p>{result.passed ? "Your completion is saved. Continue to the section activity below." : "Review the suggested textbook pages, then retry these questions."}</p>
      <button className="start-concept-button" disabled={busy} onClick={() => { setAnswers({}); setResult(null); }}>
        {result.passed ? "Practice Again" : "Retry Concept Check"}
      </button>
    </div>}
    {!!attempts.length && <div className="quiz-history"><h4>Attempt History</h4>
      <ul>{attempts.map((attempt, index) => <li key={attempt.id}>
        Attempt {index + 1}: {attempt.score}/{attempt.total_questions} {attempt.passed ? "✓ Passed" : "Retry"}
        <span> · {new Date(`${attempt.created_at.replace(" ", "T")}Z`).toLocaleString()}</span>
      </li>)}</ul>
    </div>}
  </div>;
}
