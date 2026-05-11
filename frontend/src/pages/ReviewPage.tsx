import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getSpot } from '../api/spots';
import { createReview, listReviews } from '../api/reviews';
import { useAuthStore } from '../store/auth';

interface LocationState {
  visitLogId?: string;
}

export function ReviewPage() {
  const { spotId = '' } = useParams<{ spotId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const visitLogId = (location.state as LocationState | null)?.visitLogId;
  const accessToken = useAuthStore((s) => s.accessToken);

  const [rating, setRating] = useState(5);
  const [body, setBody] = useState('');
  const [entranceFee, setEntranceFee] = useState(0);
  const [foodCost, setFoodCost] = useState(0);
  const [otherCost, setOtherCost] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: spot } = useQuery({
    queryKey: ['spot', spotId],
    queryFn: () => getSpot(spotId),
    enabled: !!spotId,
  });

  const { data: reviews = [], refetch } = useQuery({
    queryKey: ['reviews', spotId],
    queryFn: () => listReviews(spotId),
    enabled: !!spotId,
  });

  if (!accessToken) {
    return (
      <div style={pageStyle}>
        <p>로그인이 필요합니다.</p>
        <Link to="/">홈으로</Link>
      </div>
    );
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!visitLogId) {
      setError('인증된 방문 기록이 없습니다. 먼저 GPS 인증을 받아주세요.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createReview({
        visit_log_id: visitLogId,
        rating,
        body,
        entrance_fee: entranceFee,
        food_cost: foodCost,
        other_cost: otherCost,
      });
      setBody('');
      await refetch();
      navigate(`/visit/${spotId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '리뷰 등록 실패');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={pageStyle}>
      <h2 style={{ marginTop: 0 }}>{spot?.name ?? '장소'} 리뷰</h2>

      <section style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>리뷰 작성</h3>
        {!visitLogId ? (
          <p style={{ color: '#c00' }}>
            CERTIFIED 방문 기록이 필요합니다.{' '}
            <Link to={`/visit/${spotId}`}>GPS 인증 페이지</Link>로 이동하세요.
          </p>
        ) : (
          <form onSubmit={onSubmit} style={{ display: 'grid', gap: 10 }}>
            <label>
              별점:&nbsp;
              <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <textarea
              placeholder="리뷰 내용"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={4}
              style={inputStyle}
            />
            <div style={{ display: 'grid', gap: 6, gridTemplateColumns: 'repeat(3, 1fr)' }}>
              <label>
                입장료
                <input
                  type="number"
                  value={entranceFee}
                  onChange={(e) => setEntranceFee(Number(e.target.value))}
                  style={inputStyle}
                />
              </label>
              <label>
                식비
                <input
                  type="number"
                  value={foodCost}
                  onChange={(e) => setFoodCost(Number(e.target.value))}
                  style={inputStyle}
                />
              </label>
              <label>
                기타
                <input
                  type="number"
                  value={otherCost}
                  onChange={(e) => setOtherCost(Number(e.target.value))}
                  style={inputStyle}
                />
              </label>
            </div>
            <button type="submit" disabled={submitting} style={primaryBtn}>
              {submitting ? '등록 중...' : '리뷰 등록'}
            </button>
            {error && <div style={{ color: '#c00' }}>{error}</div>}
          </form>
        )}
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>리뷰 ({reviews.length})</h3>
        {reviews.length === 0 && <p style={{ color: '#666' }}>아직 리뷰가 없습니다.</p>}
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
              <div style={{ marginTop: 6 }}>{r.body}</div>
            </li>
          ))}
        </ul>
      </section>
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
};

const inputStyle: React.CSSProperties = {
  padding: '8px 10px',
  fontSize: 14,
  border: '1px solid #ccc',
  borderRadius: 6,
  width: '100%',
};

const primaryBtn: React.CSSProperties = {
  padding: '10px 16px',
  fontSize: 14,
  border: 'none',
  borderRadius: 6,
  background: '#1a73e8',
  color: '#fff',
  cursor: 'pointer',
};
