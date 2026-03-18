import axios, { AxiosInstance, AxiosError } from "axios";
import { ArthurAPIError } from "./errors";

export class ArthurAPIClient {
  private readonly http: AxiosInstance;

  constructor(baseUrl: string, apiKey: string) {
    this.http = axios.create({
      baseURL: baseUrl.replace(/\/+$/, ""),
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
    });
  }

  private handleError(err: unknown): never {
    if (err instanceof AxiosError && err.response) {
      const detail =
        err.response.data?.detail ?? err.response.statusText ?? String(err);
      throw new ArthurAPIError(err.response.status, String(detail));
    }
    throw err;
  }

  async getPromptByVersion(
    taskId: string,
    name: string,
    version: string,
  ): Promise<Record<string, any>> {
    try {
      const resp = await this.http.get(
        `/api/v1/tasks/${taskId}/prompts/${encodeURIComponent(name)}/versions/${encodeURIComponent(version)}`,
      );
      return resp.data;
    } catch (err) {
      this.handleError(err);
    }
  }

  async getPromptByTag(
    taskId: string,
    name: string,
    tag: string,
  ): Promise<Record<string, any>> {
    try {
      const resp = await this.http.get(
        `/api/v1/tasks/${taskId}/prompts/${encodeURIComponent(name)}/versions/tags/${encodeURIComponent(tag)}`,
      );
      return resp.data;
    } catch (err) {
      this.handleError(err);
    }
  }

  async renderPrompt(
    taskId: string,
    name: string,
    version: string,
    variables: Record<string, string>,
    strict: boolean = false,
  ): Promise<Record<string, any>> {
    const body = {
      completion_request: {
        variables: Object.entries(variables).map(([k, v]) => ({
          name: k,
          value: v,
        })),
        strict,
      },
    };
    try {
      const resp = await this.http.post(
        `/api/v1/tasks/${taskId}/prompts/${encodeURIComponent(name)}/versions/${encodeURIComponent(version)}/renders`,
        body,
      );
      return resp.data;
    } catch (err) {
      this.handleError(err);
    }
  }

  async resolveTaskId(taskName: string): Promise<string> {
    const pageSize = 50;
    let page = 0;
    let totalCount = 0;

    while (true) {
      let result: any;
      try {
        const resp = await this.http.post(
          `/api/v2/tasks/search`,
          { task_name: taskName },
          { params: { page_size: pageSize, page } },
        );
        result = resp.data;
      } catch (err) {
        this.handleError(err);
      }

      for (const task of result.tasks) {
        if (task.name === taskName) {
          return String(task.id);
        }
      }

      totalCount = result.count;
      if (pageSize * (page + 1) >= totalCount) {
        break;
      }
      page++;
    }

    throw new Error(
      `No task with an exact name match for '${taskName}' was found. ` +
        `Found ${totalCount} task(s) whose name contains '${taskName}' as a substring.`,
    );
  }

  close(): void {
    // axios does not require explicit cleanup
  }
}
