#!/usr/bin/env python3
"""发完一条，落盘记账。

用法：
  .venv/bin/python scripts/record-post.py --draft outputs/<dir> --post-id <id> \
      --url https://x.com/FrankFika/status/<id> --platform x --media 2 --chars 462 \
      --topic <topic_signature> [--edited-from <old_post_id>] [--note "..."]

写：state/published-posts.json · state/seen-posts.json · state/index.json ·
    private/account-safety.yaml（last_published_*）· outputs/<dir>/x.txt 尾注
每个文件先留 .bak-<ts>。
"""
import argparse, json, os, re, shutil, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = datetime.timezone(datetime.timedelta(hours=8))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return json.load(f)


def save(rel, data):
    p = os.path.join(ROOT, rel)
    shutil.copy(p, p + '.bak-' + datetime.datetime.now(TZ).strftime('%Y%m%d-%H%M'))
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--draft', required=True)
    ap.add_argument('--post-id', required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--platform', default='x')
    ap.add_argument('--media', type=int, default=0)
    ap.add_argument('--chars', type=int, default=0)
    ap.add_argument('--topic', required=True)
    ap.add_argument('--timestamp', default=None)
    ap.add_argument('--edited-from', default=None)
    ap.add_argument('--note', default='')
    ap.add_argument('--gate-sha', default=None)
    a = ap.parse_args()

    ts = a.timestamp or datetime.datetime.now(TZ).strftime('%Y-%m-%dT%H:%M:%S+08:00')
    day = ts[:10]
    draft = a.draft.rstrip('/')
    media_paths = []
    sd = os.path.join(ROOT, draft, 'screenshots')
    if os.path.isdir(sd):
        media_paths = [f'{draft}/screenshots/{f}' for f in sorted(os.listdir(sd))][:a.media]

    # 1) published-posts.json
    pp = load('state/published-posts.json')
    pp['last_updated'] = ts
    eid = f"{a.platform}_post_{a.post_id}"
    pp['entries'] = [e for e in pp['entries'] if e.get('post_id') != a.post_id]
    entry = {
        "id": eid,
        "timestamp": ts,
        "post_id": a.post_id,
        "url": a.url,
        "platform": a.platform,
        "source": {
            "trigger": "Fang 直接授权 / Codex 会话内真发",
            "cron_id": None,
            "note": a.note,
            "material_id": os.path.basename(draft),
        },
        "treatment": f"regular_post_{a.platform}_original",
        "topic_signature": a.topic,
        "media_count": a.media,
        "media_paths": media_paths,
        "character_count": a.chars,
        "visibility": "public",
    }
    if a.gate_sha:
        entry["ai_taste_check"] = {"prepublish_passed": True, "sha256": a.gate_sha}
    if a.edited_from:
        entry["verification"] = {
            "method": "permalink 详情页实测",
            "first_post_id": a.edited_from,
            "note": "首次发布版本被编辑取代，最终以本条 status id 为准",
            "platform_url": a.url,
        }
    pp['entries'].append(entry)
    save('state/published-posts.json', pp)

    # 2) seen-posts.json
    sp = load('state/seen-posts.json')
    sp['last_updated'] = ts
    sp['entries'] = [e for e in sp['entries'] if e.get('post_id') != a.post_id]
    sp['entries'].append({
        "post_id": a.post_id,
        "handle": "FrankFika",
        "seen_at": ts,
        "treatment": "own_posted",
        "topic_signature": a.topic,
        "posted_to_x": True,
        "own_post_url": a.url,
        "media_count": a.media,
        "context": a.note or "真发",
    })
    save('state/seen-posts.json', sp)

    # 3) index.json
    idx = load('state/index.json')
    idx['last_updated'] = ts
    idx['seen'][a.post_id] = {"t": "own", "h": "FrankFika", "d": day}
    idx['published'][a.post_id] = {"u": a.url, "d": day}
    save('state/index.json', idx)

    # 4) account-safety.yaml —— 文本级替换，保住注释
    p = os.path.join(ROOT, 'private/account-safety.yaml')
    shutil.copy(p, p + '.bak-' + datetime.datetime.now(TZ).strftime('%Y%m%d-%H%M'))
    s = open(p, encoding='utf-8').read()
    if a.platform == 'x':
        s, n = re.subn(r'^  last_published_at: .*$', f'  last_published_at: {ts}', s, count=1, flags=re.M)
        s, n = re.subn(r'^  last_published_post_id: .*$', f'  last_published_post_id: "{a.post_id}"', s, count=1, flags=re.M)
        s, n = re.subn(r'^  last_published_url: .*$', f'  last_published_url: "{a.url}"', s, count=1, flags=re.M)
        s, n = re.subn(r'^  last_published_round: .*$', f'  last_published_round: frank_direct_{day}', s, count=1, flags=re.M)
        s, n = re.subn(r'^  last_published_treatment: .*$', f'  last_published_treatment: regular_post_x_original_{a.media}_screenshots', s, count=1, flags=re.M)
        s, n = re.subn(r'^  last_published_topic_signature: .*$', f'  last_published_topic_signature: {a.topic}', s, count=1, flags=re.M)
        s, n = re.subn(r'^  last_published_media_count: .*$', f'  last_published_media_count: {a.media}', s, count=1, flags=re.M)
    open(p, 'w', encoding='utf-8').write(s)

    # 5) x.txt 尾部追加 posted_url / posted_at
    if a.platform == 'x':
        xt = os.path.join(ROOT, draft, 'x.txt')
        if os.path.isfile(xt):
            body = open(xt, encoding='utf-8').read()
            if '# posted_url:' not in body:
                body = body.rstrip('\n') + f'\n# posted_url: {a.url}\n# posted_at: {ts}\n'
                open(xt, 'w', encoding='utf-8').write(body)

    print(f"已记账: {a.url}")
    print(f"  published entries: {len(pp['entries'])} | seen entries: {len(sp['entries'])}")


if __name__ == '__main__':
    main()
