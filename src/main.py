# src/main.py

import os
import time
from typing import cast
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright, ViewportSize, Browser

import animator
from config import (
    REPO_URL, TWITTER_USERNAME, BASE_COLOR_SLOPE_THRESHOLD, BASE_DIR,
    LANG_CONFIG, BASE_VIEWPORT_WIDTH, BASE_VIEWPORT_HEIGHT, DEVICE_SCALE_FACTOR
)
from utils import (
    get_date_str, format_number, save_json_config, save_daily_report_data,
    ensure_picture_dir, cleanup_old_videos, cleanup_video_directories
)
from wiki_api import get_siteviews_scaling_factors, get_top_articles, generate_chart_link
from twitter_client import get_twitter_auth_v1, get_twitter_client_v2


def construct_tweet(lang_config, date_str, articles_data, chart_link):
    """构建推文文本"""
    if not articles_data:
        return None

    header = f"{lang_config['flag']} {lang_config['header']} ({date_str})"
    top_lines = []
    for i, item in enumerate(articles_data[:3]):
        # 标题处理：去下划线
        display_title = item['title'].replace('_', ' ')

        # 根据语言区分截断阈值
        limit = 17 if lang_config['code'] in ['zh', 'ja'] else 35

        # 截断处理
        if len(display_title) > limit:
            display_title = display_title[:limit - 1] + "…"

        views_str = format_number(item['views'])
        top_lines.append(f"{i + 1}. {display_title}: {views_str}")

    top_content = "\n".join(top_lines)

    tweet_text = (
        f"{header}\n\n"
        f"{top_content}\n\n"
        f"📊 Visualization & Full List:\n"
        f"{chart_link}\n\n"
        f"🔗 Project: {REPO_URL}"
    )
    return tweet_text


def update_readme(date_str, tweet_id):
    """更新 README.md"""
    readme_path = os.path.join(BASE_DIR, "README.md")
    link = f"https://x.com/{TWITTER_USERNAME}/status/{tweet_id}"
    line_to_add = f"#### {date_str}: {link}"

    try:
        if not os.path.exists(readme_path):
            print("README.md not found, skipping update.")
            return

        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if link in content:
            print(f"Link already in README: {link}")
            return

        with open(readme_path, 'a', encoding='utf-8') as f:
            if "## Tweet List" not in content:
                f.write("\n\n## Tweet List\n")
            elif not content.endswith('\n'):
                f.write("\n")
            f.write(f"{line_to_add}\n")
            print(f"-> Added to README: {line_to_add}")
    except Exception as e:
        print(f"Error updating README: {e}")


def capture_screenshots(urls, save_dir):
    """使用 Playwright 截取 Top Views, Logarithmic Line Chart 和 Pie Chart"""
    topviews_url = urls.get('topviews')
    pageviews_url = urls.get('pageviews')

    if not topviews_url or not pageviews_url:
        return []

    topviews_path = os.path.join(save_dir, "topviews.png")
    line_path = os.path.join(save_dir, "line.png")
    pie_path = os.path.join(save_dir, "pie.png")

    if all(os.path.exists(p) for p in [topviews_path, line_path, pie_path]):
        print(f"Images already exist in {save_dir}, skipping.")
        return [topviews_path, line_path, pie_path]

    images = []
    try:
        with sync_playwright() as p:
            print("Launching browser...")
            browser: Browser = p.chromium.launch(headless=True)
            vp = cast(ViewportSize, {'width': BASE_VIEWPORT_WIDTH, 'height': BASE_VIEWPORT_HEIGHT})
            page = browser.new_page(viewport=vp, device_scale_factor=DEVICE_SCALE_FACTOR)

            def scroll_past_header():
                try:
                    header = page.locator(".interapp-navigation").first
                    if header.is_visible():
                        header_box = header.bounding_box()
                        if header_box:
                            scroll_y = header_box['height'] * 0.9
                            page.evaluate(f"window.scrollBy(0, {scroll_y})")
                            time.sleep(0.5)
                except Exception as err:
                    print(f"Could not scroll past header: {err}")

            # 1. Top Views
            print(f"Navigating to Top Views: {topviews_url}")
            page.goto(topviews_url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_selector("#topview-entry-1", state="visible", timeout=15000)
            scroll_past_header()
            page.screenshot(path=topviews_path)
            print(f"Captured: {topviews_path}")
            images.append(topviews_path)

            # 2. Line Chart
            print(f"Navigating to Page Views: {pageviews_url}")
            page.goto(pageviews_url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_selector("canvas", state="visible", timeout=15000)
            time.sleep(3)

            try:
                settings_btn = page.locator(".js-test-settings").first
                if settings_btn.is_visible():
                    settings_btn.click()
                    time.sleep(1)
                    bezier = page.locator(".js-test-bezier-curve").first
                    if bezier.is_visible():
                        bezier.click()
                        time.sleep(0.5)
                    save_btn = page.locator(".save-settings-btn").first
                    if save_btn.is_visible():
                        save_btn.click()
                        time.sleep(2)
                log_label = page.locator(".logarithmic-scale").first
                if log_label.is_visible():
                    log_label.click()
                    time.sleep(3)
            except Exception as e:
                print(f"Error configuring line chart: {e}")

            scroll_past_header()
            page.screenshot(path=line_path)
            print(f"Captured: {line_path}")
            images.append(line_path)

            # 3. Pie Chart
            try:
                chart_btn = page.locator(".btn-chart-type").first
                if chart_btn.is_visible():
                    chart_btn.click()
                    time.sleep(1)
                    pie = page.locator(".js-test-pie-chart").first
                    if pie.is_visible():
                        pie.click()
                        time.sleep(3)
            except Exception as e:
                print(f"Error toggling Pie chart: {e}")

            scroll_past_header()
            page.screenshot(path=pie_path)
            print(f"Captured: {pie_path}")
            images.append(pie_path)
            browser.close()

    except Exception as e:
        print(f"Playwright critical error: {e}")

    return images


def main():
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = get_date_str(yesterday)
    print(f"--- Report Date: {date_str} ---")

    scaling_factors = get_siteviews_scaling_factors()
    save_json_config(scaling_factors, BASE_COLOR_SLOPE_THRESHOLD)

    full_config = {
        "baseThreshold": BASE_COLOR_SLOPE_THRESHOLD,
        "scalingFactors": scaling_factors
    }

    report_data = {"date": date_str, "results": []}
    tweet_queue = []

    print(">>> Phase 1: Preparing content (Data & Screenshots)...")
    for lang in LANG_CONFIG:
        print(f"\nProcessing {lang['code']}...")

        articles_data = get_top_articles(lang['code'], yesterday)
        if not articles_data:
            print(f"No data for {lang['code']}, skipping.")
            continue

        print("Updating animation data...")
        animator.update_data(lang['project'], date_str, articles_data, lang['code'])
        video_path = animator.render_video(
            date_str=date_str,
            lang_code=lang['code'],
            config=full_config
        )
        cleanup_old_videos(video_path)

        # 生成链接
        full_list_link = generate_chart_link(lang['project'], articles_data, yesterday)
        chart_link_top5 = generate_chart_link(lang['project'], articles_data, yesterday, top_n=5)
        topviews_link = f"https://pageviews.wmcloud.org/topviews/?project={lang['project']}&platform=all-access&date={date_str}&excludes="

        print("Taking screenshots...")
        pic_dir = ensure_picture_dir(date_str, lang['code'])
        screenshot_urls = {"topviews": topviews_link, "pageviews": chart_link_top5}
        image_paths = capture_screenshots(screenshot_urls, pic_dir)

        tweet_text = construct_tweet(lang, date_str, articles_data, full_list_link)
        print(f"[Content Preview] {tweet_text[:50]}...")

        # 区分视频和图片
        report_data["results"].append({
            "lang": lang['code'],
            "data": articles_data,
            "link": full_list_link,
            "images": image_paths,
            "video": video_path
        })

        tweet_queue.append({
            "lang_code": lang['code'],
            "text": tweet_text,
            "video_path": video_path,
            "image_paths": image_paths,
            "link": full_list_link
        })

    print("\n>>> Phase 2: Posting Tweets...")
    client_v2 = get_twitter_client_v2()
    api_v1 = get_twitter_auth_v1()
    last_successful_id = None

    if client_v2 and api_v1:
        for item in tweet_queue:
            lang_code = item['lang_code']
            text = item['text']
            video_path = item.get('video_path')
            image_paths = item.get('image_paths', [])

            try:
                media_ids = []

                # 1. 上传视频 (作为首个媒体)
                if video_path and os.path.exists(video_path):
                    print(f"[{lang_code}] Uploading video: {video_path}...")
                    media = api_v1.media_upload(filename=video_path, media_category='tweet_video', chunked=True)
                    if hasattr(media, 'processing_info'):
                        state = media.processing_info['state']
                        while state in ['pending', 'in_progress']:
                            time.sleep(2)
                            status = api_v1.get_media_upload_status(media.media_id)
                            state = status.processing_info['state']
                            if state == 'failed':
                                print(f"[{lang_code}] Video processing failed.")
                                break
                    media_ids.append(media.media_id)

                # 2. 上传图片 (Mixed Media: Twitter API v2 支持 1 Video + Images)
                # 注意：推特限制单个推文最多 4 个媒体文件
                for p in image_paths:
                    if os.path.exists(p) and len(media_ids) < 4:
                        print(f"[{lang_code}] Uploading image: {p}...")
                        m = api_v1.media_upload(filename=p)
                        media_ids.append(m.media_id)

                # 3. 发送推文 (视频 + 图片混合)
                print(f"[{lang_code}] Sending tweet with {len(media_ids)} media items...")

                kwargs = {
                    'text': text,
                    'media_ids': media_ids if media_ids else None
                }

                # 发送英语推文，其他语言推文回复上一条（形成 Thread）
                if last_successful_id:
                    kwargs['in_reply_to_tweet_id'] = last_successful_id

                resp = client_v2.create_tweet(**kwargs)
                last_successful_id = resp.data['id']
                print(f"[{lang_code}] Posted successfully. ID: {last_successful_id}")

                if lang_code == 'en':
                    update_readme(date_str, last_successful_id)

                time.sleep(5)

            except Exception as e:
                print(f"[{lang_code}] Failed to post: {e}")
    else:
        print("Twitter credentials missing, skipping post phase.")

    save_daily_report_data(date_str, report_data)

    # 执行目录清理 (保留最近 15 天)
    cleanup_video_directories(keep_count=15)

    print("\nAll done.")


if __name__ == "__main__":
    main()
