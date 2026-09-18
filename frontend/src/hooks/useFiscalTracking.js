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
    const poll = async () => {
      try {
        const current = await api.get(`/emission-jobs/${jobId}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        if (current.resource_id && Number(current.resource_id) !== Number(documentId)) throw new Error('El seguimiento no corresponde al documento.');
        setJob(current); setError('');
        const state = fiscalTrackingState(current);
        if (state.poll) {
          wasActive.current = true;
          timer = setTimeout(poll, current.status === 'contingency_pending' ? 15000 : 2500);
        } else if (wasActive.current && state.terminal && notified.current !== `${jobId}:${current.status}`) {
          notified.current = `${jobId}:${current.status}`;
          wasActive.current = false;
          complete.current?.({ background: true });
        }
      } catch (requestError) {
        if (!controller.signal.aborted) setError('No se pudo actualizar el seguimiento. Consultar de nuevo no reenvía el documento.');
      }
    };
    poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [documentId, jobId, cycle]);
  return { job, error, track, refresh: () => setCycle((value) => value + 1) };
}
