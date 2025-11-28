# src/wiki_api.py

import os
import requests
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Dict, List, Optional
from config import LANG_CONFIG, HEADERS, SPECIFIC_IGNORE_TERMS, IGNORE_PREFIXES, CONFIG_JSON_PATH

def get_siteviews_scaling_factors() -> Dict[str, float]:
    """
    获取各语言站点的流量数据，并计算相对于最大流量站点的放缩因子。
    用于动态调整可视化的颜色阈值。
    """
    print("Fetching site-wide views for dynamic threshold scaling...")
    factors = {lang['code']: 1.0 for lang in LANG_CONFIG}

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=20)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    avg_views = {}

    for lang in LANG_CONFIG:
        project = lang['project']
        project_key = project.replace('.org', '') if project.endswith('.org') else project
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/{project_key}/all-access/user/daily/{start_str}/{end_str}"

        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                valid_views = [item['views'] for item in items if item.get('views') is not None]
                if valid_views:
                    avg_views[lang['code']] = mean(valid_views)
            else:
                print(f"  Warning: Failed to fetch aggregate views for {lang['code']} (Status {response.status_code})")
        except Exception as e:
            print(f"  Error fetching {lang['code']}: {e}")

    if not avg_views:
        print("Warning: Could not calculate average site views from network.")
        try:
            # 网络请求失败，从缓存 config.json 文件加载旧的放缩因子
            if os.path.exists(CONFIG_JSON_PATH):
                with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                    cached_config = json.load(f)
                    cached_factors = cached_config.get("scalingFactors")
                    if cached_factors:
                        print(f"-> Using cached scaling factors from: {CONFIG_JSON_PATH}")
                        return cached_factors

            # 如果缓存文件不存在或内容无效，则使用默认值
            print("-> Cache not found or invalid. Using default scaling factors.")
            return factors
        except Exception as e:
            # 文件读取或解析出错，也使用默认值
            print(f"Error reading cache file {CONFIG_JSON_PATH}: {e}")
            print("-> Using default scaling factors.")
            return factors

    max_avg_views = max(avg_views.values())
    if max_avg_views == 0:
        return factors

    for code, avg in avg_views.items():
        factors[code] = (avg / max_avg_views) ** 0.5

    print(f"Calculated scaling factors: {json.dumps(factors, indent=2)}")
    return factors

def get_top_articles(lang_code: str, date_obj: datetime) -> List[Dict]:
    """
    获取指定语言和日期的 Top 10 条目及其浏览量。
    """
    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    day = date_obj.strftime("%d")

    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang_code}.wikipedia/all-access/{year}/{month}/{day}"

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()

        raw_articles = data.get('items', [])[0].get('articles', [])
        cleaned_data = []

        for art in raw_articles:
            title = art['article']
            views = art['views']

            if title in SPECIFIC_IGNORE_TERMS:
                continue
            if title.startswith(IGNORE_PREFIXES):
                continue

            cleaned_data.append({'title': title, 'views': views})

            if len(cleaned_data) >= 10:
                break

        return cleaned_data
    except Exception as e:
        print(f"Error fetching {lang_code}: {e}")
        return []

def generate_chart_link(project: str, articles_data: List[Dict], end_date_obj: datetime, top_n: Optional[int] = None) -> Optional[str]:
    """
    生成 pageviews.wmcloud.org 的趋势图链接。
    如果指定 top_n，则只取前 N 个条目生成链接。
    """
    if not articles_data:
        return None

    subset = articles_data[:top_n] if top_n else articles_data
    titles = [item['title'] for item in subset]

    start_date = end_date_obj - timedelta(days=60)
    base_url = "https://pageviews.wmcloud.org/pageviews/"
    params = {
        "project": project,
        "platform": "all-access",
        "agent": "user",
        "redirects": "0",
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date_obj.strftime("%Y-%m-%d"),
        "pages": "|".join(titles)
    }
    return f"{base_url}?{urllib.parse.urlencode(params, safe='|')}"
