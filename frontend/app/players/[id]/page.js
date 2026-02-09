import MetricsChart from '../../../components/metrics-chart';

async function getPlayer(id) {
  const res = await fetch(`http://backend:8000/players/${id}`, { cache: 'no-store' });
  return res.json();
}

async function getMetrics(id) {
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - 14);
  const q = `from=${from.toISOString().slice(0, 10)}&to=${to.toISOString().slice(0, 10)}`;
  const res = await fetch(`http://backend:8000/players/${id}/metrics?${q}`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

async function getNarrative(id, date) {
  const res = await fetch(`http://backend:8000/players/${id}/narratives?date=${date}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export default async function PlayerDetail({ params }) {
  const player = await getPlayer(params.id);
  const metrics = await getMetrics(params.id);
  const narrativeDate = metrics.length ? metrics[metrics.length - 1].date : new Date().toISOString().slice(0, 10);
  const narrative = await getNarrative(params.id, narrativeDate);

  return (
    <main>
      <h1>{player.full_name}</h1>
      <p>Team: {player.team || 'N/A'}</p>
      <h2>Sentiment Trend</h2>
      <MetricsChart data={metrics} />
      <h3>Top Narratives</h3>
      {narrative ? (
        <>
          <p>{narrative.summary}</p>
          <p>Date: {narrative.date}</p>
          <ul>
            {Object.entries(narrative.top_terms_json || {}).map(([term, count]) => (
              <li key={term}>
                {term}: {count}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>No narratives available yet.</p>
      )}
    </main>
  );
}
