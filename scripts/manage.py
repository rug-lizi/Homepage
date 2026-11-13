"""Maintain the website registry and refresh the GitHub repository inventory."""
import argparse
import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from build import ROOT, build, load_catalog, validate


def save(websites, repo_data):
    validate(websites, repo_data)
    (ROOT / 'data/websites.json').write_text(json.dumps({'websites': websites}, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'data/repositories.json').write_text(json.dumps(repo_data, ensure_ascii=False, indent=2) + '\n')
    build()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list-sites')
    for action in ('add-site', 'edit-site'):
        p = sub.add_parser(action)
        p.add_argument('id')
        for flag in ('name', 'url', 'summary', 'launch-date', 'launch-source'):
            p.add_argument('--' + flag, required=action == 'add-site' and flag in ('name', 'url', 'summary', 'launch-source'))
        p.add_argument('--repository', help='Repository name; empty string removes association')
        p.add_argument('--status', choices=('active', 'archived'))
        p.add_argument('--source-status', choices=('available', 'repository_only'))
        p.add_argument('--listed', choices=('true', 'false'))
        dates = p.add_mutually_exclusive_group()
        dates.add_argument('--launch-estimated', dest='launch_estimated', action='store_true', default=None)
        dates.add_argument('--launch-verified', dest='launch_estimated', action='store_false', default=None)
    sub.add_parser('remove-site').add_argument('id')
    sub.add_parser('sync-repos')
    args = parser.parse_args()
    websites, repo_data = load_catalog()
    try:
        if args.command == 'list-sites':
            for site in websites:
                print(f'{site["id"]}\t{site["name"]}\t{site["url"]}\t{site.get("repository") or "源码待归档"}')
            return
        if args.command == 'sync-repos':
            result = subprocess.run(['gh', 'repo', 'list', repo_data['owner'], '--limit', '1000', '--json', 'name,isPrivate,isArchived,description'], check=True, capture_output=True, text=True)
            current = {r['name']: r for r in repo_data['repositories']}
            incoming = json.loads(result.stdout)
            names = {r['name'] for r in incoming}
            # Preserve curated descriptions and category ordering, then append new repositories.
            ordered = [name for name in current if name in names] + [r['name'] for r in incoming if r['name'] not in current]
            by_name = {r['name']: r for r in incoming}
            refreshed = []
            for name in ordered:
                r = by_name[name]
                entry = dict(current.get(name, {'name': name, 'display_name': name, 'summary': r['description'] or '用途待补充。', 'category': '未分类', 'category_id': 'uncategorized'}))
                entry.update(private=r['isPrivate'], archived=r['isArchived'])
                refreshed.append(entry)
            repo_data['repositories'] = refreshed
            repo_data['synced_at'] = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        else:
            match = next((s for s in websites if s['id'] == args.id), None)
            if args.command == 'remove-site':
                if not match:
                    raise ValueError('Unknown website ID')
                websites.remove(match)
            else:
                if args.command == 'add-site':
                    if match:
                        raise ValueError('Website ID already exists')
                    match = {'id': args.id, 'repository': None, 'launch_date': None, 'launch_estimated': False, 'status': 'active', 'listed': True}
                    websites.append(match)
                elif match is None:
                    raise ValueError('Unknown website ID')
                for field in ('name', 'url', 'summary', 'launch_date', 'launch_source', 'repository', 'status', 'launch_estimated', 'source_status'):
                    value = getattr(args, field)
                    if value is not None:
                        match[field] = (value or None) if field in ('repository', 'launch_date') else value
                if args.listed is not None:
                    match['listed'] = args.listed == 'true'
        save(websites, repo_data)
    except (ValueError, KeyError, TypeError, subprocess.CalledProcessError, FileNotFoundError) as error:
        parser.exit(1, f'{error}\n')
    print('Registry, README and webpage updated. Review the Git diff before committing.')


if __name__ == '__main__':
    main()
