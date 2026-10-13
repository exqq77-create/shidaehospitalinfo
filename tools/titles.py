"""저장소의 현재 글 제목을 주제별로 출력(원고 작성 전 중복 방지용).  python3 tools/titles.py <repo_dir>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory import inventory
site, posts = inventory(sys.argv[1])
for t in site['topics']:
    ps = sorted((p for p in posts.values() if p['topic'] == t['slug']), key=lambda p: p['slug'])
    print(f"### {t['slug']} · {t['label']} ({len(ps)}편)")
    for p in ps:
        print('-', p['title'])
    print()
