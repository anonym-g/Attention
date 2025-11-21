import os
import json
import requests
import tweepy
import urllib.parse
from datetime import datetime, timedelta, timezone

# ================= 配置区域 =================
REPO_URL = "https://github.com/anonym-g/Attention"
TWITTER_USERNAME = "trailblaziger"

# 语言配置
LANG_CONFIG = [
    {'code': 'en', 'project': 'en.wikipedia.org', 'name': 'English', 'flag': '🇺🇸',
     'header': 'English Wikipedia Top 10'},
    {'code': 'zh', 'project': 'zh.wikipedia.org', 'name': '中文', 'flag': '🇨🇳', 'header': '中文维基百科浏览量 Top 10'},
    {'code': 'ja', 'project': 'ja.wikipedia.org', 'name': '日本語', 'flag': '🇯🇵',
     'header': 'ウィキペディア閲覧数 Top 10'},
    {'code': 'de', 'project': 'de.wikipedia.org', 'name': 'Deutsch', 'flag': '🇩🇪', 'header': 'Wikipedia Top 10 (DE)'},
    {'code': 'fr', 'project': 'fr.wikipedia.org', 'name': 'Français', 'flag': '🇫🇷', 'header': 'Wikipedia Top 10 (FR)'},
    {'code': 'ru', 'project': 'ru.wikipedia.org', 'name': 'Русский', 'flag': '🇷🇺', 'header': 'Wikipedia Top 10 (RU)'},
    {'code': 'it', 'project': 'it.wikipedia.org', 'name': 'Italiano', 'flag': '🇮🇹', 'header': 'Wikipedia Top 10 (IT)'},
]

HEADERS = {
    'User-Agent': 'Attention-Bot/3.0 (https://github.com/anonym-g/Attention)'
}

# ================= 过滤配置 =================

# 1. 命名空间前缀黑名单 (包含 EN, ZH, JA, DE, FR, RU, IT 的常见非条目空间)
IGNORE_PREFIXES = (
    # --- 英文/通用 (API有时返回通用前缀) ---
    'Special:', 'Wikipedia:', 'File:', 'Image:', 'Category:', 'Template:',
    'Help:', 'Portal:', 'Draft:', 'Talk:', 'User:', 'MediaWiki:', 'Book:',

    # --- 中文 (ZH) ---
    'Special:', 'Wikipedia:', 'File:', 'Category:', 'Template:', 'Help:', 'Portal:', 'Draft:', 'Talk:', 'User:',
    '文件:', '分类:', '模版:', '模板:', '帮助:', '传送门:', '草稿:', '讨论:', '用户:', '话题:',

    # --- 日语 (JA) ---
    '特別:', 'Wikipedia:', 'ファイル:', 'Category:', 'Template:', 'Help:', 'Portal:', 'Draft:', 'Talk:', 'User:',
    '利用者:', 'ノート:', '画像:',

    # --- 德语 (DE) ---
    'Spezial:', 'Wikipedia:', 'Datei:', 'Kategorie:', 'Vorlage:', 'Hilfe:', 'Portal:', 'Diskussion:', 'Benutzer:',

    # --- 法语 (FR) ---
    'Spécial:', 'Wikipédia:', 'Fichier:', 'Catégorie:', 'Modèle:', 'Aide:', 'Portail:', 'Discussion:', 'Utilisateur:',

    # --- 俄语 (RU) ---
    'Служебная:', 'Википедия:', 'Файл:', 'Категория:', 'Шаблон:', 'Справка:', 'Портал:', 'Обсуждение:', 'Участник:',

    # --- 意大利语 (IT) ---
    'Speciale:', 'Wikipedia:', 'File:', 'Categoria:', 'Template:', 'Aiuto:', 'Portale:', 'Discussione:', 'Utente:',
)

# 2. 精确匹配黑名单 (主要是各国首页、搜索页、404、隐私声明等)
SPECIFIC_IGNORE_TERMS = [
    # --- 首页 (Main Pages) ---
    'Main_Page',  # EN
    'Wikipedia:首页', '首页',  # ZH
    'メインページ',  # JA
    'Wikipedia:Hauptseite',  # DE
    'Wikipédia:Accueil_principal',  # FR
    'Заглавная_страница',  # RU
    'Pagina_principale',  # IT

    # --- 搜索页 (Search) ---
    'Special:Search', 'Special:搜索', 'Special:Recherche', 'Spezial:Suche',
    'Служебная:Поиск', 'Speciale:Ricerca',

    # --- 系统/错误页 ---
    '-', '404.php', 'Nap', 'Undefined',

    # --- 其他常见干扰项 ---
    'Special:CreateAccount', 'Special:Watchlist', 'Special:RecentChanges',
    'Cookie_Statement', 'Privacy_policy',
    'Wikipedia:About', 'Wikipedia:General_disclaimer'
]

def get_date_str(date_obj):
    return date_obj.strftime("%Y-%m-%d")

def format_number(num):
    """将数字格式化为千分位，如 1,234,567"""
    return f"{num:,}"

def get_top_articles(lang_code, date_obj):
    """获取 Top 10 条目及其浏览量"""
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
        cleaned_data = []  # 存储字典 {'title': ..., 'views': ...}

        for art in raw_articles:
            title = art['article']
            views = art['views']

            if title in SPECIFIC_IGNORE_TERMS:
                continue
            if title.startswith(IGNORE_PREFIXES):
                continue

            # 存储原始标题(用于链接)和浏览量
            cleaned_data.append({'title': title, 'views': views})

            if len(cleaned_data) >= 10:
                break

        return cleaned_data
    except Exception as e:
        print(f"Error fetching {lang_code}: {e}")
        return []

def generate_link(project, articles_data, end_date_obj):
    """生成趋势图链接"""
    if not articles_data:
        return None

    # 提取纯标题列表用于生成 URL
    titles = [item['title'] for item in articles_data]

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

def construct_tweet(lang_config, date_str, articles_data, chart_link):
    """构建符合要求的推文内容"""
    if not articles_data:
        return None

    # 1. 标题行
    header = f"{lang_config['flag']} {lang_config['header']} ({date_str})"

    # 2. 构建 Top 3 列表 (纯文本，替换下划线)
    top_lines = []
    for i, item in enumerate(articles_data[:3]):
        # 标题处理：去下划线
        display_title = item['title'].replace('_', ' ')
        # 截断处理：防止标题过长吃掉字符数 (保留前20个字符 + ...)
        if len(display_title) > 25:
            display_title = display_title[:24] + "…"

        views_str = format_number(item['views'])
        top_lines.append(f"{i + 1}. {display_title}: {views_str}")

    top_content = "\n".join(top_lines)

    # 3. 组合推文
    # 说明：Twitter链接占23字符。这里有两个链接，共占46字符。
    # 剩余可用：280 - 46 = 234。
    # Header + Top3 + CTA + Label 需小于 234。

    tweet_text = (
        f"{header}\n\n"
        f"{top_content}\n\n"
        f"📊 Visualization & Full List:\n"  # CTA 说明
        f"{chart_link}\n\n"
        f"🔗 Project: {REPO_URL}"
    )

    return tweet_text

def save_data(date_str, data):
    """
    将数据保存到 data/ 文件夹
    """
    # 获取 main.py 所在目录 (src/) 的父目录 (根目录)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dir_path = os.path.join(base_dir, "data")
    file_path = os.path.join(dir_path, f"{date_str}.json")

    try:
        os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"-> Data saved to: {file_path}")
    except Exception as e:
        print(f"Error saving data: {e}")

def update_readme(date_str, tweet_id):
    """
    更新 README.md，在 Tweet List 区域追加新的推文链接
    """
    # 获取项目根目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(base_dir, "README.md")

    link = f"https://x.com/{TWITTER_USERNAME}/status/{tweet_id}"
    line_to_add = f"#### {date_str}: {link}"

    try:
        if not os.path.exists(readme_path):
            print("README.md not found, skipping update.")
            return

        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 防止重复添加
        if link in content:
            print(f"Link already in README: {link}")
            return

        with open(readme_path, 'a', encoding='utf-8') as f:
            # 如果没有标题，先添加标题
            if "## Tweet List" not in content:
                f.write("\n\n## Tweet List\n")

            # 确保新行前有换行符 (如果文件末尾不是换行)
            elif not content.endswith('\n'):
                f.write("\n")

            f.write(f"{line_to_add}\n")
            print(f"-> Added to README: {line_to_add}")

    except Exception as e:
        print(f"Error updating README: {e}")

def get_twitter_client():
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("Twitter secrets missing.")
        return None

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

def main():
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = get_date_str(yesterday)
    print(f"--- Report Date: {date_str} ---")

    report_data = {"date": date_str, "results": []}
    client = get_twitter_client()

    # 维护一个有效ID
    # 如果中间某条失败，这个ID不更新，下一条会自动回复上一个成功的推文，保证Thread不断
    last_successful_id = None

    for lang in LANG_CONFIG:
        print(f"Processing {lang['code']}...")

        articles_data = get_top_articles(lang['code'], yesterday)
        if not articles_data:
            print(f"No data for {lang['code']}, skipping.")
            continue

        link = generate_link(lang['project'], articles_data, yesterday)

        report_data["results"].append({
            "lang": lang['code'],
            "data": articles_data,
            "link": link
        })

        tweet_text = construct_tweet(lang, date_str, articles_data, link)

        print(f"\n[Preview {lang['code']}] Length: {len(tweet_text)}")
        print(tweet_text)
        print("-" * 30)

        if client:
            try:
                # 尝试发送
                if last_successful_id:
                    resp = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=last_successful_id)
                else:
                    resp = client.create_tweet(text=tweet_text)

                # 测试有效，更新ID
                last_successful_id = resp.data['id']
                print(f"Posted {lang['code']} successfully. ID: {last_successful_id}")

                # 如果是英文版，将链接写入 README.md
                if lang['code'] == 'en':
                    update_readme(date_str, last_successful_id)

            except Exception as e:
                # 失败则打印错误，last_successful_id 保持不变
                print(f"Failed to post {lang['code']}: {e}")

    save_data(date_str, report_data)
    print("\nAll done.")

if __name__ == "__main__":
    main()
