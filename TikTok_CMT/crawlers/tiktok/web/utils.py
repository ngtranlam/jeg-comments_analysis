from __future__ import annotations
import httpx
import json
import random
import time
from tenacity import stop_after_attempt, retry, wait_fixed, retry_if_result
from crawlers.douyin.web.xbogus import XBogus as XBogusManager
from crawlers.utils.logger import logger
from crawlers.utils.api_exceptions import APIConnectionError, APIResponseError


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
