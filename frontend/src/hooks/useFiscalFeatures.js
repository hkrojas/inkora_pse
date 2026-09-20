import { useEffect, useState } from "react";
import { tenant } from "../services/tenant";

let cachedFlags = null;
let cachedAt = 0;
let cachedToken = null;
let pendingRequest = null;
const CACHE_TTL_MS = 30_000;

function authToken() {
  return localStorage.getItem("token") || sessionStorage.getItem("token");
}

function loadFlags({ force = false } = {}) {
  const token = authToken();
  if (cachedToken !== token) {
    cachedFlags = null;
    cachedAt = 0;
    cachedToken = token;
  }
  const isFresh = cachedFlags && Date.now() - cachedAt < CACHE_TTL_MS;
  if (!force && isFresh) return Promise.resolve(cachedFlags);
  if (!pendingRequest) {
    pendingRequest = tenant
      .subscriptionStatus()
      .then((response) => {
        cachedFlags = response?.fiscal_feature_flags || {};
        cachedAt = Date.now();
        return cachedFlags;
      })
      .finally(() => {
        pendingRequest = null;
      });
  }
  return pendingRequest;
}

export function useFiscalFeatures() {
  const [flags, setFlags] = useState(cachedFlags || {});
  const [loading, setLoading] = useState(!cachedFlags);

  useEffect(() => {
    let active = true;
    const refresh = (force = false) =>
      loadFlags({ force })
        .then((nextFlags) => {
          if (active) setFlags(nextFlags);
        })
        .catch(() => {
          if (active && !cachedFlags) setFlags({});
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") refresh(true);
    };
    refresh();
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      active = false;
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);

  return {
    flags,
    loading,
    isEnabled: (feature) => flags?.[feature] === true,
  };
}
