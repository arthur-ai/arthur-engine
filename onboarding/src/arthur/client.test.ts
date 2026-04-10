import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ArthurEngineClient } from './client.js';

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function makeResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe('ArthurEngineClient', () => {
  let client: ArthurEngineClient;

  beforeEach(() => {
    client = new ArthurEngineClient('http://localhost:3030', 'test-api-key');
    mockFetch.mockReset();
  });

  describe('verifyConnection', () => {
    it('returns true for 200', async () => {
      mockFetch.mockResolvedValue(makeResponse(200, { tasks: [] }));
      expect(await client.verifyConnection()).toBe(true);
    });

    it('returns true for 401 (engine is up, auth wrong)', async () => {
      mockFetch.mockResolvedValue(makeResponse(401, {}));
      expect(await client.verifyConnection()).toBe(true);
    });

    it('returns false on network error', async () => {
      mockFetch.mockRejectedValue(new Error('ECONNREFUSED'));
      expect(await client.verifyConnection()).toBe(false);
    });

    it('returns false for 500', async () => {
      mockFetch.mockResolvedValue(makeResponse(500, {}));
      expect(await client.verifyConnection()).toBe(false);
    });
  });

  describe('login', () => {
    it('returns true for 200', async () => {
      mockFetch.mockResolvedValue(makeResponse(200, { tasks: [] }));
      expect(await client.login()).toBe(true);
    });

    it('returns false for 401', async () => {
      mockFetch.mockResolvedValue(makeResponse(401, {}));
      expect(await client.login()).toBe(false);
    });
  });

  describe('getTasks', () => {
    it('returns tasks array', async () => {
      const tasks = [{ id: 'abc', name: 'Test Task' }];
      mockFetch.mockResolvedValue(makeResponse(200, { tasks }));
      const result = await client.getTasks();
      expect(result).toEqual(tasks);
    });

    it('handles data key', async () => {
      const data = [{ id: 'abc', name: 'Test Task' }];
      mockFetch.mockResolvedValue(makeResponse(200, { data }));
      const result = await client.getTasks();
      expect(result).toEqual(data);
    });

    it('returns empty array for empty response', async () => {
      mockFetch.mockResolvedValue(makeResponse(200, {}));
      const result = await client.getTasks();
      expect(result).toEqual([]);
    });

    it('throws on non-200', async () => {
      mockFetch.mockResolvedValue(makeResponse(500, {}));
      await expect(client.getTasks()).rejects.toThrow('HTTP 500');
    });
  });

  describe('createTask', () => {
    it('creates and returns a task', async () => {
      const task = { id: 'new-task-id', name: 'My App' };
      mockFetch.mockResolvedValue(makeResponse(201, task));
      const result = await client.createTask('My App');
      expect(result).toEqual(task);

      const [url, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(url).toBe('http://localhost:3030/api/v2/tasks');
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body as string)).toEqual({ name: 'My App' });
    });

    it('sends auth header', async () => {
      mockFetch.mockResolvedValue(makeResponse(201, { id: 'x', name: 'x' }));
      await client.createTask('x');
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect((opts.headers as Record<string, string>)['Authorization']).toBe('Bearer test-api-key');
    });
  });

  describe('getTraces', () => {
    it('returns traces array', async () => {
      const traces = [{ id: 'trace-1' }];
      mockFetch.mockResolvedValue(makeResponse(200, { traces }));
      const result = await client.getTraces('task-123');
      expect(result).toEqual(traces);
    });

    it('returns empty array on error', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));
      const result = await client.getTraces('task-123');
      expect(result).toEqual([]);
    });

    it('returns empty array for non-200', async () => {
      mockFetch.mockResolvedValue(makeResponse(404, {}));
      const result = await client.getTraces('task-123');
      expect(result).toEqual([]);
    });

    it('encodes taskId in URL', async () => {
      mockFetch.mockResolvedValue(makeResponse(200, { traces: [] }));
      await client.getTraces('task with spaces');
      const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(url).toContain('task_id=task%20with%20spaces');
    });
  });

  describe('URL normalisation', () => {
    it('strips trailing slash from baseUrl', async () => {
      const c = new ArthurEngineClient('http://localhost:3030/', 'key');
      mockFetch.mockResolvedValue(makeResponse(200, {}));
      await c.verifyConnection();
      const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(url).not.toContain('//api');
    });
  });
});
