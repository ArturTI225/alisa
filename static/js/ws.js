/*
  Lightweight reconnecting WebSocket wrapper for LaUsaTa.
  Exposes window.laWS with:
    laWS.connect(path, {onEvent, onStatus})  → {close()}

  - path:     relative WS path (e.g. "/ws/chat/42/")
  - onEvent:  called with a parsed JSON payload for every server message
  - onStatus: optional, called with "open" | "closed" | "reconnecting"

  Uses exponential backoff (1s → 30s cap) and reconnects forever while the
  page is open. Safe to call multiple times; each returned handle owns one
  socket and one reconnect timer.
*/
(function (global) {
  "use strict";

  const MAX_DELAY = 30000;
  const START_DELAY = 1000;

  function wsUrlFor(path) {
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    return scheme + "//" + location.host + path;
  }

  function connect(path, { onEvent, onStatus } = {}) {
    let socket = null;
    let closed = false;
    let delay = START_DELAY;
    let retryTimer = null;

    function setStatus(s) {
      if (typeof onStatus === "function") onStatus(s);
    }

    function open() {
      if (closed) return;
      socket = new WebSocket(wsUrlFor(path));

      socket.addEventListener("open", () => {
        delay = START_DELAY;
        setStatus("open");
      });

      socket.addEventListener("message", (ev) => {
        if (typeof onEvent !== "function") return;
        let data;
        try {
          data = JSON.parse(ev.data);
        } catch (err) {
          console.warn("laWS: bad JSON", ev.data);
          return;
        }
        onEvent(data);
      });

      socket.addEventListener("close", (ev) => {
        setStatus("closed");
        if (closed) return;
        if (ev.code === 4401 || ev.code === 4403) {
          // auth / permission denial — no point reconnecting
          closed = true;
          return;
        }
        setStatus("reconnecting");
        retryTimer = setTimeout(open, delay);
        delay = Math.min(delay * 2, MAX_DELAY);
      });

      socket.addEventListener("error", () => {
        // close handler will take care of reconnect
      });
    }

    open();

    return {
      send(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(typeof payload === "string" ? payload : JSON.stringify(payload));
          return true;
        }
        return false;
      },
      close() {
        closed = true;
        if (retryTimer) clearTimeout(retryTimer);
        if (socket) socket.close();
      },
    };
  }

  global.laWS = { connect };
})(window);
