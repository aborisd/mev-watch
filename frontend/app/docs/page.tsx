const endpoints = [
  ["GET", "/api/v1/stats?period=24h", "Aggregated profit, attack count, victims, pools, and chart buckets."],
  ["GET", "/api/v1/events?limit=50", "Recent MEV events for the live feed and event drill-down."],
  ["GET", "/api/v1/events/stream", "Server-Sent Events stream with live MEV event notifications."],
  ["GET", "/api/v1/leaderboard?period=24h&by=profit", "Top extractors by profit or event count."],
  ["GET", "/api/v1/events/{id}", "Full event payload with metadata and transaction hashes."],
];

export default function DocsPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 md:px-6 py-8 space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <a href="/" className="text-[12px] text-zinc-500 hover:text-zinc-200">
            MEV-Watch
          </a>
          <h1 className="mt-2 text-3xl font-medium tracking-tight text-zinc-50">API docs</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
            The dashboard serves these routes from FastAPI when `API_INTERNAL_URL` is
            configured. Without a backend, the same routes return deterministic demo data.
          </p>
        </div>
        <a
          href="/"
          className="rounded-md border border-line bg-surface-raised px-3 py-1.5 text-sm text-zinc-300 hover:text-zinc-50"
        >
          Dashboard
        </a>
      </header>

      <section className="rounded-lg border border-line bg-surface-raised overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-line text-[11px] uppercase tracking-[0.08em] text-zinc-500">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Method</th>
              <th className="px-4 py-3 text-left font-medium">Route</th>
              <th className="px-4 py-3 text-left font-medium">Purpose</th>
            </tr>
          </thead>
          <tbody>
            {endpoints.map(([method, route, purpose]) => (
              <tr key={route} className="border-b border-line/60 last:border-0">
                <td className="px-4 py-3 text-emerald-300">{method}</td>
                <td className="mono px-4 py-3 text-zinc-100">{route}</td>
                <td className="px-4 py-3 text-zinc-400">{purpose}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
