import { useState } from 'react';
import { CheckCircle2, ExternalLink, KeyRound, Loader2, PlugZap, XCircle } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { useToast } from '../hooks/useToast';
import { getApiKey, isApiKeyRemembered, setApiKey } from '../services/api';
import { systemService } from '../services/studentService';

export default function SettingsPage() {
  const toast = useToast();
  const [key, setKey] = useState(getApiKey);
  const [remember, setRemember] = useState(isApiKeyRemembered);
  const [checking, setChecking] = useState(false);
  const [health, setHealth] = useState(null);

  const save = (event) => {
    event.preventDefault();
    setApiKey(key.trim(), { remember });
    toast.success(key.trim() ? 'Admin API key saved for this browser.' : 'Admin API key removed.', 'Settings saved');
  };

  const checkConnection = async () => {
    setChecking(true);
    try {
      setHealth({ ok: true, ...(await systemService.health()) });
    } catch (err) {
      setHealth({ ok: false, message: err.message });
    } finally {
      setChecking(false);
    }
  };

  const docsUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/docs`;

  return (
    <>
      <PageHeader title="Settings" breadcrumbs={[{ label: 'Settings' }]} description="Connection and access settings." />

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-6" aria-labelledby="key-heading">
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 id="key-heading" className="text-base font-semibold text-ink">
              Admin access
            </h2>
          </div>
          <p className="mt-2 text-sm text-secondary">
            Adding, editing, deactivating, importing and exporting students requires the admin API key configured on
            the server (<code className="text-xs">ADMIN_API_KEY</code>). Viewing does not.
          </p>
          <form onSubmit={save} className="mt-4 space-y-4">
            <div>
              <label htmlFor="api-key" className="field-label">
                Admin API key
              </label>
              <input
                id="api-key"
                type="password"
                autoComplete="off"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                className="field-input"
                placeholder="Paste the key from your administrator"
              />
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="mt-0.5 accent-primary"
              />
              <span>
                <span className="font-medium text-ink">Remember on this browser</span>
                <span className="block text-secondary">
                  Otherwise the key is forgotten when this tab is closed. Don't use on shared computers.
                </span>
              </span>
            </label>
            <button type="submit" className="btn-primary">
              Save
            </button>
          </form>
        </section>

        <section className="card p-6" aria-labelledby="conn-heading">
          <div className="flex items-center gap-2">
            <PlugZap className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 id="conn-heading" className="text-base font-semibold text-ink">
              API connection
            </h2>
          </div>
          <p className="mt-2 text-sm text-secondary">Check that the backend and PostgreSQL database are reachable.</p>
          <button type="button" className="btn-secondary mt-4" onClick={checkConnection} disabled={checking}>
            {checking && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Test connection
          </button>

          {health && (
            <div
              role="status"
              className={`mt-4 flex items-start gap-2 rounded-lg border p-3 text-sm ${
                health.ok ? 'border-teal-200 bg-primary-soft text-primary' : 'border-red-200 bg-red-50 text-red-700'
              }`}
            >
              {health.ok ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              ) : (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              )}
              <span>
                {health.ok
                  ? `API online, database ${health.database}. Write protection is ${
                      health.write_protection ? 'enabled' : 'DISABLED (development mode)'
                    }.`
                  : health.message}
              </span>
            </div>
          )}

          <a href={docsUrl} target="_blank" rel="noreferrer" className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
            Open API documentation (Swagger UI) <ExternalLink className="h-4 w-4" aria-hidden="true" />
          </a>
        </section>
      </div>
    </>
  );
}
