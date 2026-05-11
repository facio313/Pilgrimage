import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.reviews.models import Review
from apps.spots.models import TouristSpot
from apps.users.models import User
from apps.visits.models import VisitLog

CENTERS = {
    "seoul_station": (37.5547, 126.9707),
    "sadang": (37.4764, 126.9816),
    "jongno3ga": (37.5710, 126.9920),
}

SAMPLE_SPOTS = [
    # ── Seoul Station area (35) ──
    ("남대문시장", "전통시장", ["shopping", "food"], 37.5593, 126.9774),
    ("숭례문", "문화재", ["heritage"], 37.5600, 126.9753),
    ("서울로7017", "도시공원", ["urban", "leisure"], 37.5553, 126.9720),
    ("약현성당", "문화재", ["heritage"], 37.5555, 126.9675),
    ("후암동 해방촌 카페거리", "카페", ["food", "urban"], 37.5450, 126.9780),
    ("남산타워 전망대", "관광지", ["nature", "urban"], 37.5512, 126.9882),
    ("백범광장", "공원", ["heritage", "nature"], 37.5530, 126.9680),
    ("청파동 맛집거리", "음식점", ["food"], 37.5530, 126.9650),
    ("남대문 손칼국수", "음식점", ["food"], 37.5588, 126.9742),
    ("봉래동 초밥골목", "음식점", ["food"], 37.5580, 126.9655),
    ("중림동 브런치카페", "카페", ["food"], 37.5600, 126.9640),
    ("만리재로 전망대", "전망대", ["nature"], 37.5520, 126.9630),
    ("회현동 먹거리타운", "음식점", ["food"], 37.5575, 126.9810),
    ("남산예장공원", "공원", ["nature"], 37.5535, 126.9830),
    ("명동성당", "문화재", ["heritage"], 37.5633, 126.9872),
    ("남산한옥마을", "전통마을", ["heritage", "family"], 37.5588, 126.9940),
    ("서울역사박물관 분관", "박물관", ["heritage"], 37.5605, 126.9635),
    ("마포대로 쇼핑거리", "쇼핑", ["shopping"], 37.5540, 126.9590),
    ("효창공원", "공원", ["nature", "family"], 37.5420, 126.9630),
    ("도원동 전통시장", "전통시장", ["shopping"], 37.5460, 126.9620),
    ("원효로 떡볶이골목", "음식점", ["food"], 37.5420, 126.9660),
    ("청파 수제버거집", "음식점", ["food"], 37.5500, 126.9670),
    ("갈월동 와인바거리", "음식점", ["food"], 37.5515, 126.9690),
    ("후암동 빈티지샵", "쇼핑", ["shopping"], 37.5470, 126.9740),
    ("남영동 갤러리카페", "카페", ["urban", "food"], 37.5445, 126.9720),
    ("용문동 포차거리", "음식점", ["food"], 37.5438, 126.9710),
    ("서계동 다문화거리", "음식점", ["food"], 37.5565, 126.9683),
    ("만리동 루프탑카페", "카페", ["food", "urban"], 37.5560, 126.9665),
    ("중림창고 갤러리", "갤러리", ["urban"], 37.5610, 126.9648),
    ("봉래동 전통한식집", "음식점", ["food"], 37.5562, 126.9642),
    ("서울역 광장 마켓", "전통시장", ["shopping"], 37.5550, 126.9730),
    ("한강대로 디저트길", "카페", ["food"], 37.5480, 126.9700),
    ("남산 둘레길 입구", "등산로", ["nature"], 37.5505, 126.9850),
    ("회현 지하상가", "쇼핑", ["shopping"], 37.5580, 126.9800),
    ("만리동 전망카페", "카페", ["food", "nature"], 37.5545, 126.9645),
    # ── Sadang Station area (33) ──
    ("관악산 등산로입구", "등산로", ["nature"], 37.4720, 126.9750),
    ("남현동 먹자골목", "음식점", ["food"], 37.4780, 126.9790),
    ("사당동 카페거리", "카페", ["food"], 37.4790, 126.9835),
    ("이수역 맛집타운", "음식점", ["food"], 37.4855, 126.9822),
    ("방배동 카페골목", "카페", ["food", "urban"], 37.4830, 126.9880),
    ("사당 문화의거리", "문화시설", ["urban"], 37.4770, 126.9818),
    ("남태령 전통시장", "전통시장", ["shopping"], 37.4700, 126.9840),
    ("관악구청 공원", "공원", ["nature", "family"], 37.4740, 126.9700),
    ("사당 수제맥주거리", "음식점", ["food"], 37.4775, 126.9850),
    ("방배 예술공간", "갤러리", ["urban"], 37.4810, 126.9900),
    ("남성역 족발골목", "음식점", ["food"], 37.4870, 126.9775),
    ("이수 쇼핑몰", "쇼핑", ["shopping"], 37.4860, 126.9810),
    ("사당 전통떡집", "음식점", ["food"], 37.4758, 126.9812),
    ("관악산 약수터", "자연", ["nature"], 37.4680, 126.9730),
    ("남현동 갤러리길", "갤러리", ["urban", "heritage"], 37.4795, 126.9780),
    ("방배 로데오거리", "쇼핑", ["shopping", "food"], 37.4840, 126.9860),
    ("사당동 고기집거리", "음식점", ["food"], 37.4760, 126.9855),
    ("이수 한식뷔페", "음식점", ["food"], 37.4845, 126.9840),
    ("남태령 솔밭공원", "공원", ["nature"], 37.4690, 126.9810),
    ("사당 시민공원", "공원", ["nature", "family"], 37.4780, 126.9740),
    ("방배동 브런치카페", "카페", ["food"], 37.4825, 126.9870),
    ("관악산 전망데크", "전망대", ["nature"], 37.4710, 126.9760),
    ("사당 야시장", "전통시장", ["shopping", "food"], 37.4768, 126.9828),
    ("이수 디저트거리", "카페", ["food"], 37.4850, 126.9850),
    ("남성역 파스타집", "음식점", ["food"], 37.4878, 126.9790),
    ("방배동 중고서점", "서점", ["urban"], 37.4820, 126.9890),
    ("사당 전통주 바", "음식점", ["food"], 37.4772, 126.9808),
    ("관악 자연학습장", "공원", ["nature", "family"], 37.4695, 126.9780),
    ("남현동 빵집거리", "카페", ["food"], 37.4788, 126.9775),
    ("이수 헬스파크", "레저", ["leisure"], 37.4842, 126.9798),
    ("사당역 지하상가", "쇼핑", ["shopping"], 37.4765, 126.9820),
    ("방배 한옥갤러리", "갤러리", ["heritage", "urban"], 37.4815, 126.9910),
    ("관악산 둘레길", "등산로", ["nature", "leisure"], 37.4670, 126.9770),
    # ── Jongno 3-ga Station area (32) ──
    ("탑골공원", "공원", ["heritage"], 37.5718, 126.9885),
    ("종묘", "문화재", ["heritage"], 37.5741, 126.9944),
    ("익선동 한옥마을", "전통마을", ["heritage", "urban"], 37.5729, 126.9879),
    ("광장시장", "전통시장", ["food", "shopping"], 37.5700, 126.9995),
    ("세운상가", "쇼핑", ["shopping", "urban"], 37.5680, 126.9920),
    ("낙원상가 악기골목", "쇼핑", ["shopping"], 37.5735, 126.9870),
    ("창경궁", "문화재", ["heritage"], 37.5790, 126.9960),
    ("창덕궁", "문화재", ["heritage"], 37.5800, 126.9910),
    ("종로 귀금속거리", "쇼핑", ["shopping"], 37.5705, 126.9875),
    ("을지로 노포거리", "음식점", ["food"], 37.5660, 126.9910),
    ("을지로 카페골목", "카페", ["food", "urban"], 37.5668, 126.9935),
    ("인사동 전통공예길", "쇼핑", ["shopping", "heritage"], 37.5740, 126.9852),
    ("청계천 산책로", "공원", ["nature", "urban"], 37.5690, 126.9890),
    ("종로3가 먹자골목", "음식점", ["food"], 37.5705, 126.9928),
    ("묘동 전통주거리", "음식점", ["food"], 37.5728, 126.9905),
    ("돈화문로 카페거리", "카페", ["food", "urban"], 37.5750, 126.9900),
    ("종로 보석상가", "쇼핑", ["shopping"], 37.5700, 126.9865),
    ("북촌 한옥마을", "전통마을", ["heritage", "urban"], 37.5825, 126.9850),
    ("삼청동 갤러리길", "갤러리", ["urban", "heritage"], 37.5810, 126.9815),
    ("창신동 봉제거리", "쇼핑", ["shopping"], 37.5762, 126.9990),
    ("동대문 패션타운", "쇼핑", ["shopping"], 37.5710, 127.0070),
    ("율곡로 한식거리", "음식점", ["food"], 37.5760, 126.9870),
    ("낙산공원", "공원", ["nature"], 37.5800, 127.0065),
    ("마로니에공원", "공원", ["urban", "nature"], 37.5802, 127.0030),
    ("이화동 벽화마을", "전통마을", ["urban"], 37.5785, 127.0050),
    ("광장시장 빈대떡골목", "음식점", ["food"], 37.5698, 127.0005),
    ("종로 포장마차거리", "음식점", ["food"], 37.5712, 126.9935),
    ("인사동 전통찻집", "카페", ["food", "heritage"], 37.5745, 126.9840),
    ("창덕궁 후원", "공원", ["nature", "heritage"], 37.5820, 126.9930),
    ("비원 전통정원", "공원", ["nature", "heritage"], 37.5815, 126.9945),
    ("종묘공원 산책로", "공원", ["heritage", "nature"], 37.5735, 126.9960),
    ("을지로 힙거리", "카페", ["food", "urban"], 37.5665, 126.9945),
]

SAMPLE_USERS = [
    ("traveler1@test.com", "여행가람"),
    ("traveler2@test.com", "길따라서"),
    ("foodie@test.com", "맛있는발견"),
    ("hiker@test.com", "산타러가자"),
    ("urbanexplorer@test.com", "도시탐험가"),
    ("culturelover@test.com", "문화사랑"),
    ("shopaholic@test.com", "쇼핑매니아"),
    ("cafehopper@test.com", "카페투어"),
]

REVIEW_BODIES = [
    "분위기가 정말 좋았어요. 다음에 또 방문하고 싶습니다.",
    "위치가 좋고 접근성이 뛰어나요. 추천합니다!",
    "사진 찍기 좋은 곳이에요. 인스타 감성 넘칩니다.",
    "가격 대비 만족도가 높았습니다.",
    "주변에 볼거리가 많아서 함께 둘러보기 좋아요.",
    "조용하고 한적해서 여유롭게 즐길 수 있었어요.",
    "주차가 좀 불편하지만 그래도 갈 만한 곳입니다.",
    "평일에 가면 한산해서 좋습니다.",
    "주말에는 사람이 많으니 일찍 가는 게 좋아요.",
    "아이들과 함께 가기 좋은 장소입니다.",
    "데이트 코스로 강추해요!",
    "혼자 가도 충분히 즐길 수 있는 곳이에요.",
    "전통적인 멋이 느껴지는 곳입니다.",
    "현지인 맛집이에요. 관광객한테 안 알려진 보석 같은 곳.",
    "계절마다 다른 매력이 있어서 자주 방문합니다.",
    "야경이 정말 예뻐요. 밤에 꼭 가보세요.",
    "한국 문화를 체험하기에 최적의 장소예요.",
    "교통편이 좋아서 접근하기 편합니다.",
    "산책하기 딱 좋은 코스가 있어요.",
    "맛있는 음식점이 주변에 많아서 좋았습니다.",
    "역사적 의미가 깊은 곳이라 배울 게 많아요.",
    "가이드 투어를 하면 더 재미있게 즐길 수 있어요.",
    "무료로 즐길 수 있어서 부담 없이 방문하기 좋습니다.",
    "서울 여행 필수 코스로 추천드립니다.",
    "외국인 친구에게도 추천했는데 아주 좋아하더라고요.",
]


class Command(BaseCommand):
    help = "Seed sample spots, users, visit logs, and reviews"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing sample data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            Review.objects.all().delete()
            VisitLog.objects.all().delete()
            TouristSpot.objects.filter(external_id__startswith="sample-").delete()
            User.objects.filter(email__endswith="@test.com").delete()
            self.stdout.write("Cleared existing sample data.")

        users = []
        for email, nickname in SAMPLE_USERS:
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "nickname": nickname,
                    "password": "!unusable",
                },
            )
            users.append(user)
        self.stdout.write(f"Users: {len(users)}")

        now = timezone.now()
        spots_created = 0
        reviews_created = 0

        for idx, (name, category, themes, lat, lng) in enumerate(SAMPLE_SPOTS):
            external_id = f"sample-{idx:04d}"
            spot, created = TouristSpot.objects.get_or_create(
                external_id=external_id,
                defaults={
                    "name": name,
                    "category": category,
                    "theme_tags": themes,
                    "location": Point(lng, lat, srid=4326),
                    "address": f"서울특별시 ({name})",
                    "entrance_fee": random.choice([0, 0, 0, 1000, 3000, 5000]),
                    "avg_cost": random.choice(
                        [0, 5000, 8000, 10000, 15000, 20000, 30000]
                    ),
                    "avg_stay_minutes": random.choice([30, 45, 60, 90, 120]),
                    "synced_at": now,
                },
            )
            if created:
                spots_created += 1

            num_reviews = random.randint(3, 7)
            review_users = random.sample(users, min(num_reviews, len(users)))

            ratings = []
            for review_user in review_users:
                if VisitLog.objects.filter(user=review_user, spot=spot).exists():
                    continue

                visit_start = now - timedelta(
                    days=random.randint(1, 90),
                    hours=random.randint(0, 23),
                )
                visit = VisitLog.objects.create(
                    user=review_user,
                    spot=spot,
                    status=VisitLog.Status.CERTIFIED,
                    stay_start_at=visit_start,
                    stay_end_at=visit_start + timedelta(minutes=random.randint(30, 120)),
                    stay_minutes=random.randint(30, 120),
                    certified_at=visit_start + timedelta(minutes=30),
                )

                rating = random.choices(
                    [3, 4, 5, 2, 1], weights=[30, 35, 25, 8, 2]
                )[0]
                ratings.append(rating)
                Review.objects.create(
                    visit_log=visit,
                    spot=spot,
                    user=review_user,
                    rating=rating,
                    body=random.choice(REVIEW_BODIES),
                    entrance_fee=spot.entrance_fee,
                    food_cost=random.choice([0, 5000, 8000, 12000, 15000]),
                    other_cost=random.choice([0, 0, 2000, 3000]),
                )
                reviews_created += 1

            if ratings:
                spot.avg_review_score = Decimal(
                    str(round(sum(ratings) / len(ratings), 2))
                )
                spot.save(update_fields=["avg_review_score"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {spots_created} spots, {reviews_created} reviews"
            )
        )
