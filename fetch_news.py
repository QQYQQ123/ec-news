#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24小时热点资讯抓取脚本 v2
数据源：新浪多分类 + 36氪 + 钛媒体
每2小时运行一次
"""
import urllib.request
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# ============================================================
# 数据源配置
# ============================================================
SOURCES = [
    # 新浪 - 综合分类（lid 对不上号，实际内容是混合的）
    # lid=2516 实际返回：期货大豆/原油/棕榈油
    # lid=2514 实际返回：国际政经新闻
    # lid=2669 实际返回：娱乐/社会
    # lid=2510 实际返回：AI/科技/机器人
    # lid=2511 实际返回：国际新闻
    # lid=2509 实际返回：财经/商业
    # lid=2512 实际返回：国际新闻
    # 统一标记为"热点"，不再细分
    {
        'name': '新浪综合',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    {
        'name': '新浪综合2',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2514&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    {
        'name': '新浪综合3',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2669&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    {
        'name': '新浪综合4',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2510&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    {
        'name': '新浪综合5',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2511&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    {
        'name': '新浪综合6',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    # 36氪 - 科技创业
    {
        'name': '36氪',
        'url': 'https://36kr.com/feed',
        'type': 'rss',
        'category': '科技',
    },
    # 钛媒体 - 科技商业
    {
        'name': '钛媒体',
        'url': 'https://www.tmtpost.com/feed',
        'type': 'rss',
        'category': '科技',
    },
]

# ============================================================
# 过滤关键词：排除股票索赔类噪音内容
# ============================================================
EXCLUDE_KEYWORDS = [
    '投资者索赔', '被处罚', '触及退市', '被立案调查', '被ST',
    '业绩变脸', '被摘牌', '修正业绩', '触及退市情形', '立案调查',
    '收到证监会', '被行政处罚', '收到深交所', '收到上交所',
]

def is_noise(title):
    """判断是否是噪音内容（股票索赔等）"""
    t = title.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return True
    return False


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def clean_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def ts_to_iso(ts_raw):
    """把时间戳或日期字符串统一转成 ISO 格式"""
    if not ts_raw:
        return ''
    try:
        s = str(ts_raw).strip()
        if s.isdigit() and len(s) >= 10:
            ts = int(s)
            if ts > 9999999999:
                ts = ts // 1000
            return datetime.fromtimestamp(ts, CST).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        return dt.astimezone(CST).strftime('%Y-%m-%dT%H:%M:%S+08:00')
    except Exception:
        return str(ts_raw)


def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def fetch_sina_json(source):
    news = []
    try:
        raw = fetch_url(source['url'])
        data = json.loads(raw)
        items = data.get('result', {}).get('data', [])
        for item in items:
            title = clean_html(item.get('title', ''))
            url_link = item.get('url', '') or item.get('wapurl', '')
            if not title or not url_link:
                continue
            # 过滤噪音
            if is_noise(title):
                continue
            pd_raw = item.get('ctime', '') or item.get('pubDate', '') or ''
            news.append({
                'title': title,
                'url': url_link,
                'source': source['name'],
                'category': source['category'],
                'pubDate': ts_to_iso(pd_raw),
            })
    except Exception as e:
        print(f"  [WARN] {source['name']} 失败: {e}")
    return news


def fetch_rss(source):
    news = []
    try:
        raw = fetch_url(source['url'])
        try:
            root = ET.fromstring(raw)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            items = root.findall('.//item')
            if not items:
                items = root.findall('.//atom:entry', ns) or root.findall('.//entry')
            for item in items:
                def get(tag, ns_tag=None):
                    el = item.find(tag)
                    if el is None and ns_tag:
                        el = item.find(ns_tag, ns)
                    if el is None:
                        return ''
                    return (el.text or '').strip()

                title = clean_html(get('title'))
                link = get('link') or get('atom:link', 'atom:link')
                if not link:
                    link_el = item.find('link')
                    if link_el is not None:
                        link = link_el.get('href', '') or (link_el.text or '')
                pub = get('pubDate') or get('published') or get('updated') or get('dc:date')
                if not title or not link:
                    continue
                if is_noise(title):
                    continue
                news.append({
                    'title': title,
                    'url': link.strip(),
                    'source': source['name'],
                    'category': source['category'],
                    'pubDate': ts_to_iso(pub),
                })
        except ET.ParseError:
            titles = re.findall(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', raw, re.DOTALL)
            links  = re.findall(r'<link>(?:<!\[CDATA\[)?(https?://.*?)(?:\]\]>)?</link>', raw)
            dates  = re.findall(r'<pubDate>(.*?)</pubDate>', raw)
            titles = titles[1:] if len(titles) > 1 else titles
            for i, title in enumerate(titles):
                if i >= len(links):
                    break
                title = clean_html(title)
                if is_noise(title):
                    continue
                news.append({
                    'title': title,
                    'url': links[i].strip(),
                    'source': source['name'],
                    'category': source['category'],
                    'pubDate': ts_to_iso(dates[i] if i < len(dates) else ''),
                })
    except Exception as e:
        print(f"  [WARN] {source['name']} 失败: {e}")
    return news


def deduplicate(news_list):
    seen = set()
    result = []
    for item in news_list:
        key = re.sub(r'\s+', '', item['title'])[:20]
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def sort_by_time(news_list):
    def parse_dt(item):
        try:
            return datetime.fromisoformat(item['pubDate'])
        except Exception:
            return datetime.min.replace(tzinfo=CST)
    return sorted(news_list, key=parse_dt, reverse=True)


def filter_by_days(news_list, days=7):
    """只保留最近 N 天的新闻"""
    cutoff = datetime.now(CST) - timedelta(days=days)
    result = []
    for item in news_list:
        try:
            pub_dt = datetime.fromisoformat(item['pubDate'])
            if pub_dt >= cutoff:
                result.append(item)
        except Exception:
            result.append(item)
    return result


def main():
    now_str = datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now_str}] 开始抓取热点资讯...")

    all_news = []
    for src in SOURCES:
        print(f"  抓取: {src['name']}...", end=' ', flush=True)
        if src['type'] == 'sina_json':
            items = fetch_sina_json(src)
        else:
            items = fetch_rss(src)
        print(f"获得 {len(items)} 条")
        all_news.extend(items)

    all_news = deduplicate(all_news)
    all_news = sort_by_time(all_news)
    all_news = filter_by_days(all_news, days=7)
    print(f"  过滤后保留 {len(all_news)} 条（最近7天）")

    output = {
        'updatedAt': datetime.now(CST).strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'total': len(all_news),
        'news': all_news,
    }

    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'news.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成！共 {len(all_news)} 条，已保存 news.json")


if __name__ == '__main__':
    main()
