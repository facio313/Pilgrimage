from collections import defaultdict
from typing import Iterable

from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.spots.models import TouristSpot
from common.themes import THEME_CONTENT_TYPE_MAP

from .client import KtoClient


def _build_content_type_to_themes() -> dict[int, list[str]]:
    mapping: dict[int, list[str]] = defaultdict(list)
    for theme_key, content_type_ids in THEME_CONTENT_TYPE_MAP.items():
        for ctid in content_type_ids:
            mapping[ctid].append(theme_key)
    return dict(mapping)


CONTENT_TYPE_TO_THEMES = _build_content_type_to_themes()


def _all_content_type_ids() -> list[int]:
    seen: set[int] = set()
    for ids in THEME_CONTENT_TYPE_MAP.values():
        seen.update(ids)
    return sorted(seen)


def _coerce_item_list(items_field) -> list[dict]:
    # KTO sometimes returns "" when there are no items, a single dict, or a list.
    if not items_field:
        return []
    item = items_field.get("item") if isinstance(items_field, dict) else None
    if item is None:
        return []
    if isinstance(item, dict):
        return [item]
    return list(item)


def _upsert_spot(item: dict, content_type_id: int) -> bool:
    external_id = str(item.get("contentid") or "").strip()
    if not external_id:
        return False
    try:
        lng = float(item.get("mapx") or 0)
        lat = float(item.get("mapy") or 0)
    except (TypeError, ValueError):
        return False
    if lng == 0 and lat == 0:
        return False

    address_parts = [item.get("addr1") or "", item.get("addr2") or ""]
    address = " ".join(p for p in address_parts if p).strip()
    themes = CONTENT_TYPE_TO_THEMES.get(content_type_id, [])

    TouristSpot.objects.update_or_create(
        external_id=external_id,
        defaults={
            "name": (item.get("title") or "").strip(),
            "category": (item.get("cat3") or "").strip(),
            "theme_tags": themes,
            "location": Point(lng, lat, srid=4326),
            "address": address,
            "synced_at": timezone.now(),
        },
    )
    return True


def sync_spots(
    content_type_ids: Iterable[int] | None = None,
    num_of_rows: int = 100,
    max_pages: int | None = None,
) -> int:
    if content_type_ids is None:
        content_type_ids = _all_content_type_ids()

    total = 0
    with KtoClient() as client:
        for ctid in content_type_ids:
            page = 1
            while True:
                body = client.area_based_list(
                    content_type_id=ctid,
                    page_no=page,
                    num_of_rows=num_of_rows,
                )
                items = _coerce_item_list(body.get("items"))
                for item in items:
                    if _upsert_spot(item, ctid):
                        total += 1

                total_count = int(body.get("totalCount") or 0)
                if page * num_of_rows >= total_count:
                    break
                if max_pages is not None and page >= max_pages:
                    break
                page += 1
    return total
