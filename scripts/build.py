"""Build the website and README from the same validated registry; no dependencies."""
import argparse
import json
import re
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- catalog:start -->', '<!-- catalog:end -->'


def load_catalog(root=ROOT):
    websites = json.loads((root / 'data/websites.json').read_text())['websites']
    repo_data = json.loads((root / 'data/repositories.json').read_text())
    validate(websites, repo_data)
    return websites, repo_data


def validate(websites, repo_data):
    repos = repo_data['repositories']
    if not re.fullmatch(r'[A-Za-z0-9-]+', repo_data['owner']):
        raise ValueError('Invalid GitHub owner')
    names = [r['name'] for r in repos]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate repository')
    for repo in repos:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', repo['name']):
            raise ValueError('Invalid repository name')
        for field in ('display_name', 'summary', 'category', 'category_id'):
            if not isinstance(repo.get(field), str) or not repo[field].strip():
                raise ValueError(f'{repo["name"]}: missing {field}')
        if not isinstance(repo.get('private'), bool) or not isinstance(repo.get('archived'), bool):
            raise ValueError('Repository visibility and archive state must be boolean')
    ids, urls = set(), set()
    for site in websites:
        for field in ('id', 'name', 'url', 'summary', 'launch_source'):
            if not isinstance(site.get(field), str) or not site[field].strip():
                raise ValueError(f'Missing site {field}')
        parsed = urlsplit(site['url'])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Website URL must be HTTPS and must not contain credentials')
        if site['id'] in ids or site['url'] in urls:
            raise ValueError('Duplicate website ID or URL')
        ids.add(site['id']); urls.add(site['url'])
        if site.get('launch_date'):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', site['launch_date']):
                raise ValueError('Launch date must use YYYY-MM-DD')
            date.fromisoformat(site['launch_date'])
        if not isinstance(site.get('launch_estimated'), bool) or not isinstance(site.get('listed'), bool):
            raise ValueError('Site date precision and listed state must be boolean')
        if site['status'] not in ('active', 'archived'):
            raise ValueError('Invalid website status')
        if site.get('repository') and site['repository'] not in names:
            raise ValueError(f'{site["id"]}: repository is not in registry')
        if site.get('source_status', 'available') not in ('available', 'repository_only'):
            raise ValueError('Invalid source archive status')


def sorted_websites(websites, listed_only=True):
    items = [s for s in websites if s['listed'] or not listed_only]
    return sorted(items, key=lambda s: s.get('launch_date') or '', reverse=True)


def launch_label(site):
    if not site.get('launch_date'):
        return '上线时间待核实'
    return ('约 ' if site['launch_estimated'] else '') + site['launch_date'] + ' 上线'


def short_url(url):
    parsed = urlsplit(url)
    return parsed.netloc + parsed.path.rstrip('/')


def render_page(websites, repo_data):
    owner = repo_data['owner']
    site_cards, repo_cards = [], []
    for site in sorted_websites(websites):
        name, url, summary = (escape(site[k], quote=True) for k in ('name', 'url', 'summary'))
        search = escape(' '.join([site['name'], site['url'], site['summary'], site.get('repository') or '']), quote=True)
        label = escape(launch_label(site))
        launched = (f'<time datetime="{site["launch_date"]}" title="{escape(site["launch_source"], quote=True)}">{label}</time>'
                    if site.get('launch_date') else f'<span>{label}</span>')
        source_label = '空仓库 ↗' if site.get('source_status') == 'repository_only' else '源码 ↗'
        source = (f'<a class="related" href="https://github.com/{owner}/{site["repository"]}" target="_blank" rel="noopener" aria-label="{name}的仓库">{source_label}</a>'
                  if site.get('repository') else '<span class="related unmatched">源码待归档</span>')
        site_cards.append(f'''<article class="entry" data-kind="website" data-search="{search}">
 <a class="entry-main" href="{url}" target="_blank" rel="noopener"><h2>{name}<span class="arrow" aria-hidden="true">↗</span></h2><span class="url">{escape(short_url(site['url']))}</span><p>{summary}</p><div class="entry-meta">{launched}</div></a>{source}
</article>''')
    categories = {}
    for repo in repo_data['repositories']:
        categories.setdefault(repo['category_id'], repo['category'])
        name = escape(repo['display_name'])
        url = f'https://github.com/{owner}/{repo["name"]}'
        search = escape(' '.join([repo['display_name'], repo['name'], repo['summary'], repo['category']]), quote=True)
        linked = next((s for s in websites if s.get('repository') == repo['name']), None)
        related = (f'<a class="related" href="{escape(linked["url"], quote=True)}" target="_blank" rel="noopener">网站 ↗</a>' if linked else '')
        visibility = '私有' if repo['private'] else '公开'
        state = ' · 已归档' if repo['archived'] else ''
        repo_cards.append(f'''<article class="entry" data-kind="repository" data-category="{escape(repo['category_id'], quote=True)}" data-search="{search}">
 <a class="entry-main" href="{url}" target="_blank" rel="noopener"><h2>{name}<span class="arrow" aria-hidden="true">↗</span></h2><span class="url">{escape(owner + '/' + repo['name'])}</span><p>{escape(repo['summary'])}</p><div class="entry-meta"><span>{visibility}{state} · {escape(repo['category'])}</span></div></a>{related}
</article>''')
    options = ''.join(f'<option value="{escape(k, quote=True)}">{escape(v)}</option>' for k, v in categories.items())
    return '''<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="一巍的网站与 GitHub 仓库。"><meta name="color-scheme" content="light">
<title>一巍 · 网站与仓库</title><link rel="canonical" href="https://home.liyw.top/">
<link rel="stylesheet" href="style.css"><script src="app.js" defer></script>
</head><body>
<a class="skip" href="#directory">跳到目录</a>
<header class="wrap"><div class="identity"><h1>一巍<span aria-hidden="true">。</span></h1><span class="home-url">home.liyw.top</span></div>
<a class="github-home" href="https://github.com/''' + owner + '''/Homepage" target="_blank" rel="noopener">GitHub ↗</a></header>
<main class="wrap" id="directory">
<div class="toolbar"><nav aria-label="目录"><a href="#websites" data-view="websites" aria-current="page">网站</a><a href="#repositories" data-view="repositories">仓库</a></nav>
<div class="controls"><label class="category" hidden><span class="sr-only">仓库分类</span><select id="category"><option value="">全部分类</option>''' + options + '''</select></label>
<label class="search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input type="search" id="search" placeholder="搜索" aria-label="搜索目录" autocomplete="off"></label></div></div>
<section class="gallery" id="websites" aria-label="网站，按上线时间从新到旧">''' + '\n'.join(site_cards) + '''</section>
<section class="gallery" id="repositories" aria-label="全部 GitHub 仓库" hidden>''' + '\n'.join(repo_cards) + '''</section>
<div class="empty" hidden><span>未找到</span><button type="button" id="reset">清除筛选</button></div><div class="sr-only" id="results" aria-live="polite"></div>
<noscript><style>#repositories[hidden]{display:grid!important}.category{display:none!important}</style></noscript>
</main></body></html>
'''


def md(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def render_catalog(websites, repo_data):
    repos, owner = repo_data['repositories'], repo_data['owner']
    public = sum(not r['private'] for r in repos)
    lines = [START, '## 网站', '', '按上线时间从新到旧。带「约」的日期依据首次 DNS 接入记录推定，尚未核实首次成功部署时间。', '',
             '| 网站 | 内容 | 上线时间 | 源码 |', '| --- | --- | --- | --- |']
    for site in sorted_websites(websites, listed_only=False):
        source_label = '仓库（源码待归档）' if site.get('source_status') == 'repository_only' else '仓库'
        source = f'[{source_label}](https://github.com/{owner}/{site["repository"]})' if site.get('repository') else '待归档'
        lines.append(f'| [{md(site["name"])}]({site["url"]}) | {md(site["summary"])} | {launch_label(site)} | {source} |')
    lines += ['', '## 仓库', '', f'**{len(repos)} 个仓库** · {public} 个公开 · {len(repos)-public} 个私有 · 核对于 {repo_data["synced_at"]}', '',
              '私有仓库需要登录有权限的 GitHub 账号。总数包含 Homepage。']
    groups = {}
    for repo in repos:
        groups.setdefault(repo['category'], []).append(repo)
    for category, items in groups.items():
        lines += ['', f'### {category}', '', '| 项目 | 用途 | 访问 |', '| --- | --- | --- |']
        for repo in items:
            visibility = '私有' if repo['private'] else '公开'
            lines.append(f'| [{md(repo["display_name"])}](https://github.com/{owner}/{repo["name"]}) | {md(repo["summary"])} | {visibility} |')
    return '\n'.join(lines + ['', END])


def build(root=ROOT, check=False):
    websites, repo_data = load_catalog(root)
    readme = (root / 'README.md').read_text()
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError('README must contain one catalog marker pair')
    before, rest = readme.split(START)
    _, after = rest.split(END)
    outputs = {
        root / 'dist/index.html': render_page(websites, repo_data),
        root / 'README.md': before + render_catalog(websites, repo_data) + after,
    }
    stale = []
    for path, content in outputs.items():
        if check:
            if not path.exists() or path.read_text() != content:
                stale.append(str(path.relative_to(root)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if stale:
        raise ValueError('Generated files are stale: ' + ', '.join(stale) + '; run python scripts/build.py')
    return len(websites), len(repo_data['repositories'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        sites, repos = build(check=args.check)
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(f'{sites} website records, {repos} repositories; ' + ('verified' if args.check else 'built'))


if __name__ == '__main__':
    main()
