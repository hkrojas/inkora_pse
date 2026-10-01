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
  const wasActive = useRef(false);
  const track = useCallback((actions) => {
    if (actions?.job_id) {
      const next = { id: actions.job_id, status: actions.job_status || 'queued', action: actions.job_action };
      wasActive.current = fiscalTrackingState(next).poll;
      setJob(next);
    }
  }, []);
  useEffect(() => { setJob(null); setError(''); notified.current = ''; wasActive.current = false; }, [documentId]);
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
        if (state.poll) {
          wasActive.current = true;
          timer = setTimeout(poll, ['retry', 'contingency_pending', 'pending_confirmation'].includes(current.status) ? 30000 : 5000);
        } else if (wasActive.current && state.terminal && notified.current !== `${jobId}:${current.status}`) {
          notified.current = `${jobId}:${current.status}`;
          wasActive.current = false;
          complete.current?.({ background: true });
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
