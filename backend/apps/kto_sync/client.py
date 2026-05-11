from urllib.parse import unquote

import httpx
from decouple import config
from tenacity import retry, stop_after_attempt, wait_exponential

KTO_BASE_URL = "https://apis.data.go.kr/B551011"
KTO_TIMEOUT_SEC = 3.0


class KtoClient:
    def __init__(self, base_url: str = KTO_BASE_URL, service_key: str | None = None,
                 timeout_sec: float = KTO_TIMEOUT_SEC):
        raw_key = service_key or config("KTO_API_KEY", default="")
        # The .env stores a URL-encoded key; httpx will encode params again,
        # so decode once here to avoid double-encoding.
        self.service_key = unquote(raw_key)
        self.client = httpx.Client(base_url=base_url, timeout=timeout_sec)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self) -> None:
        self.client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _get(self, path: str, params: dict) -> dict:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def area_based_list(
        self,
        content_type_id: int,
        page_no: int = 1,
        num_of_rows: int = 100,
        area_code: int | None = None,
    ) -> dict:
        params = {
            "ServiceKey": self.service_key,
            "MobileOS": "ETC",
            "MobileApp": "Pilgrimage",
            "_type": "json",
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "contentTypeId": content_type_id,
        }
        if area_code is not None:
            params["areaCode"] = area_code
        data = self._get("/KorService2/areaBasedList2", params=params)
        return data["response"]["body"]
