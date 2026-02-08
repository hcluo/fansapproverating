import Link from 'next/link';

async function getPlayers(query) {
  const url = `http://backend:8000/players${query ? `?query=${encodeURIComponent(query)}` : ''}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

export default async function Home({ searchParams }) {
  const q = searchParams?.q ?? '';
  const players = await getPlayers(q);
  return (
    <main>
      <h1>NBA Sentiment Ratings</h1>
      <form>
        <input name="q" defaultValue={q} placeholder="Search players" />
        <button type="submit">Search</button>
      </form>
      <ul>
        {players.map((p) => (
          <li key={p.id}>
            <Link href={`/players/${p.id}`}>{p.full_name}</Link> ({p.team || 'N/A'})
          </li>
        ))}
      </ul>
    </main>
  );
}
