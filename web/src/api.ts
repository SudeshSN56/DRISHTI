import type { DetectSSEEvent, ModelInfo, RunDetail, RunSummary, SampleVideo } from './types';

const API_BASE = '/api';

export async function fetchModelInfo(): Promise<ModelInfo> {
  const res = await fetch(`${API_BASE}/model/info`);
  if (!res.ok) throw new Error(`Failed to fetch model info: ${res.statusText}`);
  return res.json();
}

export async function fetchSampleVideos(): Promise<SampleVideo[]> {
  const res = await fetch(`${API_BASE}/model/sample-videos`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.statusText}`);
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}`);
  if (!res.ok) throw new Error(`Failed to fetch run ${runId}: ${res.statusText}`);
  return res.json();
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete run: ${res.statusText}`);
}

export async function generateBrief(runId: string): Promise<{ path: string; filename: string }> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}/brief`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to generate brief PDF: ${res.statusText}`);
  return res.json();
}

export function getFileUrl(runId: string, filePath: string): string {
  return `${API_BASE}/runs/${encodeURIComponent(runId)}/files/${filePath}`;
}

export function startDetectionStream(
  file: File | null,
  samplePath: string | null,
  classes: string[],
  onEvent: (event: DetectSSEEvent) => void,
  onError: (err: Error) => void
): () => void {
  const controller = new AbortController();
  const formData = new FormData();

  if (file) {
    formData.append('file', file);
  } else if (samplePath) {
    formData.append('sample_path', samplePath);
  }
  formData.append('classes', JSON.stringify(classes));

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/detect`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Detection request failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Response body stream is not available');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data:')) {
            const jsonStr = trimmed.slice(5).trim();
            try {
              const data = JSON.parse(jsonStr) as DetectSSEEvent;
              onEvent(data);
            } catch (parseErr) {
              console.error('Failed to parse SSE data:', jsonStr, parseErr);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    }
  })();

  return () => controller.abort();
}
