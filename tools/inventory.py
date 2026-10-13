"""배포된 사이트(정적 HTML, 루트 절대경로)에서 글 목록·주제·템플릿 조각을 추출한다."""
import json, re, sys, glob, os, html


def grab(pat, s, flags=re.S):
    m = re.search(pat, s, flags)
    return m.group(1) if m else None


def inventory(site_dir):
    site_dir = site_dir.rstrip('/')
    thumbs = {}
    lists = [os.path.join(site_dir, 'blog/index.html')] + glob.glob(os.path.join(site_dir, 'blog/page/*/index.html')) \
        + glob.glob(os.path.join(site_dir, 'blog/topic/*/index.html')) + glob.glob(os.path.join(site_dir, 'blog/topic/*/page/*/index.html'))
    for lp in lists:
        s = open(lp, encoding='utf-8').read()
        for li in re.findall(r'<li class="post-item">(.*?)</li>', s, re.S):
            slug = grab(r'/journal/([^/"]+)/', li)
            thumb = grab(r'^\s*(<a href="[^"]+">.*?</a>)\s*<div>', li)
            if slug and thumb:
                thumbs.setdefault(slug, thumb)
    posts = {}
    for jp in sorted(glob.glob(os.path.join(site_dir, 'journal/*/index.html'))):
        s = open(jp, encoding='utf-8').read()
        slug = jp.split('/')[-2]
        posts[slug] = dict(
            slug=slug,
            title=html.unescape(grab(r'<h1>(.*?)</h1>', s)),
            date=grab(r'article:published_time" content="([^"]+)"', s),
            summary=html.unescape(grab(r'<meta name="description" content="([^"]*)"', s)),
            topic=grab(r'/blog/topic/([^/]+)/">[^<]+</a></p>\s*<h1>', s),
            section=html.unescape(grab(r'article:section" content="([^"]*)"', s) or ''),
            thumb=thumbs.get(slug),
            risk=grab(r'(<div class="risk">.*?</div>)', s),
            disclaimer=grab(r'(<p class="disclaimer">.*?</p>)', s),
            hub=grab(r'<a class="hub-link" href="([^"]+)">', s),
            hub_text=html.unescape(grab(r'<a class="hub-link" href="[^"]+">(.*?)</a>', s) or ''),
            body=grab(r'<div class="body">(.*?)</div>', s),
        )
    b = open(os.path.join(site_dir, 'blog/index.html'), encoding='utf-8').read()

    nav = re.search(r'<nav class="topics".*?</nav>', b, re.S).group(0)
    topics = re.findall(r'/blog/topic/([^/]+)/"[^>]*>([^<]+)</a>', nav)
    home = open(os.path.join(site_dir, 'index.html'), encoding='utf-8').read()
    site = dict(
        domain=grab(r'<link rel="canonical" href="(https://[^/]+)/', home),
        app_name=grab(r'<meta name="application-name" content="([^"]+)"', home),
        clinic=grab(r'"@type":"MedicalClinic"[^}]*?"name":"([^"]+)"', home),
        author=html.unescape(grab(r'</time> · ([^<]+)</div>', b) or ''),
        topics=[dict(slug=t, label=html.unescape(l)) for t, l in topics],
    )
    return site, posts


if __name__ == '__main__':
    site, posts = inventory(sys.argv[1])
    out = dict(site=site, posts=sorted(({k: v for k, v in p.items() if k != 'body'} for p in posts.values()), key=lambda p: (p['date'], p['slug'])))
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(site['domain'], site['app_name'], site['clinic'], len(posts), [t['slug'] for t in site['topics']])
    print('missing thumb/topic:', [p['slug'] for p in posts.values() if not p['thumb'] or not p['topic']])
