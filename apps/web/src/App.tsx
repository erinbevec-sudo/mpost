import {
  BadgeCheck,
  Database,
  ExternalLink,
  FileSearch,
  Gauge,
  MessageSquare,
  RefreshCw,
  Search,
  Send,
  Shield,
  UserRoundCog,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useRef, useMemo, useState } from "react";
import {
  assignRole,
  AuthUser,
  ChatMessage,
  ChatSource,
  ClientContext,
  DocumentRecord,
  getCurrentUser,
  listDocuments,
  listRoles,
  login,
  logout,
  recommendForPersona,
  removeRole,
  reviewDocument,
  Role,
  searchDocumentsWithSummary,
  SearchResult,
  sendChatMessage,
  setPassword as setUserPassword,
  updateDocumentMetadata,
  uploadDocument,
  UserRoles,
} from "./api";

type View = "search" | "chat" | "persona" | "documents" | "rbac";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

const roles: Role[] = ["user", "chief_of_staff", "rbac_admin"];
const echelonOptions = ["squad", "platoon", "company", "battalion", "brigade", "division", "corps", "theater"];
const unitTypeOptions = [
  "detention operations",
  "general support",
  "detention camp liason",
  "theatre detention reporting center",
];
const missionContextOptions = [
  "mobility support",
  "area security",
  "detention operations",
  "police intelligence operations",
  "host nation policing support",
];

export function App() {
  const [view, setView] = useState<View>("search");
  const [email, setEmail] = useState("user@example.com");
  const [role, setRole] = useState<Role>("user");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const context = useMemo<ClientContext>(() => ({ apiUrl, email, role }), [email, role]);
  const isRbacAdmin = authUser?.roles.includes("rbac_admin") || false;
  const visibleView = isRbacAdmin || view !== "rbac" ? view : "search";

  // Check authentication on mount
  useEffect(() => {
    async function checkAuth() {
      try {
        const user = await getCurrentUser(apiUrl);
        setAuthUser(user);
        setEmail(user.email);
        setRole((user.roles[0] as Role) || "user");
      } catch {
        setAuthUser(null);
      } finally {
        setAuthLoading(false);
      }
    }
    checkAuth();
  }, []);

  async function handleLogin(loginEmail: string, password: string) {
    try {
      const user = await login(apiUrl, loginEmail, password);
      setAuthUser(user);
      setEmail(user.email);
      setRole((user.roles[0] as Role) || "user");
      return true;
    } catch (error) {
      console.error("Login failed:", error);
      return false;
    }
  }

  async function handleLogout() {
    try {
      await logout(apiUrl);
    } catch (error) {
      console.error("Logout failed:", error);
    }
    setAuthUser(null);
    setEmail("");
    setRole("user");
  }

  if (authLoading) {
    return <div className="loading-screen">Loading...</div>;
  }

  if (!authUser) {
    return <LoginView onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/logo.jpg" alt="M-POST Logo" className="brand-logo" />
          <div>
            <strong>M-POST</strong>
            <span>Military Police Operations Search Tool</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Primary">
          <NavButton active={visibleView === "search"} icon={<Search size={18} />} onClick={() => setView("search")}>
            Library
          </NavButton>
          <NavButton active={visibleView === "chat"} icon={<MessageSquare size={18} />} onClick={() => setView("chat")}>
            Chat
          </NavButton>
          <NavButton
            active={visibleView === "persona"}
            icon={<UserRoundCog size={18} />}
            onClick={() => setView("persona")}
          >
            Position
          </NavButton>
          <NavButton
            active={visibleView === "documents"}
            icon={<Database size={18} />}
            onClick={() => setView("documents")}
          >
            Documents
          </NavButton>
          {isRbacAdmin && (
            <NavButton active={visibleView === "rbac"} icon={<Shield size={18} />} onClick={() => setView("rbac")}>
              RBAC
            </NavButton>
          )}
        </nav>

        <div className="session-panel">
          <div className="role-description">{roleDescription(authUser)}</div>
          <div className="user-info">
            <div className="user-email">{email}</div>
          </div>
          <button className="secondary" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </aside>

      <main className="workspace">
        {visibleView === "search" && <SearchView context={context} />}
        {visibleView === "chat" && <ChatView context={context} />}
        {visibleView === "persona" && <PersonaView context={context} />}
        {visibleView === "documents" && <DocumentsView context={context} authUser={authUser} />}
        {visibleView === "rbac" && <RbacView context={context} />}
      </main>

      <footer className="app-footer">
        <img src="/11.svg" alt="11" />
        <img src="/290.jpg" alt="290" />
        <img src="/300.jpg" alt="300" />
        <img src="/333.jpg" alt="333" />
      </footer>
    </div>
  );
}

function NavButton({
  active,
  children,
  icon,
  onClick,
}: {
  active: boolean;
  children: string;
  icon: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>
      {icon}
      <span>{children}</span>
    </button>
  );
}

function LoginView({ onLogin }: { onLogin: (email: string, password: string) => Promise<boolean> }) {
  const [email, setEmail] = useState("dev@dev.com");
  const [password, setPassword] = useState("dev");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);

    const success = await onLogin(email, password);
    if (!success) {
      setError("Invalid email or password");
    }

    setLoading(false);
  }

  return (
    <div className="login-screen">
      <div className="login-panel">
        <div className="login-header">
          <img src="/logo.jpg" alt="M-POST Logo" className="login-logo" />
          <div>
            <h1>M-POST</h1>
            <p>Military Police Operations Search Tool</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              autoFocus
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
            />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="primary" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <footer className="login-footer">
          <img src="/11.svg" alt="11" />
          <img src="/290.jpg" alt="290" />
          <img src="/300.jpg" alt="300" />
          <img src="/333.jpg" alt="333" />
        </footer>
      </div>
    </div>
  );
}

function ChatView({ context }: { context: ClientContext }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [state, setState] = useAsyncState();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;

    const userMessage: ChatMessage = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setState("loading");

    try {
      const response = await sendChatMessage(context, {
        message: userMessage.content,
        history: messages,
        max_history: 10,
      });

      const assistantMessage: ChatMessage = { role: "assistant", content: response.response };
      setMessages((prev) => [...prev, assistantMessage]);
      setSources(response.sources);
      setState("ready");
    } catch (error) {
      setState("error", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
      ]);
    }
  }

  function clearChat() {
    setMessages([]);
    setSources([]);
  }

  return (
    <section className="view chat-view">
      <Header
        icon={<MessageSquare size={24} />}
        title="Doctrine Chat"
        detail="Ask questions about military police doctrine and get answers from the knowledge base."
      />
      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <MessageSquare size={48} />
              <h2>Ask me anything about Military Police doctrine</h2>
              <p>Examples:</p>
              <ul>
                <li>What are the key responsibilities of MP detention operations?</li>
                <li>How should MPs conduct area security operations?</li>
                <li>What are the procedures for handling detainees?</li>
              </ul>
            </div>
          )}
          {messages.map((message, index) => {
            // Convert markdown bold (**text**) to HTML
            const formattedContent = message.content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            return (
              <div key={index} className={`chat-message ${message.role}`}>
                <div className="message-content" dangerouslySetInnerHTML={{ __html: formattedContent }} />
              </div>
            );
          })}
          {state.kind === "loading" && (
            <div className="chat-message assistant">
              <div className="message-content typing">Thinking...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {sources.length > 0 && (
          <div className="chat-sources">
            <h3>Sources</h3>
            <ul>
              {sources.slice(0, 3).map((source, index) => (
                <li key={index}>
                  {source.title}
                  {source.page_number && ` (page ${source.page_number})`}
                  <span className="source-score">{(source.score * 100).toFixed(0)}% match</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <form className="chat-input-form" onSubmit={submit}>
        <input
          className="chat-input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask a question about military police doctrine..."
          disabled={state.kind === "loading"}
        />
        <button className="primary" type="submit" disabled={!input.trim() || state.kind === "loading"}>
          <Send size={17} />
          Send
        </button>
        {messages.length > 0 && (
          <button className="secondary" type="button" onClick={clearChat}>
            Clear
          </button>
        )}
      </form>
      <AsyncBanner state={state} />
    </section>
  );
}

function SearchView({ context }: { context: ClientContext }) {
  const [query, setQuery] = useState("military police support to mobility operations");
  const [limit, setLimit] = useState(10);
  const [filters, setFilters] = useState({ echelon: "", mp_unit_type: "", operation_type: "" });
  const [results, setResults] = useState<SearchResult[]>([]);
  const [summary, setSummary] = useState("");
  const [summarySource, setSummarySource] = useState("");
  const [state, setState] = useAsyncState();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("loading");
    try {
      const response = await searchDocumentsWithSummary(context, {
        query,
        limit,
        echelon: optional(filters.echelon),
        mp_unit_type: optional(filters.mp_unit_type),
        operation_type: optional(filters.operation_type),
      });
      setResults(response.results);
      setSummary(response.summary);
      setSummarySource(response.summary_source);
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  return (
    <section className="view">
      <Header
        icon={<FileSearch size={24} />}
        title="Library Search"
        detail="Search from a curated collection of Military Police Doctrine, articles, and white papers."
      />
      <form className="toolbar" onSubmit={submit}>
        <input className="query-input" value={query} onChange={(event) => setQuery(event.target.value)} />
        <NumberInput value={limit} onChange={setLimit} min={1} max={50} />
        <button className="primary" type="submit">
          <Search size={17} />
          Search
        </button>
      </form>
      <div className="filter-row">
        <TextField label="Echelon" value={filters.echelon} onChange={(value) => setFilters({ ...filters, echelon: value })} />
        <SelectField
          label="Unit Type"
          value={filters.mp_unit_type}
          options={["", ...unitTypeOptions]}
          onChange={(value) => setFilters({ ...filters, mp_unit_type: value })}
        />
        <TextField
          label="Operation"
          value={filters.operation_type}
          onChange={(value) => setFilters({ ...filters, operation_type: value })}
        />
      </div>
      <AsyncBanner state={state} />
      <SummaryPanel summary={summary} source={summarySource} />
      <ResultsTable apiUrl={context.apiUrl} results={results} />
    </section>
  );
}

function PersonaView({ context }: { context: ClientContext }) {
  const [form, setForm] = useState({
    echelon: "brigade",
    job_title: "",
    mp_unit_type: "detention operations",
    mission_context: "detention operations",
    limit: 10,
  });
  const [results, setResults] = useState<SearchResult[]>([]);
  const [state, setState] = useAsyncState();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("loading");
    try {
      const rows = await recommendForPersona(context, form);
      setResults(rows);
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  return (
    <section className="view">
      <Header
        icon={<UserRoundCog size={24} />}
        title="Position Search"
        detail="Retrieve all relevant documents based on your current Military Police position."
      />
      <form className="form-grid" onSubmit={submit}>
        <SelectField label="Echelon" value={form.echelon} options={echelonOptions} onChange={(value) => setForm({ ...form, echelon: value })} />
        <TextField label="Job Title" value={form.job_title} onChange={(value) => setForm({ ...form, job_title: value })} />
        <SelectField
          label="Unit Type"
          value={form.mp_unit_type}
          options={unitTypeOptions}
          onChange={(value) => setForm({ ...form, mp_unit_type: value })}
        />
        <SelectField
          label="Mission Context"
          value={form.mission_context}
          options={missionContextOptions}
          onChange={(value) => setForm({ ...form, mission_context: value })}
        />
        <label>
          Limit
          <NumberInput value={form.limit} onChange={(value) => setForm({ ...form, limit: value })} min={1} max={50} />
        </label>
        <button className="primary align-end" type="submit">
          <Gauge size={17} />
          Retrieve
        </button>
      </form>
      <AsyncBanner state={state} />
      <ResultsTable apiUrl={context.apiUrl} results={results} />
    </section>
  );
}

function DocumentsView({ context, authUser }: { context: ClientContext; authUser: AuthUser | null }) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selected, setSelected] = useState<DocumentRecord | null>(null);
  const [state, setState] = useAsyncState();
  const [uploadState, setUploadState] = useAsyncState();
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadForm, setUploadForm] = useState({
    title: "",
    doctrine_type: "white_paper",
    mp_unit_type: "general support",
    tags: "",
  });
  const canReview = authUser?.roles.includes("chief_of_staff") || authUser?.roles.includes("rbac_admin") || false;

  async function refresh() {
    setState("loading");
    try {
      const rows = await listDocuments(context);
      setDocuments(rows);
      setSelected((current) => rows.find((row) => row.id === current?.id) ?? rows[0] ?? null);
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  async function saveMetadata(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setState("loading");
    try {
      const updated = await updateDocumentMetadata(context, selected.id, selected);
      setSelected(updated);
      setDocuments((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  async function reviewSelected(reviewStatus: "approved" | "denied") {
    if (!selected) return;
    setState("loading");
    try {
      const updated = await reviewDocument(context, selected.id, reviewStatus);
      setSelected(updated);
      setDocuments((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  async function submitUpload(event: FormEvent) {
    event.preventDefault();
    if (!uploadFile) {
      setUploadState("error", new Error("Choose a document to upload."));
      return;
    }
    setUploadState("loading");
    try {
      await uploadDocument(context, { ...uploadForm, file: uploadFile });
      setUploadForm({ title: "", doctrine_type: "white_paper", mp_unit_type: "general support", tags: "" });
      setUploadFile(null);
      setUploadState("ready");
      if (canReview) {
        const rows = await listDocuments(context);
        setDocuments(rows);
      }
    } catch (error) {
      setUploadState("error", error);
    }
  }

  return (
    <section className="view">
      <Header
        icon={<Database size={24} />}
        title="Documents"
        detail={
          canReview
            ? "Review user submissions, approve or deny additions to the library, and maintain document metadata."
            : "Request that documents be reviewed for inclusion in the M-POST library."
        }
      />
      <form className="upload-panel" onSubmit={submitUpload}>
        <div>
          <h2>Request Library Addition</h2>
          <p>Submit documents for chief-of-staff review before they are added to the curated library.</p>
        </div>
        <input type="file" accept=".pdf,.docx" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
        <TextField label="Title" value={uploadForm.title} onChange={(value) => setUploadForm({ ...uploadForm, title: value })} />
        <TextField
          label="Document Type"
          value={uploadForm.doctrine_type}
          onChange={(value) => setUploadForm({ ...uploadForm, doctrine_type: value })}
        />
        <SelectField
          label="Unit Type"
          value={uploadForm.mp_unit_type}
          options={unitTypeOptions}
          onChange={(value) => setUploadForm({ ...uploadForm, mp_unit_type: value })}
        />
        <TextField label="Tags" value={uploadForm.tags} onChange={(value) => setUploadForm({ ...uploadForm, tags: value })} />
        <button className="secondary" type="submit">Submit Request</button>
        <AsyncBanner state={uploadState} />
      </form>
      {canReview && (
        <>
          <div className="toolbar compact">
            <button className="secondary" onClick={refresh}>
              <RefreshCw size={17} />
              Refresh
            </button>
          </div>
          <AsyncBanner state={state} />
          <div className="split">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Embeddings</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document) => (
                    <tr
                      className={selected?.id === document.id ? "selected" : ""}
                      key={document.id}
                      onClick={() => setSelected(document)}
                    >
                      <td>{document.title}</td>
                      <td>{document.status}</td>
                      <td>{document.chunk_count}</td>
                      <td>{document.embedding_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <form className="metadata-panel" onSubmit={saveMetadata}>
              {selected ? (
                <>
                  <h2>{selected.title}</h2>
                  <TextField label="Doctrine Type" value={selected.doctrine_type ?? ""} onChange={(value) => setSelected({ ...selected, doctrine_type: value })} />
                  <TextField label="Echelon" value={selected.echelon ?? ""} onChange={(value) => setSelected({ ...selected, echelon: value })} />
                  <TextField label="Unit Type" value={selected.mp_unit_type ?? ""} onChange={(value) => setSelected({ ...selected, mp_unit_type: value })} />
                  <TextField label="Operation" value={selected.operation_type ?? ""} onChange={(value) => setSelected({ ...selected, operation_type: value })} />
                  <TextField
                    label="Classification"
                    value={selected.classification_level ?? ""}
                    onChange={(value) => setSelected({ ...selected, classification_level: value })}
                  />
                  <TextField
                    label="Tags"
                    value={selected.tags.join(", ")}
                    onChange={(value) => setSelected({ ...selected, tags: value.split(",").map((item) => item.trim()).filter(Boolean) })}
                  />
                  <button className="primary" type="submit">
                    <BadgeCheck size={17} />
                    Save
                  </button>
                  <div className="review-actions">
                    <button className="secondary" type="button" onClick={() => reviewSelected("approved")}>
                      Approve
                    </button>
                    <button className="secondary danger" type="button" onClick={() => reviewSelected("denied")}>
                      Deny
                    </button>
                  </div>
                </>
              ) : (
                <p className="empty">No document selected.</p>
              )}
            </form>
          </div>
        </>
      )}
    </section>
  );
}

function RbacView({ context }: { context: ClientContext }) {
  const [rows, setRows] = useState<UserRoles[]>([]);
  const [email, setEmail] = useState("analyst@example.com");
  const [role, setRole] = useState<Role>("user");
  const [password, setPassword] = useState("");
  const [state, setState] = useAsyncState();

  async function refresh() {
    setState("loading");
    try {
      setRows(await listRoles(context));
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("loading");
    try {
      await assignRole(context, { email, role });
      if (password.trim()) {
        await setUserPassword(context, { email, password });
      }
      setRows(await listRoles(context));
      setPassword("");
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  async function handleRemoveRole(userEmail: string, userRole: string) {
    setState("loading");
    try {
      await removeRole(context, { email: userEmail, role: userRole as Role });
      setRows(await listRoles(context));
      setState("ready");
    } catch (error) {
      setState("error", error);
    }
  }

  return (
    <section className="view">
      <Header icon={<Shield size={24} />} title="RBAC" detail="Assign roles and set passwords for users." />
      <form className="toolbar" onSubmit={submit}>
        <input
          className="query-input"
          placeholder="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
          {roles.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <input
          type="password"
          placeholder="Password (optional)"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button className="primary" type="submit">
          <Shield size={17} />
          Assign
        </button>
        <button className="secondary" type="button" onClick={refresh}>
          <RefreshCw size={17} />
          Refresh
        </button>
      </form>
      <AsyncBanner state={state} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {rows
              .filter((row) => row.roles.length > 0)
              .flatMap((row) =>
                row.roles.map((userRole) => (
                  <tr key={`${row.email}-${userRole}`}>
                    <td>{row.email}</td>
                    <td>{userRole}</td>
                    <td>
                      <button
                        className="secondary danger"
                        type="button"
                        onClick={() => handleRemoveRole(row.email, userRole)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))
              )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Header({ detail, icon, title }: { detail: string; icon: ReactNode; title: string }) {
  return (
    <header className="view-header">
      <div className="title-icon">{icon}</div>
      <div>
        <h1>{title}</h1>
        <p>{detail}</p>
      </div>
    </header>
  );
}

function SummaryPanel({ source, summary }: { source: string; summary: string }) {
  if (!summary) return null;

  // Convert markdown bold (**text**) to HTML
  const formattedSummary = summary.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  return (
    <section className="summary-panel">
      <div className="summary-topline">
        <h2>Executive Summary</h2>
        <span>{source === "fallback" ? "extractive" : source}</span>
      </div>
      <p dangerouslySetInnerHTML={{ __html: formattedSummary }} />
    </section>
  );
}

function ResultsTable({ apiUrl, results }: { apiUrl: string; results: SearchResult[] }) {
  if (results.length === 0) return null;

  return (
    <>
      <h2 className="references-header">References</h2>
      <div className="results">
        {results.map((result) => (
          <article className="result-row" key={`${result.chunk_id}-${result.score}`}>
          <div className="result-topline">
            <div>
              <h2>{result.title_description}</h2>
              <span className="document-title">{result.title}</span>
            </div>
            <div className="result-actions">
              <span>{result.page_number ? `page ${result.page_number}` : "page pending"}</span>
              <span>{`chunk ${result.chunk_index}`}</span>
              <span>{result.score.toFixed(3)}</span>
              <a href={pdfSearchUrl(apiUrl, result)} target="_blank" rel="noreferrer">
                <ExternalLink size={15} />
                PDF
              </a>
            </div>
          </div>
          <p>{result.snippet}</p>
          <div className="meta-line">
            {Object.entries(result.metadata)
              .filter(([, value]) => value)
              .map(([key, value]) => (
                <span key={key}>{`${key}: ${value}`}</span>
              ))}
          </div>
        </article>
      ))}
      </div>
    </>
  );
}

function SelectField({
  label,
  onChange,
  options,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  options: string[];
  value: string;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextField({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberInput({
  max,
  min,
  onChange,
  value,
}: {
  max: number;
  min: number;
  onChange: (value: number) => void;
  value: number;
}) {
  return (
    <input
      className="number-input"
      max={max}
      min={min}
      type="number"
      value={value}
      onChange={(event) => onChange(Number(event.target.value))}
    />
  );
}

type AsyncState = { kind: "idle" | "loading" | "ready" | "error"; message?: string };

function useAsyncState(): [AsyncState, (kind: AsyncState["kind"], error?: unknown) => void] {
  const [state, setState] = useState<AsyncState>({ kind: "idle" });
  return [
    state,
    (kind, error) => {
      if (kind === "error") {
        setState({ kind, message: error instanceof Error ? error.message : String(error) });
      } else {
        setState({ kind });
      }
    },
  ];
}

function AsyncBanner({ state }: { state: AsyncState }) {
  if (state.kind === "idle") return null;
  if (state.kind === "loading") return <div className="status loading">Working...</div>;
  if (state.kind === "error") return <div className="status error">{state.message}</div>;
  return <div className="status ready">Ready</div>;
}

function optional(value: string) {
  return value.trim() ? value.trim() : null;
}

function pdfSearchUrl(apiUrl: string, result: SearchResult) {
  const searchText = result.snippet.split(/\s+/).slice(0, 12).join(" ");
  return `${apiUrl}${result.pdf_url}#search=${encodeURIComponent(searchText)}`;
}

function roleDescription(authUser: AuthUser | null) {
  if (!authUser) return "";

  const roles = authUser.roles;
  const descriptions: string[] = [];

  if (roles.includes("rbac_admin")) {
    descriptions.push("RBAC Admin");
  }
  if (roles.includes("chief_of_staff")) {
    descriptions.push("Chief of Staff");
  }
  if (roles.includes("user")) {
    descriptions.push("User");
  }

  return descriptions.join(" | ");
}
