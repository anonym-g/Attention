# src/animator.py

import os
import json
import requests
import urllib.parse
import subprocess
import pathlib
import time
import base64
import concurrent.futures
import numpy as np
import random
from datetime import datetime, timedelta
from typing import Dict, Any, cast, Optional
from scipy.interpolate import PchipInterpolator
from playwright.sync_api import sync_playwright, ViewportSize

# 导入配置和常量
from config import (
    DOCS_DIR, DOCS_DATA_DIR, VIDEO_DIR, HEADERS,
    VIDEO_FPS, VIDEO_TOTAL_FRAMES_PER_DAY, VIDEO_WIDTH, VIDEO_HEIGHT,
    VIDEO_SCALE, VIDEO_PRE_ROLL_FACTOR, MUSICS_DIR, SUPPORTED_MUSIC_EXTENSIONS
)


def ensure_dirs():
    """
    确保所有必需的目录都存在。
    """
    os.makedirs(DOCS_DATA_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(MUSICS_DIR, exist_ok=True)


def load_history(lang_code: str) -> Dict[str, Any]:
    """
    加载指定语言的历史数据。
    """
    file_path = os.path.join(DOCS_DATA_DIR, f"history_{lang_code}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"dates": [], "articles": {}}


def save_history(data: Dict[str, Any], lang_code: str):
    """
    保存指定语言的历史数据。
    """
    ensure_dirs()
    file_path = os.path.join(DOCS_DATA_DIR, f"history_{lang_code}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# --- 数据处理逻辑 ---

def fetch_raw_daily_batch(project, title, start_date_str, end_date_str, session=None):
    """
    批量获取单个条目在日期范围内的原始日浏览量数据。
    """
    try:
        s = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%Y%m%d")
        e = datetime.strptime(end_date_str, "%Y-%m-%d").strftime("%Y%m%d")
        safe_title = urllib.parse.quote(title, safe='')
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/user/{safe_title}/daily/{s}/{e}"
        requester = session if session else requests
        resp = requester.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        result = {}
        for item in data.get('items', []):
            d_str = datetime.strptime(item['timestamp'], "%Y%m%d%H").strftime("%Y-%m-%d")
            result[d_str] = item['views']
        return result
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error fetching data for {title}: {e}")
        return {}


def interpolate_curve_for_date(daily_raw_map, target_date_str):
    """
    使用 PCHIP 插值算法为单日数据生成分钟级曲线。
    """
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    x_points = []
    y_points = []
    for i in range(-2, 3):
        d = target_date + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        val = daily_raw_map.get(d_str)
        if val is None:
            val = 0 if i < 0 else daily_raw_map.get(target_date_str, 0)
        x_points.append((i + 1) * 24)
        y_points.append(val)

    if sum(y_points) == 0:
        return [0] * 1440

    try:
        interpolator = PchipInterpolator(np.array(x_points), np.array(y_points))
        xs = np.linspace(0, 24, 1440, endpoint=False)
        ys = interpolator(xs)
        return [int(max(0, y)) for y in ys]
    except (ValueError, TypeError):
        return [y_points[2]] * 1440


def update_data(project, today_date_str, top_articles, lang_code='en'):
    """
    更新并保存历史数据，包括获取新数据和重新计算插值曲线。
    """
    history = load_history(lang_code)
    today_date = datetime.strptime(today_date_str, "%Y-%m-%d")

    if today_date_str not in history['dates']:
        history['dates'].append(today_date_str)
        history['dates'].sort()
        if len(history['dates']) > 30:
            history['dates'] = history['dates'][-30:]

    top_titles = set(item['title'] for item in top_articles)
    yesterday_str = (today_date - timedelta(days=1)).strftime("%Y-%m-%d")
    maintenance_titles = []

    for title, data in history['articles'].items():
        if title not in top_titles:
            if yesterday_str in data.get("daily_raw", {}):
                maintenance_titles.append(title)

    print(f"Updating data context for {today_date_str} [{lang_code}]...")
    fetch_start = (today_date - timedelta(days=3)).strftime("%Y-%m-%d")

    with requests.Session() as session:
        for item in top_articles:
            title = item['title']
            if title not in history['articles']:
                history['articles'][title] = {"daily_raw": {}, "minutes": {}}
            recent_data = fetch_raw_daily_batch(project, title, fetch_start, today_date_str, session)
            history['articles'][title]["daily_raw"].update(recent_data)
            history['articles'][title]["daily_raw"][today_date_str] = item['views']

        for title in maintenance_titles:
            daily_data = fetch_raw_daily_batch(project, title, yesterday_str, today_date_str, session)
            if daily_data:
                history['articles'][title]["daily_raw"].update(daily_data)

    dates_to_recalc = [(today_date - timedelta(days=2)).strftime("%Y-%m-%d"), yesterday_str, today_date_str]
    for title, data in history['articles'].items():
        raw = data["daily_raw"]
        for d_str in dates_to_recalc:
            if d_str in raw:
                data["minutes"][d_str] = interpolate_curve_for_date(raw, d_str)

    keep_dates = set(history['dates'])
    for title in history['articles']:
        keys = list(history['articles'][title]["minutes"].keys())
        for k in keys:
            if k not in keep_dates:
                del history['articles'][title]["minutes"][k]

    save_history(history, lang_code)
    return history


def _render_chunk_worker(args):
    """
    使用 CDP (Page.captureScreenshot) 进行渲染。
    """
    chunk_index, start_frame, end_frame, base_url, history_data, config_data, chunk_output_path, pre_roll_frames = args

    # 错峰启动，减少并发冲击
    time.sleep(chunk_index * 1.5)

    os.makedirs(os.path.dirname(chunk_output_path), exist_ok=True)

    real_width = int(VIDEO_WIDTH * VIDEO_SCALE)
    real_height = int(VIDEO_HEIGHT * VIDEO_SCALE)

    # FFMPEG: 从 stdin 读取 MJPEG 流
    ffmpeg_cmd = ['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', str(VIDEO_FPS), '-i', '-',
                  '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                  '-vf', f'fps={VIDEO_FPS},scale={real_width}:{real_height}:flags=lanczos',
                  '-pix_fmt', 'yuv420p', chunk_output_path]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--disable-web-security', '--allow-file-access-from-files',
                                                             '--hide-scrollbars', '--mute-audio', '--disable-gpu'])

            page = browser.new_page(
                viewport=cast(ViewportSize, {'width': VIDEO_WIDTH, 'height': VIDEO_HEIGHT}),
                device_scale_factor=VIDEO_SCALE
            )

            # 注入数据
            page.add_init_script(script=f"window.INJECTED_DATA = {json.dumps(history_data, ensure_ascii=False)};")
            page.add_init_script(script=f"window.INJECTED_CONFIG = {json.dumps(config_data, ensure_ascii=False)};")

            page.goto(base_url)
            page.wait_for_function("window.appReady === true", timeout=20000)

            # 初始化位置
            page.evaluate(f"window.initializeToFrame({start_frame}, {pre_roll_frames})")

            # ================= CDP Direct Access Setup =================
            client = page.context.new_cdp_session(page)

            # 循环渲染每一帧
            for i in range(start_frame, end_frame):
                # 1. 推进模拟时间 (同步 JS 调用，确保 DOM 更新)
                page.evaluate("window.advanceFrame()")

                # 2. 调用 CDP 截图
                res = client.send("Page.captureScreenshot", {
                    "format": "jpeg",
                    "quality": 90,
                    "optimizeForSpeed": True  # 实验性参数：尝试优化速度
                })

                # 3. 解码并写入 FFmpeg
                data = base64.b64decode(res['data'])
                proc.stdin.write(data)

            client.detach()
            browser.close()

    except Exception as e:
        print(f"  [Chunk {chunk_index}] Worker error: {e}")
        return False
    finally:
        if proc.stdin:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
        proc.wait()

    return proc.returncode == 0 and os.path.exists(chunk_output_path)


def render_day_segment_parallel(date_str, prev_date_str, lang_code, history_data, config_data, final_segment_path):
    """
    分块并行渲染单日视频。
    """
    print(f"  Rendering {date_str} (pre-roll from {prev_date_str or 'start'}) (Parallel/CDP)...")

    html_file = os.path.join(DOCS_DIR, 'index.html')
    html_path = pathlib.Path(html_file).as_uri()
    base_url = f"{html_path}?lang={lang_code}&mode=capture&date={date_str}"
    if prev_date_str:
        base_url += f"&prev_date={prev_date_str}"

    workers = 2
    chunk_duration_frames = VIDEO_TOTAL_FRAMES_PER_DAY // workers
    pre_roll_frames = int(chunk_duration_frames * VIDEO_PRE_ROLL_FACTOR)

    initial_tasks = []
    chunk_files = []
    temp_dir = os.path.join(VIDEO_DIR, "temp", f"{date_str}_{lang_code}")
    os.makedirs(temp_dir, exist_ok=True)

    for i in range(workers):
        start = i * chunk_duration_frames
        end = (i + 1) * chunk_duration_frames if i < workers - 1 else VIDEO_TOTAL_FRAMES_PER_DAY
        chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp4")
        chunk_files.append(chunk_path)
        args = (i, start, end, base_url, history_data, config_data, chunk_path, pre_roll_frames)
        initial_tasks.append(args)

    tasks_to_run = initial_tasks
    max_attempts = 3
    attempt = 0
    all_chunks_succeeded = False

    while attempt < max_attempts and not all_chunks_succeeded:
        attempt += 1
        if attempt > 1:
            print(f"  Retrying {len(tasks_to_run)} failed chunks (Attempt {attempt}/{max_attempts})...")

        failed_tasks = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_task = {executor.submit(_render_chunk_worker, t): t for t in tasks_to_run}
            for future in concurrent.futures.as_completed(future_to_task):
                task_args = future_to_task[future]
                try:
                    if not future.result():
                        failed_tasks.append(task_args)
                except Exception as e:
                    print(f"  Chunk {task_args[0]} execution resulted in an exception: {e}")
                    failed_tasks.append(task_args)

        if not failed_tasks:
            all_chunks_succeeded = True
        else:
            tasks_to_run = failed_tasks

    if not all_chunks_succeeded:
        print(f"  Error: {len(tasks_to_run)} chunks failed to render after {max_attempts} attempts.")
        return False

    concat_list_path = os.path.join(temp_dir, "concat_chunks.txt")
    with open(concat_list_path, 'w') as f:
        for cf in chunk_files:
            f.write(f"file '{os.path.abspath(cf).replace('\\', '/')}'\n")

    print(f"  Merging {workers} chunks -> {os.path.basename(final_segment_path)}")
    os.makedirs(os.path.dirname(final_segment_path), exist_ok=True)
    cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_list_path}" -c copy "{final_segment_path}"'
    ret = subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if ret == 0:
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass

    return ret == 0


# --- 音频处理 ---

def _get_media_duration(file_path: str | os.PathLike) -> float:
    """使用 ffprobe 获取媒体文件的时长 (秒)"""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"  Warning: Could not get duration for {os.path.basename(file_path)}. Error: {e}")
        return 0.0


def add_background_music(video_path: str, output_path: str) -> str:
    """
    为视频添加背景音乐。
    - video_path: 无声视频文件的路径。
    - output_path: 最终带音轨的视频输出路径。
    返回最终视频的路径。
    """
    print("Adding background music...")
    try:
        music_files = [f for f in os.listdir(MUSICS_DIR) if isinstance(f, str) and any(f.endswith(ext) for ext in SUPPORTED_MUSIC_EXTENSIONS)]
        if not music_files:
            print("  No music files found. Skipping.")
            os.rename(video_path, output_path)
            return output_path

        selected_filename = random.choice(music_files)
        chosen_music_path = pathlib.Path(MUSICS_DIR) / selected_filename
        print(f"  Selected music: {selected_filename}")

        video_duration = _get_media_duration(video_path)
        audio_duration = _get_media_duration(chosen_music_path)

        if video_duration == 0 or audio_duration == 0:
            print("  Warning: Could not determine media duration. Skipping music.")
            os.rename(video_path, output_path)
            return output_path

        start_time = 0
        if audio_duration > video_duration:
            max_start = audio_duration - video_duration
            start_time = random.uniform(0, max_start)

        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-ss', str(start_time), '-i', str(chosen_music_path),
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-t', str(video_duration),
            output_path
        ]

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  Successfully mixed audio into video.")
        return output_path

    except Exception as e:
        print(f"  Error adding background music: {e}. Using video without audio.")
        if os.path.exists(video_path):
            os.rename(video_path, output_path)
        return output_path


# --- 主渲染流程 ---

def render_video(date_str, lang_code, config) -> Optional[str]:
    """
    主入口。渲染并拼接 7 天的视频，并添加背景音乐。
    """
    ensure_dirs()
    final_output = os.path.join(VIDEO_DIR, f"{date_str}_{lang_code}.mp4")
    print(f"Starting High-Performance Browser Render for {date_str} ({lang_code})...")

    history_data = load_history(lang_code)
    if not history_data['dates']:
        print("No history data found.")
        return None

    today_date = datetime.strptime(date_str, "%Y-%m-%d")
    dates_to_render = [(today_date - timedelta(days=6 - i)).strftime("%Y-%m-%d") for i in range(7)]
    segment_files = []

    for i, d_str in enumerate(dates_to_render):
        prev_d_str = None
        if i > 0:
            prev_d_str = dates_to_render[i - 1]
        else:
            current_obj = datetime.strptime(d_str, "%Y-%m-%d")
            prev_obj = current_obj - timedelta(days=1)
            prev_check_str = prev_obj.strftime("%Y-%m-%d")
            if prev_check_str in history_data['dates']:
                prev_d_str = prev_check_str

        seg_dir = str(os.path.join(VIDEO_DIR, d_str, lang_code))
        seg_path = os.path.join(seg_dir, f"segment_{d_str}.mp4")

        force_render = (d_str >= (today_date - timedelta(days=2)).strftime("%Y-%m-%d")) or not os.path.exists(seg_path)

        if d_str not in history_data['dates']:
            print(f"  Warning: No data for {d_str}, skipping.")
            continue
        if force_render and prev_d_str and prev_d_str not in history_data['dates']:
            print(f"  Warning: No pre-roll data for {prev_d_str}, skipping render of {d_str}.")
            continue

        if force_render:
            success = render_day_segment_parallel(d_str, prev_d_str, lang_code, history_data, config, seg_path)
            if not success:
                print(f"  Failed to render segment {d_str}")
        else:
            print(f"  Using cached segment for {d_str}")

        if os.path.exists(seg_path):
            segment_files.append(seg_path)

    if not segment_files:
        print("No segments generated.")
        return None

    temp_dir = os.path.join(VIDEO_DIR, "temp", f"final_{date_str}_{lang_code}")
    os.makedirs(temp_dir, exist_ok=True)
    list_file = os.path.join(temp_dir, "concat_final.txt")

    with open(list_file, 'w') as f:
        for seg in segment_files:
            f.write(f"file '{os.path.abspath(seg).replace('\\', '/')}'\n")

    video_only_path = os.path.join(temp_dir, 'video_no_audio.mp4')
    print("Concatenating 7 days into a temporary video file...")
    cmd_concat = f'ffmpeg -y -f concat -safe 0 -i "{list_file}" -c copy "{video_only_path}"'
    subprocess.call(cmd_concat, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(video_only_path):
        print("  Error: Failed to create temporary concatenated video.")
        return None

    # 添加背景音乐
    final_video_with_music = add_background_music(video_only_path, final_output)

    # 清理临时目录
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except OSError:
        pass

    print(f"Full video ready: {final_video_with_music}")
    return final_video_with_music
