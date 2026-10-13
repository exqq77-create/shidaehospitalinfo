"""빌드 결과 검수 (루트 절대경로 사이트)
  python3 tools/check.py <site_dir> [<site_dir> ...]
깨진 내부 링크, noindex, 미리보기 흔적, 백링크 누락, 새 글 금칙어·분량, 글 간 5-gram 유사도.
새 글 목록은 <site_dir>-new.json(빌드가 남김)에서 읽는다."""
import re, os, sys, glob, json, html, itertools

BANNED = ['완치', '무통', '부작용 없', '최고', '유일', '1위', '보장합니다', '100%', '할인', '이벤트', '후기']


def shingles(t, n=5):
    t = re.sub(r'\s+', '', t)
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def body_text(s):
    m = re.search(r'<div class="body">(.*?)</div>', s, re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))) if m else ''


def resolve(root, href):
    path = href.split('?')[0].split('#')[0]
    if not path.startswith('/'):
        return True
    full = os.path.join(root, path.lstrip('/'))
    return os.path.isfile(full) or os.path.isfile(os.path.join(full, 'index.html'))


def check(root):
    root = root.rstrip('/')
    problems = []
    domain = re.search(r'<link rel="canonical" href="(https://[^/]+)/', open(os.path.join(root, 'index.html'), encoding='utf-8').read()).group(1)
    texts = {}
    for f in glob.glob(os.path.join(root, '**/*.html'), recursive=True):
        s = open(f, encoding='utf-8').read()
        rel = os.path.relpath(f, root)
        if 'noindex' in s and not f.endswith('404.html'):
            problems.append(f'{rel}: noindex')
        if '미리보기 —' in s:
            problems.append(f'{rel}: 미리보기 띠')
        links = re.findall(r'(?:href|src)="(/[^"]*)"', s) + [u.split()[0] for ss in re.findall(r'srcset="([^"]+)"', s) for u in ss.split(', ')]
        for h in set(links):
            if not resolve(root, h):
                problems.append(f'{rel}: 깨진 링크 {h}')
        if rel.startswith('journal/'):
            if f'href="{domain}/"' not in s or 'class="backlink"' not in s:
                problems.append(f'{rel}: 백링크 없음')
            texts[rel.split('/')[1]] = body_text(s)
    newf = root + '-new.json'
    new = {p['slug'] for p in json.load(open(newf))} if os.path.exists(newf) else set()
    for slug in new:
        t = texts.get(slug, '')
        problems += [f'{slug}: 금칙어 "{w}"' for w in BANNED if w in t]
        if len(t.replace(' ', '')) < 1000:
            problems.append(f'{slug}: 본문 짧음')
    sh = {k: shingles(v) for k, v in texts.items()}
    sims = sorted(((len(sh[a] & sh[b]) / max(1, len(sh[a] | sh[b])), a, b)
                   for a, b in itertools.combinations(sorted(texts), 2) if a in new or b in new), reverse=True)
    return problems, sims[:3], len(texts), len(new)


if __name__ == '__main__':
    bad = 0
    for d in sys.argv[1:]:
        problems, top, n, nn = check(d)
        bad += len(problems)
        print(f'== {d}: 글 {n}편(새 글 {nn}) · 문제 {len(problems)}건 · 최고 유사도 {[(round(j, 3), a, b) for j, a, b in top]}')
        for p in problems[:30]:
            print('   ', p)
    sys.exit(1 if bad else 0)
