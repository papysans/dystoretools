import { useEffect, useRef } from "react";

const BASE_BACKOFF = 1000;
const MAX_BACKOFF = 30_000;

export function useWebSocket<T = unknown>(channel: string, onMessage: (msg: T) => void) {
  const onMsgRef = useRef(onMessage);
  onMsgRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let cancel = false;
    let backoff = BASE_BACKOFF;
    let timer: number | null = null;

    const connect = () => {
      if (cancel) return;
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${protocol}//${location.host}/ws/${channel}`);
      ws.onmessage = (e) => {
        try {
          onMsgRef.current(JSON.parse(e.data));
        } catch {
          /* ignore non-JSON frames */
        }
      };
      ws.onopen = () => { backoff = BASE_BACKOFF; };
      ws.onclose = () => {
        if (cancel) return;
        timer = window.setTimeout(connect, backoff);
        backoff = Math.min(backoff * 2, MAX_BACKOFF);
      };
      ws.onerror = () => ws?.close();
    };
    connect();

    return () => {
      cancel = true;
      if (timer) window.clearTimeout(timer);
      ws?.close();
    };
  }, [channel]);
}
