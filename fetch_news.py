#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日电商热点抓取脚本
抓取多个RSS源，输出 news.json
"""

import urllib.request
import json
import re
from datetime import datetime, timezone, timedelta

# 北京时间 (UTC+8)
CST = timezone(timedelta(hours=8))
TODAY = datetime.now(CST).strftime('%Y-%m-%d')

# RSS 源列表
RSS_SOURCES = [
    {
        'name': '亿邦动力',
        'url': 'https://www.ebrun.com/feed',
        'category': '行业媒体'
    },
    {
        'name': '36氪',
        'url': 'https://36kr.com/feed',
        'category': '科技媒体'
    },
    {
        'name': '新浪科技',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&page=1&r=0.5',
        'category': '综合科技',
        'is_json': True
    },
]

def fetch_rss(source):
    """抓取单个RSS源，返回新闻列表"""
    news = []
    try:
        req = urllib.request.Request(
            source['url'],
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')

        if source.get('is_json'):
            data = json.loads(raw)
            items = data.get('result', {}).get('data', [])
            for item in items[:10]:
                # pubDate: 统一转 ISO 时间字符串
                    pd_raw = item.get('ctime', '') or item.get('pubDate', '') or ''
                    try:
                        s = str(pd_raw).strip()
                        if s.isdigit() and len(s) >= 10:
                            ts = int(s)
                            if ts > 9999999999: ts = ts // 1000
                            pd = datetime.fromtimestamp(ts, CST).strftime('%Y-%m-%dT%H:%M:%S+08:00')
                        else:
                            pd = s
                    except:
                        pd = str(pd_raw)
                    news.append({
                        'title': clean_html(item.get('title', '')),
                        'url': item.get('url', '') or item.get('wapurl', ''),
                        'source': source['name'],
                        'category': source['category'],
                        'pubDate': pd,
                    })
        else:
            # 解析 RSS XML
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', raw)
            links  = re.findall(r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', raw)
            dates  = re.findall(r'<pubDate>(.*?)</pubDate>', raw)
            # 去掉第一个（通常是频道标题）
            titles = titles[1:] if len(titles) > 1 else titles
            n = min(len(titles), 10)
            for i in range(n):
                link = links[i] if i < len(links) else ''
                if not link or link == 'http://': continue
                news.append({
                    'title': clean_html(titles[i]),
                    'url': link.strip(),
                    'source': source['name'],
                    'category': source['category'],
                    'pubDate': dates[i] if i < len(dates) else '',
                })
    except Exception as e:
        print(f"  [WARN] {source['name']} 抓取失败: {e}")
    return news


def clean_html(text):
    """去除HTML标签"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_recent(pub_date_str, days=7):
    """判断新闻是否在最近N天内"""
    if not pub_date_str:
        return True  # 无日期则保留
    try:
        # RFC 2822 格式: Sat, 18 Apr 2026 10:00:00 +0000
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_date_str)
        now = datetime.now(CST)
        delta = now - dt.astimezone(CST)
        return delta.days < days
    except Exception:
        return True


def deduplicate(news_list):
    """按标题去重"""
    seen = set()
    result = []
    for item in news_list:
        key = item['title'][:30]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def main():
    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 开始抓取电商资讯...")
    all_news = []
    for src in RSS_SOURCES:
        print(f"  抓取: {src['name']}...")
        items = fetch_rss(src)
        print(f"    获得 {len(items)} 条")
        all_news.extend(items)

    # 去重 & 过滤
    all_news = deduplicate(all_news)

    # 构输出JSON
    output = {
        'date': TODAY,
        'updatedAt': datetime.now(CST).isoformat(),
        'total': len(all_news),
        'news': all_news
    }

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成！共 {len(all_news)} 条新闻，已保存 news.json")

if __name__ == '__main__':
    main()
