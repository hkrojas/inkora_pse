import { useEffect, useState } from "react";
import { tenant } from "../services/tenant";

let cachedFlags = null;
let pendingRequest = null;

function loadFlags() {
  if (cachedFlags) return Promise.resolve(cachedFlags);
  if (!pendingRequest) {
    pendingRequest = tenant
      .subscriptionStatus()
      .then((response) => {
        cachedFlags = response?.fiscal_feature_flags || {};
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
    loadFlags()
      .then((nextFlags) => {
        if (active) setFlags(nextFlags);
      })
      .catch(() => {
        if (active) setFlags({});
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return {
    flags,
    loading,
    isEnabled: (feature) => flags?.[feature] === true,
  };
}
