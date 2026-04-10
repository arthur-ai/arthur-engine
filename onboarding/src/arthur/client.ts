export interface Task {
  id: string;
  name: string;
  created_at?: string;
  status?: string;
}

export interface Trace {
  id: string;
  task_id?: string;
  created_at?: string;
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

  async getTraces(taskId: string): Promise<Trace[]> {
    try {
      const res = await fetch(
        `${this.baseUrl}/api/v1/traces?task_id=${encodeURIComponent(taskId)}&page_size=5`,
        {
          headers: this.headers,
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!res.ok) return [];
      const data = (await res.json()) as TraceListResponse;
      return data.traces ?? data.data ?? [];
    } catch {
      return [];
    }
  }
}
