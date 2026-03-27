import { useEffect, useRef } from "react";

/**
 * Calls `callback` immediately and then every `intervalMs` milliseconds.
 * Pauses automatically when the page is hidden (tab in background).
 */
export function useAutoRefresh(callback, intervalMs = 30000) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    let id;

    function startInterval() {
      id = setInterval(() => {
        if (document.visibilityState !== "hidden") {
          savedCallback.current();
        }
      }, intervalMs);
    }

    function handleVisibility() {
      if (document.visibilityState === "visible") {
        savedCallback.current(); // Immediate refresh on tab focus
        clearInterval(id);
        startInterval();
      } else {
        clearInterval(id);
      }
    }

    savedCallback.current(); // Initial load
    startInterval();
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [intervalMs]);
}
