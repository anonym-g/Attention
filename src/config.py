# src/config.py

import os

# ================= 路径配置 =================
# 获取当前文件所在目录的父级 (即 src\ 的父级 -> 项目根目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
DOCS_DATA_DIR = os.path.join(DOCS_DIR, "data")
VIDEO_DIR = os.path.join(BASE_DIR, "videos")
PICTURES_DIR = os.path.join(BASE_DIR, "pictures")
DATA_DIR = os.path.join(BASE_DIR, "data")
MUSICS_DIR = os.path.join(BASE_DIR, "musics")
CONFIG_JSON_PATH = os.path.join(DOCS_DIR, "config.json")

# ================= 基础配置 =================
REPO_URL = "https://github.com/anonym-g/Attention"
TWITTER_USERNAME = "trailblaziger"
BASE_COLOR_SLOPE_THRESHOLD = 100.0
SUPPORTED_MUSIC_EXTENSIONS = ['.flac', '.mp3', '.wav', '.m4a', '.ogg']

# HTTP 头
HEADERS = {
    'User-Agent': 'Attention-Bot/3.0 (https://github.com/anonym-g/Attention)'
}

# ================= 视频生成配置 (Animator) =================
VIDEO_FPS = 60
VIDEO_SECONDS_PER_DAY = 24
VIDEO_TOTAL_FRAMES_PER_DAY = VIDEO_FPS * VIDEO_SECONDS_PER_DAY
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_SCALE = 4 / 3
# 预渲染区间乘数因子：1.0 表示预渲染的长度等于一个并行块的长度
VIDEO_PRE_ROLL_FACTOR = 1.0

# ================= 截图配置 =================
BASE_VIEWPORT_WIDTH = 1920
BASE_VIEWPORT_HEIGHT = 1080
DEVICE_SCALE_FACTOR = 2

# ================= 语言配置 =================
LANG_CONFIG = [
    {'code': 'en', 'project': 'en.wikipedia.org', 'name': 'English', 'flag': '🇺🇸',
     'header': 'English Wikipedia Top 10'},
    {'code': 'zh', 'project': 'zh.wikipedia.org', 'name': '中文', 'flag': '🇨🇳', 'header': '中文维基百科前 10'},
    {'code': 'ja', 'project': 'ja.wikipedia.org', 'name': '日本語', 'flag': '🇯🇵',
     'header': 'ウィキペディア トップ10'},
    {'code': 'de', 'project': 'de.wikipedia.org', 'name': 'Deutsch', 'flag': '🇩🇪', 'header': 'Deutsche Wikipedia Top 10'},
    {'code': 'fr', 'project': 'fr.wikipedia.org', 'name': 'Français', 'flag': '🇫🇷', 'header': 'Français Wikipédia Top 10'},
    {'code': 'ru', 'project': 'ru.wikipedia.org', 'name': 'Русский', 'flag': '🇷🇺', 'header': 'Русская Википедия Топ-10'},
    {'code': 'it', 'project': 'it.wikipedia.org', 'name': 'Italiano', 'flag': '🇮🇹', 'header': 'Italiano Wikipedia Top 10'},
]

# ================= 过滤列表 =================
# 1. 命名空间前缀黑名单
IGNORE_PREFIXES = (
    # --- 英文/通用 ---
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

# 2. 精确匹配黑名单
SPECIFIC_IGNORE_TERMS = [
    # --- 首页 (Main Pages) ---
    'Main_Page', 'Wikipedia:首页', '首页', 'メインページ',
    'Wikipedia:Hauptseite', 'Wikipédia:Accueil_principal',
    'Заглавная_страница', 'Pagina_principale',
    # --- 搜索页 (Search) ---
    'Special:Search', 'Special:搜索', 'Special:Recherche', 'Spezial:Suche',
    'Служебная:Поиск', 'Speciale:Ricerca',
    # --- 系统/错误页 ---
    '-', '404.php', 'Nap', 'Undefined',
    # --- 其他常见干扰项 ---
    'Special:CreateAccount', 'Special:Watchlist', 'Special:RecentChanges',
    'Cookie_Statement', 'Privacy_policy', 'Wikipedia:About', 'Wikipedia:General_disclaimer'
]
