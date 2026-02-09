from datetime import datetime, timezone

from app.services.forum_ingest import parse_rss_items, parse_thread_html


def test_parse_rss_items_extracts_thread_id():
    xml = """
    <rss>
      <channel>
        <item>
          <title>Game thread</title>
          <link>https://bbs.clutchfans.net/threads/clutchfans-game-thread.123456/</link>
          <pubDate>Sun, 08 Feb 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    items = parse_rss_items(xml)
    assert len(items) == 1
    assert items[0].external_id == "123456"


def test_parse_thread_html_extracts_posts_and_last_page():
    html = """
    <html>
      <body>
        <nav>
          <a class="pageNav-page">1</a>
          <a class="pageNav-page">3</a>
        </nav>
        <article class="message" id="post-111">
          <header>
            <a class="username">UserA</a>
            <time datetime="2026-02-08T12:00:00Z"></time>
          </header>
          <div class="message-body">
            <div class="bbWrapper">
              Hello
              <blockquote>Quoted</blockquote>
              Rockets win!
            </div>
            <div class="message-signature">sig</div>
          </div>
          <div class="reactionsBar-summary" data-score="5">5</div>
        </article>
        <article class="message" data-content="post-222">
          <time data-time="1760000000"></time>
          <div class="message-body">
            <div class="bbWrapper">Second post</div>
          </div>
        </article>
      </body>
    </html>
    """
    posts, last_page = parse_thread_html(html, "https://bbs.clutchfans.net/threads/test.123/")
    assert last_page == 3
    assert len(posts) == 2
    assert posts[0].external_id == "111"
    assert posts[0].score == 5
    assert posts[0].author == "UserA"
    assert "Quoted" not in posts[0].body
    assert "sig" not in posts[0].body
    assert posts[1].external_id == "222"
    assert posts[1].created_at == datetime.fromtimestamp(1760000000, tz=timezone.utc)
