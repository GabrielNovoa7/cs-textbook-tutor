import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import Editor from "@monaco-editor/react";

type Section = "library" | "chats" | "practice" | "progress";
type View = "dashboard" | "study";

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

const [code, setCode] = useState(`public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}`);

const [codeOutput, setCodeOutput] = useState(
  "Run your code to see output here."
);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
  messagesEndRef.current?.scrollIntoView({
    behavior: "smooth",
  });
}, [messages, sending]);

  async function loadTextbooks() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/textbooks"
      );

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

  async function handleTextbookUpload(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
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
      const response = await fetch(
        "http://127.0.0.1:8000/upload-textbook",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Textbook upload failed.");
      }

      const result = await response.json();

      if (result.already_exists) {
        setUploadMessage(
          "That textbook is already in your library."
        );
      } else {
        setUploadMessage(
          "Textbook uploaded successfully."
        );
      }

      await loadTextbooks();
    } catch (error) {
      console.error(error);

      setUploadMessage(
        "Something went wrong while uploading the textbook."
      );
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function loadMessages(chatId: number) {
    const response = await fetch(
      `http://127.0.0.1:8000/chats/${chatId}/messages`
    );

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
        `http://127.0.0.1:8000/textbooks/${book.id}/chats`
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
          `http://127.0.0.1:8000/textbooks/${book.id}/chats`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              title: "Study Session",
            }),
          }
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
      const response = await fetch(
        `http://127.0.0.1:8000/chats/${currentChatId}/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question,
          }),
        }
      );

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

  async function runCode() {
  if (!code.trim()) {
    setCodeOutput("Write some Java code first.");
    return;
  }

  setRunningCode(true);
  setCodeOutput("Running...");

  try {
    const response = await fetch(
      "http://127.0.0.1:8000/run-code",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code: code,
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Code execution failed.");
    }

    const result = await response.json();

    setCodeOutput(
      result.output || "Program finished with no output."
    );
  } catch (error) {
    console.error(error);

    setCodeOutput(
      "Could not run the code. Make sure the backend is running."
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
    const response = await fetch(
      `http://127.0.0.1:8000/chats/${currentChatId}/ask`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: tutorQuestion,
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Tutor code review failed.");
    }

    await response.json();

    await loadMessages(currentChatId);
  } catch (error) {
    console.error(error);

    setCodeOutput(
      "Could not ask the tutor about your code."
    );
  } finally {
    setReviewingCode(false);
  }
}

  function handleMessageKeyDown(
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  function returnToLibrary() {
    setView("dashboard");
    setSelectedBook(null);
    setCurrentChatId(null);
    setMessages([]);
    setMessageInput("");
  }

  if (view === "study" && selectedBook) {
    return (
      <div className="study-page">
        <header className="study-header">
          <button
            className="back-button"
            onClick={returnToLibrary}
          >
            ← Library
          </button>
          <button
  className="code-toggle-button"
  onClick={() => setShowCodePanel(!showCodePanel)}
>
  {showCodePanel ? "Close Code" : "</> Code Playground"}
</button>

          <div className="study-book-info">
            <p className="eyebrow">Studying</p>
            <h2>{selectedBook.filename}</h2>
          </div>
        </header>

        <main
  className={
    showCodePanel
      ? "study-layout code-open"
      : "study-layout"
  }
>
  <section className="study-chat">
            <div className="messages">
              {messages.length === 0 ? (
                <div className="empty-chat">
                  <div className="empty-chat-icon">CS</div>

                  <h2>What do you want to learn?</h2>

                  <p>
                    Ask a question about this textbook and
                    your tutor will use the book to help
                    explain it.
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
                        {message.role === "user"
                          ? "You"
                          : "Tutor"}
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
                    <span className="message-role">
                      Tutor
                    </span>

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
                onChange={(event) =>
                  setMessageInput(event.target.value)
                }
                onKeyDown={handleMessageKeyDown}
                placeholder="Ask your textbook a question..."
                disabled={sending}
              />

              <button
                className="send-button"
                onClick={sendMessage}
                disabled={
                  sending || !messageInput.trim()
                }
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
          setCode(`public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}`)
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
  {reviewingCode
    ? "Reviewing..."
    : "Ask Tutor About My Code"}
</button>
    </div>

    <div className="output-panel">
      <div className="output-header">
        Output
      </div>

      <pre>{codeOutput}</pre>
    </div>
  </aside>
)}
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleTextbookUpload}
        style={{ display: "none" }}
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
              activeSection === "library"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => setActiveSection("library")}
          >
            <span>📚</span>
            Library
          </button>

          <button
            className={
              activeSection === "chats"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => setActiveSection("chats")}
          >
            <span>💬</span>
            Chats
          </button>

          <button
            className={
              activeSection === "practice"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => setActiveSection("practice")}
          >
            <span>🧠</span>
            Practice
          </button>

          <button
            className={
              activeSection === "progress"
                ? "nav-item active"
                : "nav-item"
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
            <p className="eyebrow">
              Study workspace
            </p>

            <h2>My Library</h2>
          </div>

          <button
            className="upload-button"
            onClick={openFilePicker}
            disabled={uploading}
          >
            {uploading
              ? "Uploading..."
              : "+ Add Textbook"}
          </button>
        </header>

        {uploadMessage && (
          <p className="upload-message">
            {uploadMessage}
          </p>
        )}

        <section className="welcome-card">
          <div>
            <p className="eyebrow">
              Welcome back
            </p>

            <h3>
              What do you want to learn today?
            </h3>

            <p className="welcome-description">
              Open a textbook, continue a saved
              conversation, or start a new study
              session with your AI tutor.
            </p>
          </div>

          <div className="welcome-stat">
            <strong>{textbooks.length}</strong>

            <span>
              {textbooks.length === 1
                ? "Textbook"
                : "Textbooks"}
            </span>
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                Your textbooks
              </p>

              <h3>Library</h3>
            </div>

            <button className="text-button">
              View all
            </button>
          </div>

          <div className="book-grid">
            {loading ? (
              <p>Loading textbooks...</p>
            ) : (
              textbooks.map((book) => (
                <article
                  className="book-card"
                  key={book.id}
                >
                  <div className="book-cover">
                    <span>CS</span>
                  </div>

                  <div className="book-info">
                    <span className="book-label">
                      Textbook
                    </span>

                    <h4>{book.filename}</h4>

                    <p>Uploaded textbook</p>

                    <div className="book-meta">
                      <span>
                        {book.page_count.toLocaleString()} pages
                      </span>
                    </div>

                    <button
                      className="study-button"
                      onClick={() =>
                        openStudySession(book)
                      }
                      disabled={
                        openingStudy === book.id
                      }
                    >
                      {openingStudy === book.id
                        ? "Opening..."
                        : "Continue Studying"}
                    </button>
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
                {uploading
                  ? "Processing textbook..."
                  : "Add a textbook"}
              </strong>

              <p>
                Upload a PDF to create a new
                study space.
              </p>
            </button>
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                Pick up where you left off
              </p>

              <h3>Recent Chats</h3>
            </div>
          </div>

          <div className="chat-list">
            <button className="chat-card">
              <div className="chat-icon">
                💬
              </div>

              <div className="chat-info">
                <strong>
                  Constructors Review
                </strong>

                <p>Absolute Java</p>
              </div>

              <span className="chat-arrow">
                →
              </span>
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;