export type Role = "user" | "chief_of_staff" | "rbac_admin";

export type SearchResult = {
  chunk_id: string;
  chunk_index: number;
  page_number: number | null;
  document_id: string;
  title: string;
  title_description: string;
  snippet: string;
  score: number;
  pdf_url: string;
  metadata: Record<string, string | null>;
};

export type SearchResponse = {
  summary: string;
  summary_source: string;
  results: SearchResult[];
};

export type DocumentRecord = {
  id: string;
  title: string;
  source_filename: string;
  storage_uri: string | null;
  status: string;
  doctrine_type: string | null;
  echelon: string | null;
  mp_unit_type: string | null;
  operation_type: string | null;
  classification_level: string | null;
  publication_date: string | null;
  tags: string[];
  chunk_count: number;
  embedding_count: number;
};

export type UserRoles = {
  email: string;
  roles: string[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatSource = {
  document_id: string;
  title: string;
  page_number: number | null;
  score: number;
};

export type ChatResponse = {
  response: string;
  sources: ChatSource[];
};

export type ClientContext = {
  apiUrl: string;
  email: string;
  role: Role;
};

async function request<T>(
  context: ClientContext,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${context.apiUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-MPOST-User-Email": context.email,
      "X-MPOST-User-Role": context.role,
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function searchDocuments(
  context: ClientContext,
  body: {
    query: string;
    limit: number;
    echelon?: string | null;
    mp_unit_type?: string | null;
    operation_type?: string | null;
  },
) {
  return request<SearchResult[]>(context, "/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function searchDocumentsWithSummary(
  context: ClientContext,
  body: {
    query: string;
    limit: number;
    echelon?: string | null;
    mp_unit_type?: string | null;
    operation_type?: string | null;
  },
) {
  return request<SearchResponse>(context, "/search/summary", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function recommendForPersona(
  context: ClientContext,
  body: {
    echelon: string;
    job_title: string;
    mp_unit_type: string;
    mission_context?: string | null;
    limit: number;
  },
) {
  return request<SearchResult[]>(context, "/personas/recommendations", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listDocuments(context: ClientContext) {
  return request<DocumentRecord[]>(context, "/documents");
}

export function updateDocumentMetadata(
  context: ClientContext,
  documentId: string,
  body: Partial<DocumentRecord>,
) {
  return request<DocumentRecord>(context, `/documents/${documentId}/metadata`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function uploadDocument(
  context: ClientContext,
  body: {
    file: File;
    title: string;
    doctrine_type: string;
    mp_unit_type: string;
    tags: string;
  },
) {
  const formData = new FormData();
  formData.append("file", body.file);
  formData.append("title", body.title);
  formData.append("doctrine_type", body.doctrine_type);
  formData.append("mp_unit_type", body.mp_unit_type);
  formData.append("tags", body.tags);

  const response = await fetch(`${context.apiUrl}/documents/upload`, {
    method: "POST",
    headers: {
      "X-MPOST-User-Email": context.email,
      "X-MPOST-User-Role": context.role,
    },
    body: formData,
  });
  if (!response.ok) {
    const bodyText = await response.text();
    throw new Error(bodyText || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<DocumentRecord>;
}

export function reviewDocument(
  context: ClientContext,
  documentId: string,
  reviewStatus: "approved" | "denied",
) {
  return request<DocumentRecord>(context, `/documents/${documentId}/review`, {
    method: "POST",
    body: JSON.stringify({ status: reviewStatus }),
  });
}

export function listRoles(context: ClientContext) {
  return request<UserRoles[]>(context, "/admin/roles");
}

export function assignRole(context: ClientContext, body: { email: string; role: Role }) {
  return request<{ email: string; role: string; status: string }>(context, "/admin/roles", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function removeRole(context: ClientContext, body: { email: string; role: Role }) {
  return request<{ email: string; role: string; status: string }>(context, "/admin/roles", {
    method: "DELETE",
    body: JSON.stringify(body),
  });
}

export function setPassword(context: ClientContext, body: { email: string; password: string }) {
  return request<{ email: string; status: string }>(context, "/admin/password", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function sendChatMessage(
  context: ClientContext,
  body: {
    message: string;
    history: ChatMessage[];
    max_history?: number;
  },
) {
  return request<ChatResponse>(context, "/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export type AuthUser = {
  email: string;
  display_name: string | null;
  roles: string[];
  authenticated: boolean;
};

export async function login(apiUrl: string, email: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${apiUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<AuthUser>;
}

export async function logout(apiUrl: string): Promise<void> {
  const response = await fetch(`${apiUrl}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
}

export async function getCurrentUser(apiUrl: string): Promise<AuthUser> {
  const response = await fetch(`${apiUrl}/auth/current-user`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<AuthUser>;
}
