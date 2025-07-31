from __future__ import annotations
import os
import re
import json
import yaml
import httpx
import asyncio

from typing import Union
from pathlib import Path

from crawlers.utils.logger import logger
from crawlers.douyin.web.xbogus import XBogus as XB
from crawlers.utils.utils import (
    gen_random_str,
    get_timestamp,
    extract_valid_urls,
    split_filename,
)
from crawlers.utils.api_exceptions import (
    APIError,
    APIConnectionError,
    APIResponseError,
    APIUnauthorizedError,
    APINotFoundError,
)
from tenacity import stop_after_attempt, retry, wait_fixed, retry_if_result
from crawlers.tiktok.web.xbogus import XBogus as XBogusManager
import random
import time


path = os.path.abspath(os.path.dirname(__file__))

with open(f"{path}/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class TokenManager:
    """Manages tokens and cookies for TikTok API requests on an instance basis."""

    def __init__(self):
        self.tokens: dict = {}
        self.cookies: dict = {}
        self.headers: dict = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        }
        self.web_url: str = "https://www.tiktok.com/"
        self.api_url: str = "https://www.tiktok.com/passport/web/login/login_info/"
        self.odin_url: str = "https://www.tiktok.com/aweme/v1/web/login/qrcode/"

    async def get_token(self, token_name: str, transport: httpx.AsyncHTTPTransport) -> str:
        """Get token by name."""
        if token_name not in self.tokens:
            token_method_map = {
                "msToken": self.get_ms_token,
                "ttwid": self.get_ttwid,
                "odin_tt": self.get_odin_tt
            }
            token_method = token_method_map.get(token_name)
            if token_method:
                self.tokens[token_name] = await token_method(transport=transport)
            else:
                raise ValueError(f"Invalid token name: {token_name}")
        return self.tokens.get(token_name, "")

    async def get_cookies(self, url: str, transport: httpx.AsyncHTTPTransport) -> dict:
        """Get cookies from Web page."""
        if not self.cookies:
            async with httpx.AsyncClient(transport=transport) as client:
                response = await client.get(url=url, headers=self.headers)
            self.cookies = dict(response.cookies)
        return self.cookies

    async def get_tt_chain_token(self, url: str, transport: httpx.AsyncHTTPTransport) -> tuple[str, str, int]:
        """Get value x-tt-chain-token from headers"""
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.head(url=url, headers=self.headers, follow_redirects=True)
        tt_chain_token = response.headers.get("x-tt-chain-token", "")
        return tt_chain_token, str(response.url), int(response.status_code)

    async def get_ms_token(self, transport: httpx.AsyncHTTPTransport) -> str:
        """Get value msToken from API"""
        async with httpx.AsyncClient(headers=self.headers, transport=transport, timeout=10) as client:
            response = await client.post(url=self.api_url, data={})
        return response.json().get("data", {}).get("msToken", "")

    async def get_ttwid(self, transport: httpx.AsyncHTTPTransport) -> str:
        """Get value ttwid from Web"""
        async with httpx.AsyncClient(headers=self.headers, transport=transport, timeout=10) as client:
            response = await client.head(url=self.web_url, follow_redirects=True)
        return response.cookies.get("ttwid")

    async def get_odin_tt(self, transport: httpx.AsyncHTTPTransport) -> str:
        """Get value odin_tt from API"""
        async with httpx.AsyncClient(headers=self.headers, transport=transport, timeout=10) as client:
            response = await client.get(url=self.odin_url)
        return response.cookies.get("odin_tt")


class BogusManager:
    """Generates bogus parameters for TikTok API requests on an instance basis."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    def _is_fail(self, res: httpx.Response) -> bool:
        """Check if the response is fail"""
        if res.status_code != 200:
            return True
        elif res.json().get("status_code") != 0:
            return True
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry_error_callback=lambda state: logger.error(f"gen_bogus failed: {state.outcome.exception()}"),
        retry=retry_if_result(_is_fail)
    )
    def gen_bogus(self, url: str, data: str | None = None) -> tuple[str, str]:
        """Get value X-Bogus from Web page"""
        transport = httpx.HTTPTransport(retries=3)
        with httpx.Client(transport=transport) as client:
            response = client.post(
                url="https://vm.vnice.great-fire.org/v1/xbogus",
                json={"url": url, "user_agent": self.user_agent, "data": data}
            )
        data = response.json()
        return data.get("X-Bogus", ""), data.get("params", "")

    def get_final_url(self, url: str, data: str | None = None) -> str:
        """Get final url with bogus params"""
        xbogus, params = self.gen_bogus(url, data)
        final_url = f"{url}&X-Bogus={xbogus}" if params == "" else f"{url}&{params}&X-Bogus={xbogus}"
        return final_url


class SecUidManager:
    """Converts user unique_id to sec_uid."""

    headers: dict = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    }

    @classmethod
    def _is_fail(cls, res: httpx.Response) -> bool:
        """Check if the response is fail"""
        if res.status_code != 200:
            return True
        try:
            data = res.json()
            if data.get("statusCode", 0) != 0 or "userInfo" not in data:
                return True
        except (json.JSONDecodeError, AttributeError):
            return True
        return False

    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry_error_callback=lambda state: logger.error(f"get_sec_uid failed: {state.outcome.exception()}"),
        retry=retry_if_result(_is_fail)
    )
    def get_sec_uid(cls, unique_id: str) -> str:
        """Get sec_uid from unique_id"""
        url = f"https://www.tiktok.com/api/user/detail/?uniqueId={unique_id}"
        transport = httpx.HTTPTransport(retries=3)
        with httpx.Client(transport=transport) as client:
            response = client.get(url=url, headers=cls.headers)
        return response.json().get("userInfo", {}).get("user", {}).get("secUid")


def is_response_success(response: httpx.Response) -> bool:
    """Check if the response is successful"""
    if response.status_code == 200 and response.json().get("status_code") == 0:
        return True
    logger.error(f"response is not success, status_code: {response.status_code}, response: {response.text}")
    return False


class BogusManager:
    @classmethod
    def xb_str_2_endpoint(cls, user_agent: str, endpoint: str) -> str:
        try:
            final_endpoint = XB(user_agent).getXBogus(endpoint)
        except Exception as e:
            raise RuntimeError("Failed to generate X-Bogus: {0})".format(e))

        return final_endpoint[0]

    @classmethod
    def model_2_endpoint(cls, base_endpoint: str, params: dict, user_agent: str) -> str:
        if not isinstance(params, dict):
            raise TypeError("Parameters must be dictionary type")

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            xb_value = XB(user_agent).getXBogus(param_str)
        except Exception as e:
            raise RuntimeError("Failed to generate X-Bogus: {0})".format(e))

        separator = "&" if "?" in base_endpoint else "?"

        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"

        return final_endpoint


class SecUserIdFetcher:
    _TIKTOK_SECUID_PARREN = re.compile(
        r"<script id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\" type=\"application/json\">(.*?)</script>"
    )
    _TIKTOK_UNIQUEID_PARREN = re.compile(r"/@([^/?]*)")
    _TIKTOK_NOTFOUND_PARREN = re.compile(r"notfound")

    @classmethod
    async def get_secuid(cls, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("Input parameter must be string")

        url = extract_valid_urls(url)

        if url is None:
            raise APINotFoundError("Input URL is invalid. Class name: {0}".format(cls.__name__))

        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
                transport=transport, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)
                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PARREN.search(str(response.url)):
                        raise APINotFoundError("Page unavailable, possibly due to regional restrictions (proxy). Class name: {0}"
                                               .format(cls.__name__))

                    match = cls._TIKTOK_SECUID_PARREN.search(str(response.text))
                    if not match:
                        raise APIResponseError("Not found {0} in response, check if link is user homepage. Class name: {1}"
                                               .format("sec_uid", cls.__name__))

                    data = json.loads(match.group(1))
                    default_scope = data.get("__DEFAULT_SCOPE__", {})
                    user_detail = default_scope.get("webapp.user-detail", {})
                    user_info = user_detail.get("userInfo", {}).get("user", {})
                    sec_uid = user_info.get("secUid")

                    if sec_uid is None:
                        raise RuntimeError("Failed to get {0}, {1}".format(sec_uid, user_info))

                    return sec_uid
                else:
                    raise ConnectionError("Interface status code exception, please check and retry")

            except httpx.RequestError as exc:
                raise APIConnectionError("Request endpoint failed, please check current network environment. Link: {0}, Proxy: {1}, Class name: {2}, Exception details: {3}"
                                         .format(url, TokenManager.proxies, cls.__name__, exc))

    @classmethod
    async def get_all_secuid(cls, urls: list) -> list:
        if not isinstance(urls, list):
            raise TypeError("Parameter must be list type")

        urls = extract_valid_urls(urls)

        if urls == []:
            raise APINotFoundError("Input URL List is invalid. Class name: {0}".format(cls.__name__))

        secuids = [cls.get_secuid(url) for url in urls]
        return await asyncio.gather(*secuids)

    @classmethod
    async def get_uniqueid(cls, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("Input parameter must be string")

        url = extract_valid_urls(url)

        if url is None:
            raise APINotFoundError("Input URL is invalid. Class name: {0}".format(cls.__name__))

        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
                transport=transport, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PARREN.search(str(response.url)):
                        raise APINotFoundError("Page unavailable, possibly due to regional restrictions (proxy). Class name: {0}"
                                               .format(cls.__name__))

                    match = cls._TIKTOK_UNIQUEID_PARREN.search(str(response.url))
                    if not match:
                        raise APIResponseError("Not found {0} in response".format("unique_id"))

                    unique_id = match.group(1)

                    if unique_id is None:
                        raise RuntimeError("Failed to get {0}, {1}".format("unique_id", response.url))

                    return unique_id
                else:
                    raise ConnectionError("Interface status code exception {0}, please check and retry".format(response.status_code))

            except httpx.RequestError:
                raise APIConnectionError("Failed to connect endpoint, check network environment or proxy: {0} Proxy: {1} Class name: {2}"
                                         .format(url, TokenManager.proxies, cls.__name__))

    @classmethod
    async def get_all_uniqueid(cls, urls: list) -> list:
        if not isinstance(urls, list):
            raise TypeError("Parameter must be list type")

        urls = extract_valid_urls(urls)

        if urls == []:
            raise APINotFoundError("Input URL List is invalid. Class name: {0}".format(cls.__name__))

        unique_ids = [cls.get_uniqueid(url) for url in urls]
        return await asyncio.gather(*unique_ids)


class AwemeIdFetcher:
    _TIKTOK_AWEMEID_PATTERN = re.compile(r"video/(\d+)")
    _TIKTOK_PHOTOID_PATTERN = re.compile(r"photo/(\d+)")
    _TIKTOK_NOTFOUND_PATTERN = re.compile(r"notfound")

    @classmethod
    async def get_aweme_id(cls, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("Input parameter must be string")

        url = extract_valid_urls(url)

        if url is None:
            raise APINotFoundError("Input URL is invalid. Class name: {0}".format(cls.__name__))

        if "tiktok" and "@" in url:
            print(f"Input URL does not need redirection: {url}")
            video_match = cls._TIKTOK_AWEMEID_PATTERN.search(url)
            photo_match = cls._TIKTOK_PHOTOID_PATTERN.search(url)

            if not video_match and not photo_match:
                raise APIResponseError("Not found aweme_id or photo_id in response")

            aweme_id = video_match.group(1) if video_match else photo_match.group(1)

            if aweme_id is None:
                raise RuntimeError("Failed to get aweme_id or photo_id, {0}".format(url))

            return aweme_id

        print(f"Input URL needs redirection: {url}")
        transport = httpx.AsyncHTTPTransport(retries=10)
        async with httpx.AsyncClient(
                transport=transport, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PATTERN.search(str(response.url)):
                        raise APINotFoundError("Page unavailable, possibly due to regional restrictions (proxy). Class name: {0}"
                                               .format(cls.__name__))

                    video_match = cls._TIKTOK_AWEMEID_PATTERN.search(str(response.url))
                    photo_match = cls._TIKTOK_PHOTOID_PATTERN.search(str(response.url))

                    if not video_match and not photo_match:
                        raise APIResponseError("Not found aweme_id or photo_id in response")

                    aweme_id = video_match.group(1) if video_match else photo_match.group(1)

                    if aweme_id is None:
                        raise RuntimeError("Failed to get aweme_id or photo_id, {0}".format(response.url))

                    return aweme_id
                else:
                    raise ConnectionError("Interface status code exception {0}, please check and retry".format(response.status_code))

            except httpx.RequestError as exc:
                raise APIConnectionError("Request endpoint failed, please check current network environment. Link: {0}, Proxy: {1}, Class name: {2}, Exception details: {3}"
                                         .format(url, TokenManager.proxies, cls.__name__, exc))

    @classmethod
    async def get_all_aweme_id(cls, urls: list) -> list:
        if not isinstance(urls, list):
            raise TypeError("Parameter must be list type")

        urls = extract_valid_urls(urls)

        if urls == []:
            raise APINotFoundError("Input URL List is invalid. Class name: {0}".format(cls.__name__))

        aweme_ids = [cls.get_aweme_id(url) for url in urls]
        return await asyncio.gather(*aweme_ids)


def format_file_name(
        naming_template: str,
        aweme_data: dict = {},
        custom_fields: dict = {},
) -> str:
    os_limit = {
        "win32": 200,
        "cygwin": 60,
        "darwin": 60,
        "linux": 60,
    }

    fields = {
        "create": aweme_data.get("createTime", ""),
        "nickname": aweme_data.get("nickname", ""),
        "aweme_id": aweme_data.get("aweme_id", ""),
        "desc": split_filename(aweme_data.get("desc", ""), os_limit),
        "uid": aweme_data.get("uid", ""),
    }

    if custom_fields:
        fields.update(custom_fields)

    try:
        return naming_template.format(**fields)
    except KeyError as e:
        raise KeyError("File name template field {0} does not exist, please check".format(e))


def create_user_folder(kwargs: dict, nickname: Union[str, int]) -> Path:
    if not isinstance(kwargs, dict):
        raise TypeError("kwargs parameter must be dictionary")

    base_path = Path(kwargs.get("path", "Download"))

    user_path = (
            base_path / "tiktok" / kwargs.get("mode", "PLEASE_SETUP_MODE") / str(nickname)
    )

    resolve_user_path = user_path.resolve()

    resolve_user_path.mkdir(parents=True, exist_ok=True)

    return resolve_user_path


def rename_user_folder(old_path: Path, new_nickname: str) -> Path:
    parent_directory = old_path.parent

    new_path = old_path.rename(parent_directory / new_nickname).resolve()

    return new_path


def create_or_rename_user_folder(
        kwargs: dict, local_user_data: dict, current_nickname: str
) -> Path:
    user_path = create_user_folder(kwargs, current_nickname)

    if not local_user_data:
        return user_path

    if local_user_data.get("nickname") != current_nickname:
        user_path = rename_user_folder(user_path, current_nickname)

    return user_path
