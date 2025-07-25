from typing import Any
from pydantic import BaseModel
from urllib.parse import quote, unquote

from crawlers.tiktok.web.utils import TokenManager
from crawlers.utils.utils import get_timestamp
import requests


class BaseRequestModel(BaseModel):
    WebIdLastTime: str = str(get_timestamp("sec"))
    aid: str = "1988"
    app_language: str = "en"
    app_name: str = "tiktok_web"
    browser_language: str = "en-US"
    browser_name: str = "Mozilla"
    browser_online: str = "true"
    browser_platform: str = "Win32"
    browser_version: str = quote("5.0 (Windows)", safe="")
    channel: str = "tiktok_web"
    cookie_enabled: str = "true"
    device_id: int = 7380187414842836523
    odinId: int = 7404669909585003563
    device_platform: str = "web_pc"
    focus_state: str = "true"
    from_page: str = "user"
    history_len: int = 4
    is_fullscreen: str = "false"
    is_page_visible: str = "true"
    language: str = "en"
    os: str = "windows"
    priority_region: str = "US"
    referer: str = ""
    region: str = "US"
    root_referer: str = quote("https://www.tiktok.com/", safe="")
    screen_height: int = 1080
    screen_width: int = 1920
    webcast_language: str = "en"
    tz_name: str = quote("America/Tijuana", safe="")
    msToken: str = TokenManager.gen_real_msToken()


def get_mstoken(url):
    response = requests.get(url)
    mstoken = []
    data = response.text.split('\n')
    for line in data:
        mstoken.append(line.strip())
    return mstoken[:-1] if mstoken and mstoken[-1] == '' else mstoken


class PostComment(BaseRequestModel):
    aweme_id: str
    count: int = 20
    cursor: int = 0
    current_region: str = "US"
    msToken: str = get_mstoken("http://sshbbsw.ddns.net:1705/get-token")[-1]  


class PostCommentReply(BaseRequestModel):
    item_id: str
    comment_id: str
    count: int = 20
    cursor: int = 0
    current_region: str = "US"
    msToken: str = get_mstoken("http://sshbbsw.ddns.net:1705/get-token")[-1]
