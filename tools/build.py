"""배포된 병원 정보 사이트(저장소 main)에 새 글(JSON)을 더한다. 증분 방식.

  python3 tools/build.py <repo_dir> <posts.json> [<posts.json> ...]

- repo_dir 안의 현재 글(HTML)을 읽어 목록을 만들고, JSON의 새 글을 같은 템플릿으로 추가한다.
- 블로그 목록(10편/페이지)·주제 목록(20편/페이지)·sitemap.xml·rss.xml(최신 30편)을 다시 만든다.
- 모든 글 하단에 대표 키워드 백링크 1줄을 넣는다(없을 때만).
- 날짜는 JSON 파일명 앞 10자(YYYY-MM-DD). 같은 제목이 이미 있으면 건너뛴다.
"""
import json, re, os, sys, glob, html, shutil, datetime
from email.utils import format_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory import inventory

PER_PAGE, TOPIC_PER_PAGE = 10, 20
KST = datetime.timezone(datetime.timedelta(hours=9))
esc = lambda s: html.escape(s, quote=True)


def read(p):
    return open(p, encoding='utf-8').read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(s)


def kdate(d):
    y, m, dd = d.split('-')
    return f'{int(y)}년 {int(m)}월 {int(dd)}일'


def render_body(p):
    out = []
    for i, sec in enumerate(p['sections']):
        out.append(f'<h2 id="s{i+1}">{esc(sec["h"])}</h2>')
        out += [f'<p>{esc(x)}</p>' for x in sec['paras']]
    return '\n'.join(out)


def list_item(p, eager):
    thumb = p['thumb']
    thumb = thumb.replace('loading="lazy"', 'loading="eager"') if eager else thumb.replace('loading="eager"', 'loading="lazy"')
    return f'''
      <li class="post-item">
        {thumb}
        <div>
          <div class="cat">{esc(p['section'])}</div>
          <h2><a href="/journal/{p['slug']}/">{esc(p['title'])}</a></h2>
          <div class="meta"><time datetime="{p['date']}">{kdate(p['date'])}</time> · {esc(p['author'])}</div>
          <p>{esc(p['summary'])}</p>
          <a href="/journal/{p['slug']}/">더 읽기 →</a>
        </div>
      </li>
      '''


def pager(cur, total, base):
    if total <= 1:
        return ''
    url = lambda n: f'{base}' if n == 1 else f'{base}page/{n}/'
    parts = [f'<a href="{url(cur-1)}">← 이전</a>'] if cur > 1 else []
    nums = []
    for n in range(1, total + 1):
        if n in (1, total) or abs(n - cur) <= 2:
            nums.append(f'<span aria-current="page">{n}</span>' if n == cur else f'<a href="{url(n)}">{n}</a>')
        elif nums[-1] != '<span>…</span>':
            nums.append('<span>…</span>')
    parts.append(''.join(nums))
    if cur < total:
        parts.append(f'<a href="{url(cur+1)}">다음 →</a>')
    return '\n    <nav class="pager" aria-label="페이지 이동">\n      ' + '\n      '.join(parts) + '\n    </nav>\n    '


def list_page(tpl, items, pager_html, n, canonical):
    t = re.sub(r'<ul class="post-list">.*?</ul>', lambda m: '<ul class="post-list">' + items + '</ul>', tpl, count=1, flags=re.S)
    t = re.sub(r'\s*<nav class="pager".*?</nav>\s*', '\n    ', t, count=1, flags=re.S)
    if pager_html:
        t = t.replace('</ul>\n', '</ul>\n' + pager_html, 1)
    t = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda m: m.group(1) + canonical, t, count=1)
    t = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + canonical, t, count=1)
    t = re.sub(r'("@type":"CollectionPage"[^}]*?"url":")[^"]*', lambda m: m.group(1) + canonical, t, count=1)
    # 제목의 "N페이지" 표기
    def fix_title(s):
        s = re.sub(r' \d+페이지', '', s)
        return s if n == 1 else re.sub(r'^(.*?)( \| )', lambda m: f'{m.group(1)} {n}페이지{m.group(2)}', s, count=1)
    t = re.sub(r'<title>(.*?)</title>', lambda m: f'<title>{fix_title(m.group(1))}</title>', t, count=1)
    for k in ['og:title" content="', 'twitter:title" content="']:
        t = re.sub(r'(' + re.escape(k) + r')([^"]*)', lambda m: m.group(1) + fix_title(m.group(2)), t, count=1)
    return t


def build(repo, json_files, out):
    info, existing = inventory(repo)
    domain = info['domain']
    topics = {t['slug']: t['label'] for t in info['topics']}
    ex = list(existing.values())
    titles = {p['title'] for p in ex}
    counters = {}
    for s in existing:
        m = re.match(r'(.+)-(\d+)$', s)
        if m:
            counters[m.group(1)] = max(counters.get(m.group(1), 0), int(m.group(2)))
    first_of = {}
    for p in sorted(ex, key=lambda p: p['slug']):
        first_of.setdefault(p['topic'], p)
    by_topic = {}
    for p in sorted(ex, key=lambda p: p['slug']):
        if p['thumb']:
            by_topic.setdefault(p['topic'], []).append(p)

    new = []
    for f in json_files:
        date = os.path.basename(f)[:10]
        datetime.date.fromisoformat(date)
        for i, p in enumerate(json.load(open(f, encoding='utf-8'))):
            if p['title'] in titles:
                print('  건너뜀(이미 있음):', p['title'])
                continue
            if p['topic'] not in topics:
                raise SystemExit(f'알 수 없는 topic: {p["topic"]}')
            n = counters.get(p['topic'], 0) + 1
            counters[p['topic']] = n
            slug = f"{p['topic']}-{n:02d}"
            pool = by_topic[p['topic']]
            src = pool[(n - 1) % len(pool)]
            f0 = first_of[p['topic']]
            p = dict(p, slug=slug, date=date, new=True, order=len(new), section=topics[p['topic']],
                     thumb=src['thumb'].replace(f'/journal/{src["slug"]}/', f'/journal/{slug}/'),
                     risk=f0['risk'], disclaimer=f0['disclaimer'], hub=f0['hub'], hub_text=f0['hub_text'], tpl_slug=f0['slug'])
            titles.add(p['title'])
            new.append(p)

    for p in ex + new:
        p['author'] = info['author']
    allp = sorted(ex + new, key=lambda p: (p['date'], p.get('order', -1), p['slug']), reverse=True)
    chrono = list(reversed(allp))

    if os.path.abspath(out) != os.path.abspath(repo):
        if os.path.exists(out):
            shutil.rmtree(out)
        shutil.copytree(repo, out, ignore=shutil.ignore_patterns('.git'))

    # ---- 새 글 페이지
    for p in new:
        tpl = read(os.path.join(repo, 'journal', p['tpl_slug'], 'index.html'))
        url = f'{domain}/journal/{p["slug"]}/'
        og = f'{domain}/images/og-default.jpg'
        t = tpl
        t = re.sub(r'<title>.*?</title>', lambda m: f'<title>{esc(p["title"])} | {esc(info["clinic"])}</title>', t, count=1)
        for pat, val in [(r'(<meta name="description" content=")[^"]*', p['summary']),
                         (r'(<meta property="og:description" content=")[^"]*', p['summary']),
                         (r'(<meta name="twitter:description" content=")[^"]*', p['summary']),
                         (r'(<meta property="og:title" content=")[^"]*', p['title']),
                         (r'(<meta name="twitter:title" content=")[^"]*', p['title']),
                         (r'(<meta property="og:image:alt" content=")[^"]*', info['clinic'] + ' 로고')]:
            t = re.sub(pat, lambda m: m.group(1) + esc(val), t, count=1)
        t = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda m: m.group(1) + url, t, count=1)
        t = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + url, t, count=1)
        t = re.sub(r'(<meta (?:property="og:image"|name="twitter:image") content=")[^"]*', lambda m: m.group(1) + og, t)
        t = re.sub(r'(article:(?:published|modified)_time" content=")[^"]*', lambda m: m.group(1) + p['date'], t)
        art = {'@type': 'Article', 'headline': p['title'], 'description': p['summary'], 'inLanguage': 'ko-KR',
               'mainEntityOfPage': {'@type': 'WebPage', '@id': url}, 'url': url, 'image': og,
               'datePublished': p['date'], 'dateModified': p['date'],
               'author': {'@type': 'Organization', 'name': info['author']}, 'publisher': {'@id': f'{domain}/#clinic'},
               'articleSection': p['section']}
        t = re.sub(r'\{"@type":"Article".*?"articleSection":"[^"]*"\}', lambda m: json.dumps(art, ensure_ascii=False, separators=(',', ':')), t, count=1, flags=re.S)

        i = chrono.index(p)
        pv, nx = (chrono[i - 1] if i > 0 else None), (chrono[i + 1] if i + 1 < len(chrono) else None)
        same = [q for q in allp if q['topic'] == p['topic'] and q['slug'] != p['slug']][:3]
        toc = ''
        if len(p['sections']) >= 4:
            toc = '<nav class="toc" aria-label="목차"><strong>이 글에서 확인할 내용</strong><ol>' + ''.join(
                f'<li><a href="#s{k+1}">{esc(s["h"])}</a></li>' for k, s in enumerate(p['sections'])) + '</ol></nav>'
        check = ('<h2>상담 전 확인할 내용</h2>\n    <ul>' + ''.join(f'<li>{esc(c)}</li>' for c in p['checklist']) + '</ul>') if p.get('checklist') else ''
        srcs = ''
        if p.get('sources'):
            srcs = ('<h2>참고 자료</h2>\n    <ul class="srcs">' + ''.join(
                f'<li><a href="{esc(s["url"])}" rel="noopener" target="_blank">{esc(s["title"])} ↗</a></li>' for s in p['sources'])
                + '</ul>\n    <p class="fine" style="font-size:.88rem;color:var(--muted)">공공기관·학회의 일반 안내를 사실 확인에 참고했습니다. 국내 허가사항이나 본원의 진료 제공 여부를 확인하는 자료는 아닙니다.</p>')
        prevnext = ('<nav class="prevnext" aria-label="이전·다음 글">\n      '
                    + (f'<a class="prev" href="/journal/{pv["slug"]}/"><span>← 이전 글</span>{esc(pv["title"])}</a>' if pv else '<span></span>') + '\n      '
                    + (f'<a class="next" href="/journal/{nx["slug"]}/"><span>다음 글 →</span>{esc(nx["title"])}</a>' if nx else '<span></span>') + '\n    </nav>')
        related = ('<section class="related">\n      <h2>같은 주제의 글</h2>\n      <ul>'
                   + ''.join(f'<li><a href="/journal/{q["slug"]}/">{esc(q["title"])}</a></li>' for q in same) + '</ul>\n    </section>')
        ctas = re.search(r'<div class="ctas">.*?</div>', tpl, re.S).group(0)
        article = f'''<article class="section article">
  <div class="wrap">
    <p class="breadcrumb"><a href="/">{esc(info['app_name'])}</a> › <a href="/blog/">건강정보</a> › <a href="/blog/topic/{p['topic']}/">{esc(p['section'])}</a></p>
    <h1>{esc(p['title'])}</h1>
    <p class="meta"><time datetime="{p['date']}">{kdate(p['date'])}</time> · 작성자: {esc(info['author'])}</p>
    <p class="summary">{esc(p['summary'])}</p>
    {toc}
    <div class="body">{render_body(p)}</div>

    {check}

    {p['risk']}
    {p['disclaimer']}

    {srcs}

    <a class="hub-link" href="{p['hub']}">{esc(p['hub_text'])}</a>
    <p>카테고리 <a href="/blog/topic/{p['topic']}/">{esc(p['section'])}</a></p>

    {prevnext}

    {related}
    {ctas}
  </div>
</article>'''
        t = re.sub(r'<article class="section article">.*?</article>', lambda m: article, t, count=1, flags=re.S)
        write(os.path.join(out, 'journal', p['slug'], 'index.html'), t)

    # ---- 블로그 전체 목록
    tpl1 = read(os.path.join(repo, 'blog/index.html'))
    tpl2 = read(os.path.join(repo, 'blog/page/2/index.html')) if os.path.exists(os.path.join(repo, 'blog/page/2/index.html')) else tpl1
    pages = [allp[i:i + PER_PAGE] for i in range(0, len(allp), PER_PAGE)]
    shutil.rmtree(os.path.join(out, 'blog/page'), ignore_errors=True)
    for n, chunk in enumerate(pages, 1):
        items = ''.join(list_item(p, k < 2) for k, p in enumerate(chunk))
        canon = f'{domain}/blog/' if n == 1 else f'{domain}/blog/page/{n}/'
        t = list_page(tpl1 if n == 1 else tpl2, items, pager(n, len(pages), '/blog/'), n, canon)
        write(os.path.join(out, 'blog/index.html' if n == 1 else f'blog/page/{n}/index.html'), t)

    # ---- 주제 목록
    for slug in topics:
        tplt = read(os.path.join(repo, 'blog/topic', slug, 'index.html'))
        tps = [p for p in allp if p['topic'] == slug]
        tpages = [tps[i:i + TOPIC_PER_PAGE] for i in range(0, len(tps), TOPIC_PER_PAGE)]
        shutil.rmtree(os.path.join(out, 'blog/topic', slug, 'page'), ignore_errors=True)
        for n, chunk in enumerate(tpages, 1):
            items = ''.join(list_item(p, k < 2) for k, p in enumerate(chunk))
            base = f'/blog/topic/{slug}/'
            t = list_page(tplt, items, pager(n, len(tpages), base), n, domain + (base if n == 1 else f'{base}page/{n}/'))
            write(os.path.join(out, 'blog/topic', slug, 'index.html' if n == 1 else f'page/{n}/index.html'), t)

    # ---- sitemap
    sm = read(os.path.join(repo, 'sitemap.xml'))
    latest = allp[0]['date']
    keep = [u for u in re.findall(r'<url>.*?</url>', sm, re.S) if not re.search(r'/journal/|/blog/page/|/blog/topic/', u)]
    keep = [re.sub(r'(<loc>[^<]*/blog/</loc>)(<lastmod>[^<]*</lastmod>)?', lambda m: m.group(1) + f'<lastmod>{latest}</lastmod>', u) for u in keep]
    urls = keep + [f'<url><loc>{domain}/blog/page/{n}/</loc><lastmod>{latest}</lastmod></url>' for n in range(2, len(pages) + 1)]
    for slug in topics:
        tps = [p for p in allp if p['topic'] == slug]
        urls.append(f'<url><loc>{domain}/blog/topic/{slug}/</loc><lastmod>{tps[0]["date"]}</lastmod></url>')
        urls += [f'<url><loc>{domain}/blog/topic/{slug}/page/{n}/</loc><lastmod>{tps[0]["date"]}</lastmod></url>' for n in range(2, (len(tps) - 1) // TOPIC_PER_PAGE + 2)]
    urls += [f'<url><loc>{domain}/journal/{p["slug"]}/</loc><lastmod>{p["date"]}</lastmod></url>' for p in allp]
    write(os.path.join(out, 'sitemap.xml'), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>\n')

    # ---- rss
    head = read(os.path.join(repo, 'rss.xml')).split('<item>')[0]
    items = []
    for p in allp[:30]:
        body = render_body(p) if p.get('new') else (p.get('body') or '')
        dt = datetime.datetime.strptime(p['date'], '%Y-%m-%d').replace(hour=9, tzinfo=KST)
        u = f'{domain}/journal/{p["slug"]}/'
        items.append(f'<item><title>{esc(p["title"])}</title><link>{u}</link><guid isPermaLink="true">{u}</guid>'
                     f'<pubDate>{format_datetime(dt)}</pubDate><category>{esc(p["section"])}</category>'
                     f'<description><![CDATA[<p>{esc(p["summary"])}</p>{body}]]></description></item>')
    write(os.path.join(out, 'rss.xml'), head + '\n'.join(items) + '\n</channel></rss>\n')

    # ---- 백링크
    backlink = f'<p class="backlink" style="margin:18px 0 0;font-size:.95rem">{esc(info["clinic"])} 안내: <a href="{domain}/">{esc(info["app_name"])}</a></p>'
    for f in glob.glob(os.path.join(out, 'journal/*/index.html')):
        s = read(f)
        if 'class="backlink"' not in s:
            write(f, s.replace('\n    <nav class="prevnext"', '\n    ' + backlink + '\n\n    <nav class="prevnext"', 1))

    print(f'{domain}: 기존 {len(ex)} + 새 글 {len(new)} = {len(allp)}편, 목록 {len(pages)}페이지 → {out}')
    return [dict(slug=p['slug'], title=p['title'], topic=p['topic'], date=p['date']) for p in new]


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('posts', nargs='*')
    ap.add_argument('--out', help='출력 폴더(기본: repo 자체를 수정)')
    a = ap.parse_args()
    res = build(a.repo, a.posts, a.out or a.repo)
    if a.out:
        json.dump(res, open(os.path.join(a.out, '..', os.path.basename(a.out.rstrip('/')) + '-new.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
