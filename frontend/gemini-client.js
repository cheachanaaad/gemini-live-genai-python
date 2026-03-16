/**
 * GeminiClient: Handles WebSocket communication
 */
class GeminiClient {
  constructor(config) {
    this.websocket = null;
    this.onOpen = config.onOpen;
    this.onMessage = config.onMessage;
    this.onClose = config.onClose;
    this.onError = config.onError;
    this.heartbeatInterval = null;
    this.heartbeatMs = 5000;
  }

  connect() {
    if (this.websocket) {
      try {
        this.websocket.close(1000, "reconnect");
      } catch (error) {
        console.warn("Failed to close existing websocket before reconnect", error);
      }
      this.websocket = null;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.websocket = new WebSocket(wsUrl);
    this.websocket.binaryType = "arraybuffer";

    this.websocket.onopen = () => {
      this.startHeartbeat();
      if (this.onOpen) this.onOpen();
    };

    this.websocket.onmessage = (event) => {
      if (this.onMessage) this.onMessage(event);
    };

    this.websocket.onclose = (event) => {
      this.stopHeartbeat();
      if (this.onClose) this.onClose(event);
    };

    this.websocket.onerror = (event) => {
      if (this.onError) this.onError(event);
    };
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(
          JSON.stringify({
            type: "heartbeat",
            ts: Date.now(),
          })
        );
      }
    }, this.heartbeatMs);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  send(data) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(data);
    }
  }

  sendText(text) {
    this.send(JSON.stringify({ text: text }));
  }

  sendImage(base64Data, mimeType = "image/jpeg") {
    this.send(
      JSON.stringify({
        type: "image",
        mime_type: mimeType,
        data: base64Data,
      })
    );
  }

  disconnect(code = 1000, reason = "client_disconnect") {
    this.stopHeartbeat();
    if (this.websocket) {
      try {
        if (this.websocket.readyState === WebSocket.OPEN) {
          this.websocket.send(
            JSON.stringify({
              type: "client_disconnect",
              reason,
            })
          );
        }
      } catch (error) {
        console.warn("Failed to send disconnect notice", error);
      }
      try {
        this.websocket.close(code, reason);
      } catch (error) {
        console.warn("Failed to close websocket cleanly", error);
      }
      this.websocket = null;
    }
  }

  isConnected() {
    return this.websocket && this.websocket.readyState === WebSocket.OPEN;
  }
}
