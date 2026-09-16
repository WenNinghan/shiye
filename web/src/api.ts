export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    ...init,
    headers: {
      ...(init.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "网络连接失败，请检查本机服务" }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "输入格式不正确，请检查填写内容",
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
export const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});
export const imageUrl = (docId: string, pageId: string, version: number) =>
  `/api/documents/${docId}/pages/${pageId}/image?v=${version}`;
