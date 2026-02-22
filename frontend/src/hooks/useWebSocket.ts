import { useEffect } from "react";

interface WebSocketMessage {
  channel: string;
  data: unknown;
}

export function useWebSocket(
  wsUrl: string,
  channel: string,
  token: string | null,
  onMessage: (message: WebSocketMessage) => void
) {
  useEffect(() => {
    if (!token) {
      return;
    }

    const socket = new WebSocket(`${wsUrl}/ws/${channel}?token=${token}`);
    const heartbeat = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 10_000);

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as WebSocketMessage;
        onMessage(parsed);
      } catch {
        // Ignore malformed frames.
      }
    };

    return () => {
      window.clearInterval(heartbeat);
      socket.close();
    };
  }, [wsUrl, channel, token, onMessage]);
}
