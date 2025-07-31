from __future__ import annotations
from crawlers.base_crawler import BaseCrawler
from crawlers.utils.utils import get_user_agent, get_device_id
from crawlers.tiktok.web.utils import (
    is_response_success,
    TokenManager,
    BogusManager,
    SecUidManager
)
from crawlers.tiktok.web.endpoints import Endpoints
from crawlers.tiktok.web.models import PostComment, PostCommentReply
import httpx


class TikTokWebCrawler(BaseCrawler):
    """
    TikTok web crawler.
    """

    def __init__(self, **kwargs):
        """
        Initialize the TikTokWebCrawler.
        """
        self.headers = self.get_default_headers()
        super().__init__(max_retries=3, max_connections=50, crawler_headers=self.headers)
        # Each crawler instance gets its own state managers
        self.token_manager = TokenManager()
        self.bogus_manager = BogusManager(user_agent=self.headers.get("User-Agent"))

    def get_default_headers(self) -> dict:
        """
        Get default headers for TikTok web crawler.
        """
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.tiktok.com",
            "Referer": "https://www.tiktok.com/",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": get_user_agent(),
        }

    async def get_tiktok_headers(self) -> dict:
        """
        Get headers for TikTok web crawler.
        """
        transport = httpx.AsyncHTTPTransport(retries=3)
        device_id = get_device_id()
        cookies = await self.token_manager.get_cookies(Endpoints.URL_WEB, transport)
        ms_token = await self.token_manager.get_token("msToken", transport)
        ttwid = await self.token_manager.get_token("ttwid", transport)
        odin_tt = await self.token_manager.get_token("odin_tt", transport)

        self.headers.update({
            "Cookie": f"msToken={ms_token}; odin_tt={odin_tt}; ttwid={ttwid};"
        })
        return {"headers": self.headers, "device_id": device_id}

    async def fetch_post_comment(self, aweme_id: str, cursor: int = 0, count: int = 20, current_region: str = ""):
        """
        Fetch post comments from TikTok web.
        """
        async with self as crawler:
            params = PostComment(aweme_id=aweme_id, cursor=cursor, count=count, current_region=current_region)
            
            headers_data = await self.get_tiktok_headers()
            params.device_id = headers_data["device_id"]
            
            final_url = self.bogus_manager.get_final_url(url=Endpoints.URL_COMMENT, data=params.to_str())
            
            response = await crawler.fetch(
                url=final_url,
                headers=headers_data["headers"]
            )
            
            if is_response_success(response):
                return response.json()
            return None

    async def fetch_post_comment_reply(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20,
                                       current_region: str = ""):
        """
        Fetch post comment replies from TikTok web.
        """
        async with self as crawler:
            params = PostCommentReply(item_id=item_id, comment_id=comment_id, cursor=cursor, count=count,
                                      current_region=current_region)
            
            headers_data = await self.get_tiktok_headers()
            params.device_id = headers_data["device_id"]
            
            final_url = self.bogus_manager.get_final_url(url=Endpoints.URL_COMMENT_REPLY, data=params.to_str())
            
            response = await crawler.fetch(
                url=final_url,
                headers=headers_data["headers"]
            )
            
            if is_response_success(response):
                return response.json()
            return None