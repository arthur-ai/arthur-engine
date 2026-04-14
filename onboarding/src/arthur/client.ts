export interface Task {
  id: string;
  name: string;
  created_at?: string;
  status?: string;
}

export interface Trace {
  trace_id: string;
  task_id?: string;
  created_at?: string;
}

export interface TraceCheckResult {
  traces: Trace[];
  error?: string;
}

export interface SpanDetail {
  span_name: string | null;
  span_kind?: string | null;
  input_content: string | null;
  output_content: string | null;
  children?: SpanDetail[];
}

export interface TraceDetail {
  trace_id: string;
  root_spans?: SpanDetail[];
}

export interface ModelProviderInfo {
  provider: string;
  enabled: boolean;
}

export interface CreatedLlmEval {
  name: string;
  version: number;
}

export interface CreatedTransform {
  id: string;
  name: string;
}

export interface CreatedContinuousEval {
  id: string;
  name: string;
}

interface TaskListResponse {
  tasks?: Task[];
  data?: Task[];
  page?: number;
  page_size?: number;
  total?: number;
}

interface TraceListResponse {
  traces?: Trace[];
  data?: Trace[];
}

interface ModelProviderListResponse {
  providers?: ModelProviderInfo[];
}

export class ArthurEngineClient {
  private baseUrl: string;

  constructor(
    baseUrl: string,
    private apiKey: string,
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private get headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
    };
  }

  /** Returns true if the engine is reachable (regardless of auth status). */
  async verifyConnection(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v2/tasks?page=0&page_size=1`, {
        headers: this.headers,
        signal: AbortSignal.timeout(10_000),
      });
      // 200 = up and authed, 401 = up but wrong key — either way it's reachable
      return res.status === 200 || res.status === 401;
    } catch {
      return false;
    }
  }

  /** Returns true if the API key is valid. */
  async login(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v2/tasks?page=0&page_size=1`, {
        headers: this.headers,
        signal: AbortSignal.timeout(10_000),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async getTasks(): Promise<Task[]> {
    const res = await fetch(`${this.baseUrl}/api/v2/tasks`, {
      headers: this.headers,
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) throw new Error(`Failed to get tasks: HTTP ${res.status}`);
    const data = (await res.json()) as TaskListResponse;
    return data.tasks ?? data.data ?? [];
  }

  async createTask(name: string): Promise<Task> {
    const res = await fetch(`${this.baseUrl}/api/v2/tasks`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ name }),
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new Error(`Failed to create task: HTTP ${res.status} ${body}`);
    }
    return (await res.json()) as Task;
  }

  async getTraces(taskId: string): Promise<TraceCheckResult> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/traces?task_ids=${encodeURIComponent(taskId)}&page_size=5`,
        {
          headers: this.headers,
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        return { traces: [], error: `HTTP ${res.status}: ${body}` };
      }
      const data = (await res.json()) as TraceListResponse;
      return { traces: data.traces ?? data.data ?? [] };
    } catch (err) {
      return { traces: [], error: err instanceof Error ? err.message : String(err) };
    }
  }

  async getTraceDetail(traceId: string): Promise<TraceDetail | null> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/traces/${encodeURIComponent(traceId)}`,
        {
          headers: this.headers,
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) return null;
      return (await res.json()) as TraceDetail;
    } catch {
      return null;
    }
  }

  async getModelProviders(): Promise<ModelProviderInfo[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/model_providers`, {
        headers: this.headers,
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) return [];
      const data = (await res.json()) as ModelProviderListResponse;
      return data.providers ?? [];
    } catch {
      return [];
    }
  }

  async createLlmEval(
    taskId: string,
    evalSlug: string,
    body: { model_name: string; model_provider: string; instructions: string },
  ): Promise<{ eval?: CreatedLlmEval; error?: string }> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/tasks/${encodeURIComponent(taskId)}/llm_evals/${encodeURIComponent(evalSlug)}`,
        {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        return { error: `HTTP ${res.status}: ${text}` };
      }
      return { eval: (await res.json()) as CreatedLlmEval };
    } catch (err) {
      return { error: err instanceof Error ? err.message : String(err) };
    }
  }

  async createTransform(
    taskId: string,
    body: {
      name: string;
      definition: {
        variables: Array<{
          variable_name: string;
          span_name: string;
          attribute_path: string;
          fallback?: string;
        }>;
      };
    },
  ): Promise<{ transform?: CreatedTransform; error?: string }> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/tasks/${encodeURIComponent(taskId)}/traces/transforms`,
        {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        return { error: `HTTP ${res.status}: ${text}` };
      }
      return { transform: (await res.json()) as CreatedTransform };
    } catch (err) {
      return { error: err instanceof Error ? err.message : String(err) };
    }
  }

  async createContinuousEval(
    taskId: string,
    body: {
      name: string;
      llm_eval_name: string;
      llm_eval_version: string;
      transform_id: string;
      transform_variable_mapping: Array<{ transform_variable: string; eval_variable: string }>;
      enabled: boolean;
    },
  ): Promise<{ continuousEval?: CreatedContinuousEval; error?: string }> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/tasks/${encodeURIComponent(taskId)}/continuous_evals`,
        {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        return { error: `HTTP ${res.status}: ${text}` };
      }
      return { continuousEval: (await res.json()) as CreatedContinuousEval };
    } catch (err) {
      return { error: err instanceof Error ? err.message : String(err) };
    }
  }

  async configureModelProvider(
    provider: string,
    credentials: { api_key: string },
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/model_providers/${encodeURIComponent(provider)}`,
        {
          method: 'PUT',
          headers: this.headers,
          body: JSON.stringify({ api_key: credentials.api_key }),
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        return { success: false, error: `HTTP ${res.status}: ${text}` };
      }
      return { success: true };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : String(err) };
    }
  }
}
