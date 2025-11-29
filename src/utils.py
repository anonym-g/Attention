# src/utils.py

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any
from config import CONFIG_JSON_PATH, DATA_DIR, VIDEO_DIR, PICTURES_DIR

def get_date_str(date_obj: datetime) -> str:
    """格式化日期对象为 YYYY-MM-DD 字符串"""
    return date_obj.strftime("%Y-%m-%d")

def format_number(num: int) -> str:
    """将数字格式化为千分位字符串"""
    return f"{num:,}"

def save_json_config(scaling_factors: Dict[str, float], base_threshold: float):
    """保存前端所需的配置文件"""
    config_data = {
        "baseThreshold": base_threshold,
        "scalingFactors": scaling_factors
    }
    try:
        os.makedirs(os.path.dirname(CONFIG_JSON_PATH), exist_ok=True)
        with open(CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        print(f"-> Configuration saved to: {CONFIG_JSON_PATH}")
    except Exception as e:
        print(f"Error saving config: {e}")

def save_daily_report_data(date_str: str, data: Dict[str, Any]):
    """向 data/ 保存每日报告数据"""
    file_path = os.path.join(DATA_DIR, f"{date_str}.json")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"-> Data saved to: {file_path}")
    except Exception as e:
        print(f"Error saving data: {e}")

def ensure_picture_dir(date_str: str, lang_code: str) -> str:
    """确保图片保存目录存在并返回路径"""
    path = os.path.join(PICTURES_DIR, date_str, lang_code)
    os.makedirs(path, exist_ok=True)
    return path

def cleanup_old_videos(current_video_path: str):
    """清理旧的成品视频文件"""
    if not current_video_path:
        return
    video_dir = os.path.dirname(current_video_path)
    filename = os.path.basename(current_video_path)
    if "_" in filename:
        lang_suffix = filename.split("_")[-1]
    else:
        return
    try:
        for fname in os.listdir(video_dir):
            full_path = os.path.join(video_dir, fname)
            if fname.endswith(lang_suffix) and full_path != current_video_path and os.path.isfile(full_path):
                print(f"Removing old video: {fname}")
                os.remove(full_path)
    except Exception as e:
        print(f"Error cleaning up old videos: {e}")

def cleanup_video_directories(keep_count: int = 6):
    """
    清理 videos/ 下的旧日期目录，仅保留最近 keep_count 个。
    """
    if not os.path.exists(VIDEO_DIR):
        return

    try:
        # 获取所有子目录
        subdirs = [d for d in os.listdir(VIDEO_DIR) if os.path.isdir(os.path.join(VIDEO_DIR, d))]
        # 按日期字符串排序 (YYYY-MM-DD)
        subdirs.sort()

        # 如果数量超过保留限制，删除旧的
        if len(subdirs) > keep_count:
            to_remove = subdirs[:-keep_count]
            print(f"Cleaning up {len(to_remove)} old video directories...")
            for d_name in to_remove:
                dir_path = os.path.join(VIDEO_DIR, d_name)
                shutil.rmtree(dir_path)
                print(f"  -> Removed: {dir_path}")
    except Exception as e:
        print(f"Error cleaning video directories: {e}")
