import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Editor from "@monaco-editor/react";

const API_BASE = "http://127.0.0.1:8000";

type Section = "library" | "learning-path" | "chats" | "progress";

type View = "dashboard" | "study" | "lesson";

type Textbook = {
  id: number;
  filename: string;
  page_count: number;
  characters_extracted: number;
  uploaded_at: string;
};

type Chat = {
  id: number;
  textbook_id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

type Message = {
  id: number;
  chat_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

type LearningPathSection = {
  id: number;
  chapter_id: number;
  section_number: string;
  title: string;
  book_page: number | null;
  toc_pdf_page: number | null;
  confidence: "direct" | "recovered";
};

type LessonSource = {
  section_id: number;
  section_number: string;
  section_title: string;

  chapter_id: number;
  chapter_number: string;
  chapter_title: string;

  textbook_id: number;
  filename: string;

  pdf_url: string;
  source_type: string;

  pdf_start_page: number | null;
  pdf_end_page: number | null;

  book_start_page: number | null;
  book_end_page: number | null;

  page_offset: number | null;
  error?: string;
};

type LearningPathChapter = {
  id: number;
  textbook_id: number;
  chapter_number: string;
  title: string;
  book_page: number | null;
  toc_pdf_page: number | null;
  confidence: "direct" | "recovered";
  sections: LearningPathSection[];
};

type LearningPathResponse = {
  textbook_id: number;
  filename: string;
  built: boolean;
  chapters_found?: number;
  chapters: LearningPathChapter[];
};

function App() {
  const [activeSection, setActiveSection] = useState<Section>("library");

  const [view, setView] = useState<View>("dashboard");

  const [textbooks, setTextbooks] = useState<Textbook[]>([]);

  const [loading, setLoading] = useState(true);

  const [uploading, setUploading] = useState(false);

  const [uploadMessage, setUploadMessage] = useState("");

  const [selectedBook, setSelectedBook] = useState<Textbook | null>(null);

  const [currentChatId, setCurrentChatId] = useState<number | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);

  const [messageInput, setMessageInput] = useState("");

  const [sending, setSending] = useState(false);

  const [openingStudy, setOpeningStudy] = useState<number | null>(null);

  const [showCodePanel, setShowCodePanel] = useState(false);

  const [runningCode, setRunningCode] = useState(false);

  const [reviewingCode, setReviewingCode] = useState(false);

  const [code, setCode] = useState(
    `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}`,
  );

  const [codeOutput, setCodeOutput] = useState(
    "Run your code to see output here.",
  );

  // ==========================================
  // LEARNING PATH STATE
  // ==========================================

  const [learningPathBook, setLearningPathBook] = useState<Textbook | null>(
    null,
  );

  const [learningPath, setLearningPath] = useState<LearningPathResponse | null>(
    null,
  );

  const [learningPathLoading, setLearningPathLoading] = useState(false);

  const [learningPathError, setLearningPathError] = useState("");

  const [expandedChapterId, setExpandedChapterId] = useState<number | null>(
    null,
  );

  const fileInputRef = useRef<HTMLInputElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, sending]);

  const [selectedLearningSection, setSelectedLearningSection] =
    useState<LearningPathSection | null>(null);

  const [lessonSource, setLessonSource] = useState<LessonSource | null>(null);

  const [lessonLoading, setLessonLoading] = useState(false);

  const [lessonError, setLessonError] = useState("");

  // ==========================================
  // TEXTBOOK LIBRARY
  // ==========================================

  async function loadTextbooks() {
    try {
      const response = await fetch(`${API_BASE}/textbooks`);

      if (!response.ok) {
        throw new Error("Could not load textbooks.");
      }

      const data = await response.json();

      setTextbooks(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTextbooks();
  }, []);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleTextbookUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadMessage("Please choose a PDF file.");

      return;
    }

    setUploading(true);

    setUploadMessage(`Uploading ${file.name}...`);

    const formData = new FormData();

    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/upload-textbook`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Textbook upload failed.");
      }

      const result = await response.json();

      if (result.already_exists) {
        setUploadMessage("That textbook is already in your library.");
      } else {
        setUploadMessage("Textbook uploaded successfully.");
      }

      await loadTextbooks();
    } catch (error) {
      console.error(error);

      setUploadMessage("Something went wrong while uploading the textbook.");
    } finally {
      setUploading(false);

      event.target.value = "";
    }
  }

  // ==========================================
  // LEARNING PATH
  // ==========================================

  async function openLearningPath(book: Textbook) {
    setActiveSection("learning-path");

    setLearningPathBook(book);

    setLearningPathLoading(true);

    setLearningPathError("");

    setLearningPath(null);

    try {
      let response = await fetch(
        `${API_BASE}/textbooks/${book.id}/learning-path`,
      );

      if (!response.ok) {
        throw new Error("Could not load the Learning Path.");
      }

      let data: LearningPathResponse = await response.json();

      /*
        If this textbook does not have a saved
        Learning Path yet, automatically build it.
      */
      if (!data.built) {
        const rebuildResponse = await fetch(
          `${API_BASE}/textbooks/${book.id}/learning-path/rebuild`,
          {
            method: "POST",
          },
        );

        if (!rebuildResponse.ok) {
          throw new Error("Could not build the Learning Path.");
        }

        const rebuildResult = await rebuildResponse.json();

        if (!rebuildResult.saved) {
          throw new Error("The textbook structure could not be safely built.");
        }

        response = await fetch(
          `${API_BASE}/textbooks/${book.id}/learning-path`,
        );

        if (!response.ok) {
          throw new Error("Could not reload the Learning Path.");
        }

        data = await response.json();
      }

      setLearningPath(data);

      if (data.chapters.length > 0) {
        setExpandedChapterId(data.chapters[0].id);
      }
    } catch (error) {
      console.error(error);

      setLearningPathError("Could not load this textbook's Learning Path.");
    } finally {
      setLearningPathLoading(false);
    }
  }

  async function openLesson(section: LearningPathSection) {
    setSelectedLearningSection(section);

    setLessonSource(null);

    setLessonError("");

    setLessonLoading(true);

    setView("lesson");

    try {
      const response = await fetch(
        `${API_BASE}/sections/${section.id}/lesson-source`,
      );

      if (!response.ok) {
        throw new Error("Could not load lesson.");
      }

      const data: LessonSource = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setLessonSource(data);
    } catch (error) {
      console.error(error);

      setLessonError("Could not load this lesson.");
    } finally {
      setLessonLoading(false);
    }
  }

  function returnToLearningPath() {
    setView("dashboard");

    setActiveSection("learning-path");

    setSelectedLearningSection(null);

    setLessonSource(null);

    setLessonError("");
  }

  function closeLearningPathBook() {
    setLearningPathBook(null);
    setLearningPath(null);
    setLearningPathError("");
    setExpandedChapterId(null);
  }

  function toggleChapter(chapterId: number, locked: boolean) {
    if (locked) {
      return;
    }

    setExpandedChapterId(expandedChapterId === chapterId ? null : chapterId);
  }

  // ==========================================
  // CHAT
  // ==========================================

  async function loadMessages(chatId: number) {
    const response = await fetch(`${API_BASE}/chats/${chatId}/messages`);

    if (!response.ok) {
      throw new Error("Could not load chat messages.");
    }

    const data = await response.json();

    setMessages(data);
  }

  async function openStudySession(book: Textbook) {
    try {
      setOpeningStudy(book.id);

      setSelectedBook(book);

      const chatsResponse = await fetch(
        `${API_BASE}/textbooks/${book.id}/chats`,
      );

      if (!chatsResponse.ok) {
        throw new Error("Could not load chats.");
      }

      const chats: Chat[] = await chatsResponse.json();

      let chatId: number;

      if (chats.length > 0) {
        chatId = chats[0].id;
      } else {
        const createResponse = await fetch(
          `${API_BASE}/textbooks/${book.id}/chats`,
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              title: "Study Session",
            }),
          },
        );

        if (!createResponse.ok) {
          throw new Error("Could not create a study chat.");
        }

        const newChat = await createResponse.json();

        chatId = newChat.chat_id;
      }

      setCurrentChatId(chatId);

      await loadMessages(chatId);

      setView("study");
    } catch (error) {
      console.error(error);
    } finally {
      setOpeningStudy(null);
    }
  }

  async function sendMessage() {
    if (!messageInput.trim()) {
      return;
    }

    if (!currentChatId) {
      return;
    }

    const question = messageInput.trim();

    setMessageInput("");

    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/chats/${currentChatId}/ask`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          question,
        }),
      });

      if (!response.ok) {
        throw new Error("Tutor request failed.");
      }

      await response.json();

      await loadMessages(currentChatId);
    } catch (error) {
      console.error(error);
    } finally {
      setSending(false);
    }
  }

  // ==========================================
  // CODE PLAYGROUND
  // ==========================================

  async function runCode() {
    if (!code.trim()) {
      setCodeOutput("Write some Java code first.");

      return;
    }

    setRunningCode(true);

    setCodeOutput("Running...");

    try {
      const response = await fetch(`${API_BASE}/run-code`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          code,
        }),
      });

      if (!response.ok) {
        throw new Error("Code execution failed.");
      }

      const result = await response.json();

      setCodeOutput(result.output || "Program finished with no output.");
    } catch (error) {
      console.error(error);

      setCodeOutput(
        "Could not run the code. Make sure the backend is running.",
      );
    } finally {
      setRunningCode(false);
    }
  }

  async function askTutorAboutCode() {
    if (!currentChatId) {
      setCodeOutput("Open a study session first.");

      return;
    }

    if (!code.trim()) {
      setCodeOutput("Write some Java code first.");

      return;
    }

    setReviewingCode(true);

    const tutorQuestion = `
Please help me understand my Java code.

Do not immediately rewrite the entire solution for me.
Explain what I did correctly, what is wrong, and guide me toward fixing it.

MY CODE:

\`\`\`java
${code}
\`\`\`

PROGRAM / COMPILER OUTPUT:

\`\`\`text
${codeOutput}
\`\`\`

Please connect your explanation to the textbook when relevant.
`;

    try {
      const response = await fetch(`${API_BASE}/chats/${currentChatId}/ask`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          question: tutorQuestion,
        }),
      });

      if (!response.ok) {
        throw new Error("Tutor code review failed.");
      }

      await response.json();

      await loadMessages(currentChatId);
    } catch (error) {
      console.error(error);

      setCodeOutput("Could not ask the tutor about your code.");
    } finally {
      setReviewingCode(false);
    }
  }

  function handleMessageKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      sendMessage();
    }
  }

  function returnToLibrary() {
    setView("dashboard");

    setActiveSection("library");

    setSelectedBook(null);

    setCurrentChatId(null);

    setMessages([]);

    setMessageInput("");

    setShowCodePanel(false);
  }

  // ==========================================
  // STUDY CHAT PAGE
  // ==========================================

  if (view === "study" && selectedBook) {
    return (
      <div className="study-page">
        <header className="study-header">
          <button className="back-button" onClick={returnToLibrary}>
            ← Library
          </button>

          <div className="study-book-info">
            <p className="eyebrow">Studying</p>

            <h2>{selectedBook.filename}</h2>
          </div>

          <button
            className="code-toggle-button"
            onClick={() => setShowCodePanel(!showCodePanel)}
          >
            {showCodePanel ? "Close Code" : "</> Code Playground"}
          </button>
        </header>

        <main
          className={showCodePanel ? "study-layout code-open" : "study-layout"}
        >
          <section className="study-chat">
            <div className="messages">
              {messages.length === 0 ? (
                <div className="empty-chat">
                  <div className="empty-chat-icon">CS</div>

                  <h2>What do you want to learn?</h2>

                  <p>
                    Ask a question about this textbook and your tutor will use
                    the book to help explain it.
                  </p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    className={
                      message.role === "user"
                        ? "message-row user-row"
                        : "message-row assistant-row"
                    }
                    key={message.id}
                  >
                    <div
                      className={
                        message.role === "user"
                          ? "message user-message"
                          : "message assistant-message"
                      }
                    >
                      <span className="message-role">
                        {message.role === "user" ? "You" : "Tutor"}
                      </span>

                      <div className="message-content">
                        {message.role === "assistant" ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        ) : (
                          message.content
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}

              {sending && (
                <div className="message-row assistant-row">
                  <div className="message assistant-message">
                    <span className="message-role">Tutor</span>

                    <div className="message-content">
                      <span className="thinking-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div ref={messagesEndRef} />

            <div className="chat-input-area">
              <textarea
                value={messageInput}
                onChange={(event) => setMessageInput(event.target.value)}
                onKeyDown={handleMessageKeyDown}
                placeholder="Ask your textbook a question..."
                disabled={sending}
              />

              <button
                className="send-button"
                onClick={sendMessage}
                disabled={sending || !messageInput.trim()}
              >
                {sending ? "..." : "Send"}
              </button>
            </div>

            <p className="chat-hint">
              Press Enter to send · Shift + Enter for a new line
            </p>
          </section>

          {showCodePanel && (
            <aside className="code-panel">
              <div className="code-panel-header">
                <div>
                  <p className="eyebrow">Playground</p>

                  <h3>Java Editor</h3>
                </div>

                <button
                  className="reset-code-button"
                  onClick={() =>
                    setCode(
                      `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}`,
                    )
                  }
                >
                  Reset
                </button>
              </div>

              <div className="editor-container">
                <Editor
                  height="100%"
                  defaultLanguage="java"
                  language="java"
                  theme="vs-dark"
                  value={code}
                  onChange={(value) => setCode(value ?? "")}
                  options={{
                    minimap: {
                      enabled: false,
                    },

                    fontSize: 14,

                    automaticLayout: true,

                    scrollBeyondLastLine: false,

                    wordWrap: "on",
                  }}
                />
              </div>

              <div className="code-actions">
                <button
                  className="run-code-button"
                  onClick={runCode}
                  disabled={runningCode}
                >
                  {runningCode ? "Running..." : "▶ Run"}
                </button>

                <button
                  className="ask-code-button"
                  onClick={askTutorAboutCode}
                  disabled={reviewingCode}
                >
                  {reviewingCode ? "Reviewing..." : "Ask Tutor About My Code"}
                </button>
              </div>

              <div className="output-panel">
                <div className="output-header">Output</div>

                <pre>{codeOutput}</pre>
              </div>
            </aside>
          )}
        </main>
      </div>
    );
  }

  // ==========================================
  // INTERACTIVE LESSON PAGE
  // ==========================================

  if (view === "lesson" && selectedLearningSection) {
    return (
      <div className="lesson-page">
        <header className="lesson-header">
          <button className="back-button" onClick={returnToLearningPath}>
            ← Learning Path
          </button>

          <div className="lesson-header-info">
            <p className="eyebrow">Interactive Lesson</p>

            <h2>
              Section {selectedLearningSection.section_number}
              {" — "}
              {selectedLearningSection.title}
            </h2>
          </div>
        </header>

        {lessonLoading && (
          <div className="lesson-loading">Loading textbook lesson...</div>
        )}

        {lessonError && <div className="path-error">{lessonError}</div>}

        {lessonSource && (
          <main className="lesson-layout">
            <section className="lesson-intro-card">
              <p className="eyebrow">Required Reading</p>

              <h3>
                Chapter {lessonSource.chapter_number}
                {" — "}
                {lessonSource.chapter_title}
              </h3>

              <p>
                Read Section {lessonSource.section_number} directly from your
                textbook.
              </p>

              <div className="lesson-reading-meta">
                {lessonSource.book_start_page !== null && (
                  <span>
                    📖 Textbook pages {lessonSource.book_start_page}
                    {lessonSource.book_end_page !== null && (
                      <>
                        {"–"}
                        {lessonSource.book_end_page}
                      </>
                    )}
                  </span>
                )}

                {lessonSource.pdf_start_page !== null && (
                  <span>
                    PDF pages {lessonSource.pdf_start_page}
                    {lessonSource.pdf_end_page !== null && (
                      <>
                        {"–"}
                        {lessonSource.pdf_end_page}
                      </>
                    )}
                  </span>
                )}
              </div>
            </section>

            {lessonSource.pdf_start_page !== null && (
              <section className="textbook-reader">
                <div className="reader-header">
                  <div>
                    <p className="eyebrow">From Your Textbook</p>

                    <strong>{lessonSource.filename}</strong>
                  </div>

                  <a
                    className="open-pdf-button"
                    href={`${API_BASE}${lessonSource.pdf_url}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Full PDF
                  </a>
                </div>

                <iframe
                  className="pdf-reader"
                  title={`Section ${lessonSource.section_number} textbook reading`}
                  src={
                    `${API_BASE}${lessonSource.pdf_url}` +
                    `#page=${lessonSource.pdf_start_page}`
                  }
                />
              </section>
            )}

            <section className="lesson-next-card">
              <p className="eyebrow">Next Step</p>

              <h3>Check Your Understanding</h3>

              <p>
                This is where we'll add the interactive questions, coding
                activity, and mastery check.
              </p>
            </section>
          </main>
        )}
      </div>
    );
  }

  // ==========================================
  // DASHBOARD CONTENT
  // ==========================================

  function renderLibrary() {
    return (
      <>
        {uploadMessage && <p className="upload-message">{uploadMessage}</p>}

        <section className="welcome-card">
          <div>
            <p className="eyebrow">Welcome back</p>

            <h3>What do you want to learn today?</h3>

            <p className="welcome-description">
              Open a textbook, continue a saved conversation, or follow your
              structured Learning Path.
            </p>
          </div>

          <div className="welcome-stat">
            <strong>{textbooks.length}</strong>

            <span>{textbooks.length === 1 ? "Textbook" : "Textbooks"}</span>
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Your textbooks</p>

              <h3>Library</h3>
            </div>
          </div>

          <div className="book-grid">
            {loading ? (
              <p>Loading textbooks...</p>
            ) : (
              textbooks.map((book) => (
                <article className="book-card" key={book.id}>
                  <div className="book-cover">
                    <span>CS</span>
                  </div>

                  <div className="book-info">
                    <span className="book-label">Textbook</span>

                    <h4>{book.filename}</h4>

                    <p>Uploaded textbook</p>

                    <div className="book-meta">
                      <span>{book.page_count.toLocaleString()} pages</span>
                    </div>

                    <div className="book-actions">
                      <button
                        className="study-button"
                        onClick={() => openStudySession(book)}
                        disabled={openingStudy === book.id}
                      >
                        {openingStudy === book.id
                          ? "Opening..."
                          : "Continue Studying"}
                      </button>

                      <button
                        className="learning-path-button"
                        onClick={() => openLearningPath(book)}
                      >
                        Learning Path
                      </button>
                    </div>
                  </div>
                </article>
              ))
            )}

            <button
              className="add-book-card"
              onClick={openFilePicker}
              disabled={uploading}
            >
              <span className="plus">+</span>

              <strong>
                {uploading ? "Processing textbook..." : "Add a textbook"}
              </strong>

              <p>Upload a PDF to create a new study space.</p>
            </button>
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Pick up where you left off</p>

              <h3>Recent Chats</h3>
            </div>
          </div>

          <div className="chat-list">
            <button className="chat-card">
              <div className="chat-icon">💬</div>

              <div className="chat-info">
                <strong>Constructors Review</strong>

                <p>Absolute Java</p>
              </div>

              <span className="chat-arrow">→</span>
            </button>
          </div>
        </section>
      </>
    );
  }

  function renderLearningPath() {
    if (!learningPathBook) {
      return (
        <>
          <section className="learning-path-hero">
            <div>
              <p className="eyebrow">Course Mode</p>

              <h3>Choose a textbook</h3>

              <p>
                Work through your textbook chapter by chapter with readings,
                quizzes, coding activities, and mastery checks.
              </p>
            </div>

            <div className="path-hero-icon">🗺️</div>
          </section>

          <section className="section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Your courses</p>

                <h3>Learning Paths</h3>
              </div>
            </div>

            <div className="book-grid">
              {textbooks.map((book) => (
                <article className="book-card" key={book.id}>
                  <div className="book-cover">
                    <span>CS</span>
                  </div>

                  <div className="book-info">
                    <span className="book-label">Learning Path</span>

                    <h4>{book.filename}</h4>

                    <p>Follow the book in order.</p>

                    <button
                      className="study-button"
                      onClick={() => openLearningPath(book)}
                    >
                      Open Learning Path
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      );
    }

    return (
      <>
        <section className="path-course-header">
          <button className="path-back-button" onClick={closeLearningPathBook}>
            ← All Learning Paths
          </button>

          <div className="path-course-title">
            <p className="eyebrow">Learning Path</p>

            <h3>{learningPathBook.filename}</h3>

            <p>Complete each chapter in order to finish the textbook.</p>
          </div>

          <div className="overall-progress">
            <div className="overall-progress-top">
              <span>Overall Progress</span>

              <strong>0%</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: "0%",
                }}
              />
            </div>
          </div>
        </section>

        {learningPathLoading && (
          <div className="path-loading">
            <div className="path-spinner" />

            <h3>Building Learning Path...</h3>

            <p>Reading the textbook structure and organizing its chapters.</p>
          </div>
        )}

        {learningPathError && (
          <div className="path-error">{learningPathError}</div>
        )}

        {!learningPathLoading && learningPath && (
          <section className="chapter-roadmap">
            <div className="roadmap-heading">
              <p className="eyebrow">Course roadmap</p>

              <h3>{learningPath.chapters.length} Chapters</h3>

              <p>
                Chapter 1 is available now. Complete each chapter to unlock the
                next one.
              </p>
            </div>

            <div className="chapter-list">
              {learningPath.chapters.map((chapter, index) => {
                /*
                    For the MVP only Chapter 1
                    is unlocked.

                    Later this comes from real
                    progress/mastery data.
                  */
                const locked = index > 0;

                const expanded = expandedChapterId === chapter.id;

                return (
                  <article
                    className={`chapter-card ${
                      locked ? "chapter-locked" : "chapter-unlocked"
                    } ${expanded ? "chapter-expanded" : ""}`}
                    key={chapter.id}
                  >
                    <div className="chapter-path-marker">
                      <div className="chapter-number-circle">
                        {locked ? "🔒" : chapter.chapter_number}
                      </div>

                      {index < learningPath.chapters.length - 1 && (
                        <div className="chapter-connector" />
                      )}
                    </div>

                    <div className="chapter-content">
                      <button
                        className="chapter-header-button"
                        disabled={locked}
                        onClick={() => toggleChapter(chapter.id, locked)}
                      >
                        <div className="chapter-title-area">
                          <span className="chapter-label">
                            Chapter {chapter.chapter_number}
                          </span>

                          <h4>{chapter.title}</h4>

                          <p>
                            {chapter.sections.length} sections
                            {chapter.book_page !== null && (
                              <> · starts on page {chapter.book_page}</>
                            )}
                          </p>
                        </div>

                        <div className="chapter-status">
                          {locked ? (
                            <span className="locked-badge">Locked</span>
                          ) : (
                            <span className="current-badge">Start Here</span>
                          )}

                          {!locked && (
                            <span className="expand-arrow">
                              {expanded ? "▲" : "▼"}
                            </span>
                          )}
                        </div>
                      </button>

                      {expanded && !locked && (
                        <div className="chapter-sections">
                          <div className="chapter-progress-summary">
                            <span>Chapter Progress</span>

                            <strong>0%</strong>
                          </div>

                          <div className="progress-track small">
                            <div
                              className="progress-fill"
                              style={{
                                width: "0%",
                              }}
                            />
                          </div>

                          <div className="section-list">
                            {chapter.sections.map((section, sectionIndex) => (
                              <button
                                className={
                                  sectionIndex === 0
                                    ? "learning-section-row lesson-ready-row"
                                    : "learning-section-row"
                                }
                                key={section.id}
                                disabled={sectionIndex !== 0}
                                onClick={() => openLesson(section)}
                              >
                                <div className="section-status-dot">
                                  {sectionIndex === 0 ? "▶" : "○"}
                                </div>

                                <div className="learning-section-info">
                                  <span>Section {section.section_number}</span>

                                  <strong>{section.title}</strong>

                                  {section.book_page !== null && (
                                    <p>Textbook page {section.book_page}</p>
                                  )}
                                </div>

                                <div className="section-row-status">
                                  {sectionIndex === 0 ? (
                                    <span className="ready-badge">Ready</span>
                                  ) : (
                                    <span className="upcoming-badge">
                                      Upcoming
                                    </span>
                                  )}
                                </div>
                              </button>
                            ))}
                          </div>

                          <div className="chapter-coming-next">
                            <span>Next development step</span>

                            <strong>
                              Open Section {chapter.sections[0]?.section_number}{" "}
                              as an interactive lesson
                            </strong>
                          </div>
                        </div>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}
      </>
    );
  }

  function renderPlaceholder(title: string, description: string) {
    return (
      <section className="placeholder-page">
        <div className="placeholder-icon">CS</div>

        <p className="eyebrow">Coming next</p>

        <h3>{title}</h3>

        <p>{description}</p>
      </section>
    );
  }

  // ==========================================
  // MAIN DASHBOARD
  // ==========================================

  const pageTitle =
    activeSection === "library"
      ? "My Library"
      : activeSection === "learning-path"
        ? "Learning Path"
        : activeSection === "chats"
          ? "Chats"
          : "Progress";

  return (
    <div className="app">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleTextbookUpload}
        style={{
          display: "none",
        }}
      />

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">CS</div>

          <div>
            <h1>Textbook Tutor</h1>

            <p>AI Study Assistant</p>
          </div>
        </div>

        <nav className="nav">
          <button
            className={
              activeSection === "library" ? "nav-item active" : "nav-item"
            }
            onClick={() => {
              setActiveSection("library");

              closeLearningPathBook();
            }}
          >
            <span>📚</span>
            Library
          </button>

          <button
            className={
              activeSection === "learning-path" ? "nav-item active" : "nav-item"
            }
            onClick={() => setActiveSection("learning-path")}
          >
            <span>🗺️</span>
            Learning Path
          </button>

          <button
            className={
              activeSection === "chats" ? "nav-item active" : "nav-item"
            }
            onClick={() => setActiveSection("chats")}
          >
            <span>💬</span>
            Chats
          </button>

          <button
            className={
              activeSection === "progress" ? "nav-item active" : "nav-item"
            }
            onClick={() => setActiveSection("progress")}
          >
            <span>📊</span>
            Progress
          </button>
        </nav>

        <div className="sidebar-footer">
          <p>CS Textbook Tutor</p>

          <span>Learning project</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Study workspace</p>

            <h2>{pageTitle}</h2>
          </div>

          {activeSection === "library" && (
            <button
              className="upload-button"
              onClick={openFilePicker}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "+ Add Textbook"}
            </button>
          )}
        </header>

        {activeSection === "library" && renderLibrary()}

        {activeSection === "learning-path" && renderLearningPath()}

        {activeSection === "chats" &&
          renderPlaceholder(
            "Saved Chats",
            "Your full saved-chat browser will live here.",
          )}

        {activeSection === "progress" &&
          renderPlaceholder(
            "Progress Dashboard",
            "Reading, quiz, coding, and mastery progress will appear here.",
          )}
      </main>
    </div>
  );
}

export default App;
