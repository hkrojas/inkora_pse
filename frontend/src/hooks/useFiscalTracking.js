import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/utils/api';
import { fiscalTrackingState } from '../lib/utils/fiscalTracking';

export default function useFiscalTracking(documentId, onComplete) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [cycle, setCycle] = useState(0);
  const complete = useRef(onComplete);
  complete.current = onComplete;
  const notified = useRef('');
  const refreshed = useRef({ jobId: null, signature: '', at: 0 });
  const track = useCallback((actions) => {
    if (actions?.job_id) {
      const next = { id: actions.job_id, status: actions.job_status || 'queued', action: actions.job_action };
      setJob(next);
    }
  }, []);
  useEffect(() => { setJob(null); setError(''); notified.current = ''; refreshed.current = { jobId: null, signature: '', at: 0 }; }, [documentId]);
  const jobId = job?.id;
  useEffect(() => {
    if (!jobId) return undefined;
    const controller = new AbortController();
    let timer;
    let inFlight = false;
    const poll = async () => {
      if (inFlight || controller.signal.aborted) return;
      clearTimeout(timer);
      if (document.visibilityState === 'hidden' || navigator.onLine === false) return;
      inFlight = true;
      try {
        const current = await api.get(`/emission-jobs/${jobId}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        if (current.resource_id && Number(current.resource_id) !== Number(documentId)) throw new Error('El seguimiento no corresponde al documento.');
        setJob(current); setError('');
        const state = fiscalTrackingState(current);
        const signature = JSON.stringify([jobId, current.status, current.action, current.updated_at]);
        const previous = refreshed.current;
        const terminalKey = `${jobId}:${current.status}`;
        const shouldRefresh = state.terminal
          ? notified.current !== terminalKey
          : previous.jobId !== jobId || (previous.signature !== signature && Date.now() - previous.at >= 15000);
        if (shouldRefresh) {
          // Keep the last *refreshed* signature: a throttled change is picked
          // up on a later poll even if the job stops changing in the meantime.
          const loaded = await complete.current?.({ background: true });
          if (loaded === false) throw new Error('La actualización del documento quedó pendiente.');
          if (controller.signal.aborted) return;
          refreshed.current = { jobId, signature, at: Date.now() };
          if (state.terminal) notified.current = terminalKey;
        }
        if (controller.signal.aborted) return;
        if (state.poll) {
          timer = setTimeout(poll, ['retry', 'contingency_pending', 'pending_confirmation'].includes(current.status) ? 30000 : 5000);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError('No se pudo actualizar el seguimiento. Se intentará nuevamente.');
          timer = setTimeout(poll, 30000);
        }
      } finally {
        inFlight = false;
      }
    };
    const resume = () => { if (document.visibilityState !== 'hidden') poll(); };
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('online', resume);
    poll();
    return () => {
      controller.abort(); clearTimeout(timer);
      document.removeEventListener('visibilitychange', resume);
      window.removeEventListener('online', resume);
    };
  }, [documentId, jobId, cycle]);
  return { job, error, track, refresh: () => setCycle((value) => value + 1) };
}
