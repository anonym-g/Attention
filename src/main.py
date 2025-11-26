import os
import json
import time
import requests
import tweepy
import urllib.parse
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright, ViewportSize, Browser, FloatRect

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
    '文件:', '分类:', '模版:', '模板:', '帮助:', '传送门:', '草稿:', '讨论:', '用户:', '话题:',

    # --- 日语 (JA) ---
    '特別:', 'ファイル:', '利用者:', 'ノート:', '画像:',

    # --- 德语 (DE) ---
    'Spezial:', 'Datei:', 'Kategorie:', 'Vorlage:', 'Hilfe:', 'Diskussion:', 'Benutzer:',

    # --- 法语 (FR) ---
    'Spécial:', 'Wikipédia:', 'Fichier:', 'Catégorie:', 'Modèle:', 'Aide:', 'Portail:', 'Discussion:', 'Utilisateur:',

    # --- 俄语 (RU) ---
    'Служебная:', 'Википедия:', 'Файл:', 'Категория:', 'Шаблон:', 'Справка:', 'Портал:', 'Обсуждение:', 'Участник:',

    # --- 意大利语 (IT) ---
    'Speciale:', 'Categoria:', 'Aiuto:', 'Portale:', 'Discussione:', 'Utente:',
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

def ensure_picture_dir(date_str, lang_code):
    """创建图片保存目录"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "pictures", date_str, lang_code)
    os.makedirs(path, exist_ok=True)
    return path

def capture_screenshots(url, save_dir):
    """使用 Playwright 截取 Logarithmic Line Chart 和 Pie Chart"""
    if not url:
        return []

    line_path = os.path.join(save_dir, "line.png")
    pie_path = os.path.join(save_dir, "pie.png")

    if os.path.exists(line_path) and os.path.exists(pie_path):
        print(f"Images already exist in {save_dir}, skipping.")
        return [line_path, pie_path]

    images = []

    try:
        with sync_playwright() as p:
            print("Launching browser...")
            browser: Browser = p.chromium.launch(headless=True)

            viewport_size: ViewportSize = {"width": 2560, "height": 1440}
            page = browser.new_page(viewport=viewport_size)

            print(f"Navigating to: {url}")
            page.goto(url, wait_until='networkidle', timeout=90000)

            try:
                page.wait_for_selector("canvas", state="visible", timeout=30000)
                time.sleep(5)
            except Exception as e:
                print(f"Warning: Canvas not detected or slow loading: {e}")

            def take_smart_screenshot(file_path):
                """智能截图"""
                try:
                    canvas = page.locator("canvas").first
                    box = canvas.bounding_box()
                    if box:
                        bottom_y = box['y'] + box['height'] + 180
                        clip_rect: FloatRect = {
                            'x': 0.0,
                            'y': 0.0,
                            'width': 2560.0,
                            'height': float(bottom_y)
                        }
                        page.screenshot(path=file_path, clip=clip_rect)
                        print(f"Captured (Smart): {file_path}")
                    else:
                        raise Exception("Canvas bounding box is None")
                except Exception as err:
                    print(f"Smart screenshot failed ({err}), falling back to viewport screenshot.")
                    page.screenshot(path=file_path)
                    print(f"Captured (Fallback): {file_path}")

            # 1. Logarithmic Line Chart
            try:
                # 使用 exact=True 避免匹配到 "Automatically use logarithmic"
                # 或者直接定位 class
                log_label = page.locator(".logarithmic-scale").first
                if log_label.is_visible():
                    log_label.click()
                    time.sleep(3)
                else:
                    # 备选：精确文本匹配
                    page.get_by_text("Logarithmic scale", exact=True).click()
                    time.sleep(3)
            except Exception as e:
                print(f"Error toggling Logarithmic: {e}")

            take_smart_screenshot(line_path)
            images.append(line_path)

            # 2. Pie Chart
            try:
                # 使用 CSS 类定位按钮，避免匹配到模态框标题 "Chart types"
                chart_btn = page.locator(".btn-chart-type").first
                if chart_btn.is_visible():
                    chart_btn.click()
                    time.sleep(1)

                    # 在下拉菜单中点击 "Pie"
                    pie_option = page.get_by_text("Pie", exact=True)
                    if pie_option.is_visible():
                        pie_option.click()
                        time.sleep(3)
                    else:
                        print("Pie option not visible.")
                else:
                    print("Chart type button not found.")
            except Exception as e:
                print(f"Error toggling Pie chart: {e}")

            take_smart_screenshot(pie_path)
            images.append(pie_path)

            browser.close()

    except Exception as e:
        print(f"Playwright critical error: {e}")

    return images

def get_twitter_auth_v1():
    """获取 v1.1 API (用于上传媒体)"""
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        return None

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    return tweepy.API(auth)

def get_twitter_client_v2():
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

    # 1. 准备阶段：抓取数据，生成链接、截图，构建文本
    tweet_queue = []

    print(">>> Phase 1: Preparing content (Data & Screenshots)...")
    for lang in LANG_CONFIG:
        print(f"\nProcessing {lang['code']}...")

        articles_data = get_top_articles(lang['code'], yesterday)
        if not articles_data:
            print(f"No data for {lang['code']}, skipping.")
            continue

        link = generate_link(lang['project'], articles_data, yesterday)

        # --- 截图 ---
        print("Taking screenshots...")
        pic_dir = ensure_picture_dir(date_str, lang['code'])
        image_paths = capture_screenshots(link, pic_dir)

        # --- 构建推文文本 ---
        tweet_text = construct_tweet(lang, date_str, articles_data, link)
        print(f"[Content Preview] {tweet_text[:50]}...")

        # 存入数据报告
        report_data["results"].append({
            "lang": lang['code'],
            "data": articles_data,
            "link": link,
            "images": image_paths
        })

        # 存入发推队列
        tweet_queue.append({
            "lang_code": lang['code'],
            "text": tweet_text,
            "images": image_paths
        })

    # 2. 发送阶段：批量上传图片并发送 Thread
    print("\n>>> Phase 2: Posting Tweets...")

    client_v2 = get_twitter_client_v2()
    api_v1 = get_twitter_auth_v1()
    last_successful_id = None

    if client_v2 and api_v1:
        for item in tweet_queue:
            lang_code = item['lang_code']
            text = item['text']
            images = item['images']

            try:
                media_ids = []
                # 上传图片
                for img_path in images:
                    if os.path.exists(img_path):
                        print(f"[{lang_code}] Uploading {img_path}...")
                        media = api_v1.media_upload(filename=img_path)
                        media_ids.append(media.media_id)

                # 发推
                print(f"[{lang_code}] Sending tweet...")
                if last_successful_id:
                    resp = client_v2.create_tweet(
                        text=text,
                        media_ids=media_ids if media_ids else None,
                        in_reply_to_tweet_id=last_successful_id
                    )
                else:
                    resp = client_v2.create_tweet(
                        text=text,
                        media_ids=media_ids if media_ids else None
                    )

                # 测试有效，更新ID
                last_successful_id = resp.data['id']
                print(f"[{lang_code}] Posted successfully. ID: {last_successful_id}")

                if lang_code == 'en':
                    update_readme(date_str, last_successful_id)

                # 稍微等待避免速率限制
                time.sleep(2)

            except Exception as e:
                print(f"[{lang_code}] Failed to post: {e}")
    else:
        print("Twitter credentials missing, skipping post phase.")

    # 3. 保存数据
    save_data(date_str, report_data)
    print("\nAll done.")

if __name__ == "__main__":
    main()
