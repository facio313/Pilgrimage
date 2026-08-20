import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createRoute, shareRoute, type Route } from '../api/routes';
import { useAuthStore } from '../store/auth';
import { useRouteDraftStore, type TransportMode } from '../store/route';

const TRANSPORT_OPTIONS: { value: TransportMode; label: string }[] = [
  { value: 'mixed', label: '혼합' },
  { value: 'car', label: '자동차' },
  { value: 'bus', label: '버스' },
  { value: 'train', label: '기차' },
  { value: 'walking', label: '도보' },
  { value: 'bicycle', label: '자전거' },
];

export function RouteSavePage() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { theme, spotIds, transportMode, setTransport, reset } = useRouteDraftStore();

  const [title, setTitle] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedRoute, setSavedRoute] = useState<Route | null>(null);
  const [shareLink, setShareLink] = useState<string | null>(null);

  if (!accessToken) {
    return (
      <div style={pageStyle}>
        <p>로그인이 필요합니다.</p>
        <Link to="/">홈으로</Link>
      </div>
    );
  }

  if (spotIds.length === 0 && !savedRoute) {
    return (
      <div style={pageStyle}>
        <p>선택된 장소가 없습니다.</p>
        <Link to="/map">지도로 돌아가기</Link>
      </div>
    );
  }

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const route = await createRoute({
        title,
        theme_tags: theme ? [theme] : [],
        transport_mode: transportMode,
        is_public: isPublic,
        spot_ids: spotIds,
      });
      setSavedRoute(route);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장 실패');
    } finally {
      setSubmitting(false);
    }
  };

  const onShare = async () => {
    if (!savedRoute) return;
    try {
      const { share_token } = await shareRoute(savedRoute.id);
      setShareLink(`${window.location.origin}/pilgrimage/shared/${share_token}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '공유 링크 생성 실패');
    }
  };

  if (savedRoute) {
    return (
      <div style={pageStyle}>
        <h2 style={{ marginTop: 0 }}>저장 완료</h2>
        <section style={cardStyle}>
          <p><strong>{savedRoute.title}</strong></p>
          <p>총 거리: {savedRoute.total_distance_km} km</p>
          <p>예상 비용: {savedRoute.total_estimated_cost.toLocaleString()} 원</p>
          <p>장소 수: {savedRoute.route_spots.length}</p>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button onClick={onShare} style={primaryBtn}>공유 링크 생성</button>
            <button onClick={() => navigate('/themes')} style={secondaryBtn}>새 경로 만들기</button>
          </div>
          {shareLink && (
            <div style={{ marginTop: 12, padding: 10, background: '#f4f6fb', borderRadius: 6 }}>
              <div style={{ fontSize: 13, color: '#555' }}>공유 링크 (로그인 없이 열람 가능):</div>
              <code style={{ fontSize: 13 }}>{shareLink}</code>
            </div>
          )}
        </section>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <h2 style={{ marginTop: 0 }}>경로 저장</h2>
      <p style={{ color: '#666' }}>선택된 장소 {spotIds.length}개</p>

      <form onSubmit={onSave} style={{ ...cardStyle, display: 'grid', gap: 12 }}>
        <input
          type="text"
          placeholder="경로 제목"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          style={inputStyle}
        />
        <label>
          이동 수단
          <select
            value={transportMode}
            onChange={(e) => setTransport(e.target.value as TransportMode)}
            style={{ ...inputStyle, marginLeft: 8 }}
          >
            {TRANSPORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={isPublic}
            onChange={(e) => setIsPublic(e.target.checked)}
          />
          {' '}공개 (다른 사용자가 fork 가능)
        </label>
        <button type="submit" disabled={submitting} style={primaryBtn}>
          {submitting ? '저장 중...' : '저장하기'}
        </button>
        {error && <div style={{ color: '#c00' }}>{error}</div>}
      </form>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: 560,
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

const secondaryBtn: React.CSSProperties = {
  padding: '10px 16px',
  fontSize: 14,
  border: '1px solid #ccc',
  borderRadius: 6,
  background: '#fff',
  cursor: 'pointer',
};
