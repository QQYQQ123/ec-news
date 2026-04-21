#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24小时热点资讯抓取脚本
多源聚合，每2小时运行一次
"""

import urllib.request
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# ============================================================
# 数据源配置（多源聚合）
# ============================================================
SOURCES = [
    # --- 新浪科技 JSON API ---
    {
        'name': '新浪科技',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '科技',
    },
    # --- 新浪财经 JSON API ---
    {
        'name': '新浪财经',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2514&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '财经',
    },
    # --- 新浪新闻 JSON API ---
    {
        'name': '新浪新闻',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2669&k=&num=30&page=1&r=0.5',
        'type': 'sina_json',
        'category': '热点',
    },
    # --- 新浪体育 JSON API ---
    {
        'name': '新浪体育',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2510&k=&num=20&page=1&r=0.5',
        'type': 'sina_json',
        'category': '体育',
    },
    # --- 新浪娱乐 JSON API ---
    {
        'name': '新浪娱乐',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2511&k=&num=20&page=1&r=0.5',
        'type': 'sina_json',
        'category': '娱乐',
    },
    # --- 澎湃新闻 RSS ---
    {
        'name': '澎湃新闻',
        'url': 'https://www.thepaper.cn/rss_cn.xml',
        'type': 'rss',
        'category': '热点',
    },
    # --- 虎嗅 RSS ---
    {
        'name': '虎嗅',
        'url': 'https://www.huxiu.com/rss/0.xml',
        'type': 'rss',
        'category': '科技',
    },
    # --- 36氪 RSS ---
    {
        'name': '36氪',
        'url': 'https://36kr.com/feed',
        'type': 'rss',
        'category': '科技',
    },
    # --- 钛媒体 RSS ---
    {
        'name': '钛媒体',
        'url': 'https://www.tmtpost.com/feed',
        'type': 'rss',
        'category': '科技',
    },
    # --- 界面新闻 RSS ---
    {
        'name': '界面新闻',
        'url': 'https://www.jiemian.com/rss.xml',
        'type': 'rss',
        'category': '财经',
    },
]

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
        # RFC 2822 格式
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
            url = item.get('url', '') or item.get('wapurl', '')
            if not title or not url:
                continue
            pd_raw = item.get('ctime', '') or item.get('pubDate', '') or ''
            news.append({
                'title': title,
                'url': url,
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
        # 尝试 XML 解析
        try:
            root = ET.fromstring(raw)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            # RSS 2.0
            items = root.findall('.//item')
            if not items:
                # Atom
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
                news.append({
                    'title': title,
                    'url': link.strip(),
                    'source': source['name'],
                    'category': source['category'],
                    'pubDate': ts_to_iso(pub),
                })
        except ET.ParseError:
            # 降级：正则解析
            titles = re.findall(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', raw, re.DOTALL)
            links  = re.findall(r'<link>(?:<!\[CDATA\[)?(https?://.*?)(?:\]\]>)?</link>', raw)
            dates  = re.findall(r'<pubDate>(.*?)</pubDate>', raw)
            titles = titles[1:] if len(titles) > 1 else titles
            for i, title in enumerate(titles):
                if i >= len(links):
                    break
                news.append({
                    'title': clean_html(title),
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
    """只保留最近 N 天的新闻，过滤掉旧数据"""
    cutoff = datetime.now(CST) - timedelta(days=days)
    result = []
    for item in news_list:
        try:
            pub_dt = datetime.fromisoformat(item['pubDate'])
            if pub_dt >= cutoff:
                result.append(item)
        except Exception:
            # 时间解析失败的也保留
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
    all_news = filter_by_days(all_news, days=7)  # 只保留最近7天
    print(f"  过滤后保留 {len(all_news)} 条（最近7天）")

    output = {
        'updatedAt': datetime.now(CST).strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'total': len(all_news),
        'news': all_news,
    }

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成！共 {len(all_news)} 条，已保存 news.json")


if __name__ == '__main__':
    main()
