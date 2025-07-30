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

path = os.path.abspath(os.path.dirname(__file__))

with open(f"{path}/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class TokenManager:
    tiktok_manager = config.get("TokenManager").get("tiktok")
    token_conf = tiktok_manager.get("msToken", None)
    ttwid_conf = tiktok_manager.get("ttwid", None)
    odin_tt_conf = tiktok_manager.get("odin_tt", None)
    proxies_conf = tiktok_manager.get("proxies", None)
    proxies = {
        "http://": proxies_conf.get("http", None),
        "https://": proxies_conf.get("https", None),
    }

    @classmethod
    def gen_real_msToken(cls) -> str:
        payload = json.dumps(
            {
                "magic": cls.token_conf["magic"],
                "version": cls.token_conf["version"],
                "dataType": cls.token_conf["dataType"],
                "strData": cls.token_conf["strData"],
                "tspFromClient": get_timestamp(),
            }
        )

        headers = {
            "User-Agent": cls.token_conf["User-Agent"],
            "Content-Type": "application/json",
        }

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport) as client:
            try:
                response = client.post(
                    cls.token_conf["url"], headers=headers, content=payload
                )
                response.raise_for_status()

                msToken = str(httpx.Cookies(response.cookies).get("msToken"))

                return msToken

            except Exception as e:
                logger.error("TikTok msToken API error: {0}".format(e))
                logger.info("Current network cannot access TikTok server normally, using fake msToken to continue.")
                logger.info("TikTok related APIs probably cannot be used normally, please update proxy in (/tiktok/web/config.yaml).")
                logger.info("If you don't need to use TikTok related APIs, please ignore this message.")
                return cls.gen_false_msToken()

    @classmethod
    def gen_false_msToken(cls) -> str:
        return gen_random_str(146) + "=="

    @classmethod
    def gen_ttwid(cls, cookie: str) -> str:
        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport) as client:
            try:
                response = client.post(
                    cls.ttwid_conf["url"],
                    content=cls.ttwid_conf["data"],
                    headers={
                        "Cookie": cookie,
                        "Content-Type": "text/plain",
                    },
                )
                response.raise_for_status()

                ttwid = httpx.Cookies(response.cookies).get("ttwid")

                if ttwid is None:
                    raise APIResponseError("ttwid: Check failed, please update ttwid in config file")

                return ttwid

            except httpx.RequestError as exc:
                raise APIConnectionError("Request endpoint failed, please check current network environment. Link: {0}, Proxy: {1}, Class name: {2}, Exception details: {3}"
                                         .format(cls.ttwid_conf["url"], cls.proxies, cls.__name__, exc))

            except httpx.HTTPStatusError as e:
                if response.status_code == 401:
                    raise APIUnauthorizedError("Parameter validation failed, please update {0} in Douyin_TikTok_Download_API config file to match {1} new rules"
                                               .format("ttwid", "tiktok"))

                elif response.status_code == 404:
                    raise APINotFoundError("{0} API endpoint not found".format("ttwid"))
                else:
                    raise APIResponseError("Link: {0}, Status code {1}: {2}".format(
                        e.response.url, e.response.status_code, e.response.text))

    @classmethod
    def gen_odin_tt(cls):
        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport) as client:
            try:
                response = client.get(cls.odin_tt_conf["url"])
                response.raise_for_status()

                odin_tt = httpx.Cookies(response.cookies).get("odin_tt")

                if odin_tt is None:
                    raise APIResponseError("{0} content does not meet requirements".format("odin_tt"))

                return odin_tt

            except httpx.RequestError as exc:
                raise APIConnectionError("Request endpoint failed, please check current network environment. Link: {0}, Proxy: {1}, Class name: {2}, Exception details: {3}"
                                         .format(cls.odin_tt_conf["url"], cls.proxies, cls.__name__, exc))

            except httpx.HTTPStatusError as e:
                if response.status_code == 401:
                    raise APIUnauthorizedError("Parameter validation failed, please update {0} in Douyin_TikTok_Download_API config file to match {1} new rules"
                                               .format("odin_tt", "tiktok"))

                elif response.status_code == 404:
                    raise APINotFoundError("{0} API endpoint not found".format("odin_tt"))
                else:
                    raise APIResponseError("Link: {0}, Status code {1}: {2}".format(
                        e.response.url, e.response.status_code, e.response.text))

    @classmethod
    def reset(cls):
        """
        Resets the shared state of the TokenManager.
        This should be called before starting a new, independent crawl task.
        """
        cls.tokens = {}
        cls.cookies = {}


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
