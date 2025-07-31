import yaml
import os

from crawlers.base_crawler import BaseCrawler
from crawlers.tiktok.web.endpoints import TikTokAPIEndpoints
from crawlers.tiktok.web.utils import BogusManager
from crawlers.tiktok.web.models import PostComment, PostCommentReply

path = os.path.abspath(os.path.dirname(__file__))

with open(f"{path}/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class TikTokWebCrawler(BaseCrawler):
    """
    TikTok Web Crawler
    """

    def __init__(self, **kwargs):
        """
        Initialize the Crawler.
        """
        # Set headers for this instance
        if kwargs.get("headers") and isinstance(kwargs.get("headers"), dict):
            self.headers = kwargs["headers"]
        else:
            self.headers = self.get_default_headers()
        
        # Call parent constructor with the correct headers and other params
        super().__init__(
            crawler_headers=self.headers
            # Other parameters will use defaults from BaseCrawler's signature
        )

    @staticmethod
    def get_default_headers() -> dict:
        """
        Get default headers for the crawler.
        """
        tiktok_config = config["TokenManager"]["tiktok"]
        return {
            "User-Agent": tiktok_config["headers"]["User-Agent"],
            "Referer": tiktok_config["headers"]["Referer"],
            "Cookie": tiktok_config["headers"]["Cookie"],
        }

    async def get_tiktok_headers(self):
        tiktok_config = config["TokenManager"]["tiktok"]
        kwargs = {
            "headers": {
                "User-Agent": tiktok_config["headers"]["User-Agent"],
                "Referer": tiktok_config["headers"]["Referer"],
                "Cookie": tiktok_config["headers"]["Cookie"],
            },
            "proxies": {"http://": tiktok_config["proxies"]["http"],
                        "https://": tiktok_config["proxies"]["https"]}
        }
        return kwargs

    async def fetch_post_comment(self, aweme_id: str, cursor: int = 0, count: int = 20, current_region: str = ""):
        kwargs = await self.get_tiktok_headers()
        base_crawler = BaseCrawler(crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = PostComment(aweme_id=aweme_id, cursor=cursor, count=count, current_region=current_region)
            endpoint = BogusManager.model_2_endpoint(
                TikTokAPIEndpoints.POST_COMMENT, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response

    async def fetch_post_comment_reply(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20,
                                       current_region: str = ""):
        kwargs = await self.get_tiktok_headers()
        base_crawler = BaseCrawler(crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = PostCommentReply(item_id=item_id, comment_id=comment_id, cursor=cursor, count=count,
                                      current_region=current_region)
            endpoint = BogusManager.model_2_endpoint(
                TikTokAPIEndpoints.POST_COMMENT_REPLY, params.dict(), kwargs["headers"]["User-Agent"]
            )
            response = await crawler.fetch_get_json(endpoint)
        return response