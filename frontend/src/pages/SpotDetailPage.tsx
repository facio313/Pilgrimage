import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getSpot } from '../api/spots';
import { listReviews } from '../api/reviews';
import { useAuthStore } from '../store/auth';
import { useRouteDraftStore } from '../store/route';

export function SpotDetailPage() {
  const { spotId = '' } = useParams<{ spotId: string }>();
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { spotIds, addSpot, removeSpot } = useRouteDraftStore();

  const { data: spot, isLoading, error } = useQuery({
    queryKey: ['spot', spotId],
    queryFn: () => getSpot(spotId),
    enabled: !!spotId,
  });

  const { data: reviews = [] } = useQuery({
    queryKey: ['reviews', spotId],
    queryFn: () => listReviews(spotId),
    enabled: !!spotId,
  });

  if (isLoading) {
    return <div style={pageStyle}>로딩 중...</div>;
  }

  if (error || !spot) {
    return (
      <div style={pageStyle}>
        <p style={{ color: '#c00' }}>장소를 불러올 수 없습니다.</p>
        <Link to="/map">지도로 돌아가기</Link>
      </div>
    );
  }

  const inRoute = spotIds.includes(spot.id);

  return (
    <div style={pageStyle}>
      <h2 style={{ marginTop: 0 }}>{spot.name}</h2>
      <div style={{ color: '#555', fontSize: 14 }}>{spot.category} · {spot.address}</div>

      <section style={cardStyle}>
        <div style={twoColStyle}>
          <Stat label="평균 별점" value={Number(spot.avg_review_score).toFixed(2)} />
          <Stat label="입장료" value={`${spot.entrance_fee.toLocaleString()}원`} />
          <Stat label="평균 비용" value={`${spot.avg_cost.toLocaleString()}원`} />
          <Stat label="평균 체류" value={`${spot.avg_stay_minutes}분`} />
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          {accessToken && (inRoute ? (
            <button onClick={() => removeSpot(spot.id)} style={secondaryBtn}>경로에서 제거</button>
          ) : (
            <button onClick={() => addSpot(spot.id)} style={primaryBtn}>경로에 추가</button>
          ))}
          {accessToken && (
            <button onClick={() => navigate(`/visit/${spot.id}`)} style={secondaryBtn}>
              방문 인증
            </button>
          )}
          <button onClick={() => navigate('/map')} style={secondaryBtn}>지도로</button>
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>리뷰 ({reviews.length})</h3>
        {reviews.length === 0 ? (
          <p style={{ color: '#666' }}>아직 리뷰가 없습니다.</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {reviews.map((r) => (
              <li
                key={r.id}
                style={{
                  border: '1px solid #eee',
                  borderRadius: 6,
                  padding: 12,
                  marginBottom: 8,
                }}
              >
                <div>
                  <strong>★ {r.rating}</strong> · {r.user_nickname || '익명'}
                </div>
                {r.body && <div style={{ marginTop: 6 }}>{r.body}</div>}
                <div style={{ marginTop: 6, color: '#777', fontSize: 13 }}>
                  비용: 입장 {r.entrance_fee.toLocaleString()}원 · 식사 {r.food_cost.toLocaleString()}원 · 기타 {r.other_cost.toLocaleString()}원
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: '#888' }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: 640,
  margin: '0 auto',
  padding: '32px 20px',
};

const cardStyle: React.CSSProperties = {
  border: '1px solid #e2e2e2',
  borderRadius: 8,
  padding: 20,
  background: '#fff',
  marginTop: 16,
};

const twoColStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, 1fr)',
  gap: 12,
};

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  fontSize: 13,
  border: 'none',
  borderRadius: 6,
  background: '#1a73e8',
  color: '#fff',
  cursor: 'pointer',
};

const secondaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  fontSize: 13,
  border: '1px solid #ccc',
  borderRadius: 6,
  background: '#fff',
  cursor: 'pointer',
};
