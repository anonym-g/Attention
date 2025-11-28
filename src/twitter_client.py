# src/twitter_client.py

import os
import tweepy
from typing import Optional

def get_twitter_auth_v1() -> Optional[tweepy.API]:
    """获取 v1.1 API 对象 (用于上传媒体)"""
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        return None

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    return tweepy.API(auth)

def get_twitter_client_v2() -> Optional[tweepy.Client]:
    """获取 v2 Client 对象 (用于发布推文)"""
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
