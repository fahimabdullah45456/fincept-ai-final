import {useFinanceRevision} from '../financeChanges';
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthProvider';
import { ApiError } from '../auth/services/authApi';
import { overviewRequest } from './services/overviewApi';
export function useOverviewResource<T>(path: string) { const financeRevision=useFinanceRevision(); const { refresh } = useAuth(); const [attempt, setAttempt] = useState(0); const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: string;
}>({ data: null, loading: true, error: '' }); useEffect(() => { const controller = new AbortController(); setState({ data: null, loading: true, error: '' }); const timeout = setTimeout(() => controller.abort('timeout'), 15000); overviewRequest<T>(path, controller.signal).then(data => { if (!controller.signal.aborted)
    setState({ data, loading: false, error: '' }); }).catch(e => { if (controller.signal.aborted && controller.signal.reason !== 'timeout')
    return; if (e instanceof ApiError && e.status === 401) {
    void refresh();
    return;
} setState({ data: null, loading: false, error: e instanceof Error && e.name !== 'AbortError' ? e.message : 'The request timed out. Please retry.' }); }).finally(() => clearTimeout(timeout)); return () => { clearTimeout(timeout); controller.abort(); }; }, [path, attempt, refresh, financeRevision]); return { ...state, retry: () => setAttempt(v => v + 1) }; }
