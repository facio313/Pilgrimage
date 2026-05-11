import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { autoRecommendRoute, type Route } from '../api/routes';
import { useAuthStore } from '../store/auth';
import type { TransportMode } from '../store/route';

const THEMES: { key: string; label: string }[] = [
  { key: 'mixed', label: '혼합' },
  { key: 'nature', label: '자연' },
  { key: 'heritage', label: '유적' },
  { key: 'urban', label: '도시' },
  { key: 'festival', label: '축제' },
  { key: 'leisure', label: '레저' },
  { key: 'shopping', label: '쇼핑' },
  { key: 'food', label: '맛집' },
  { key: 'camping', label: '캠핑' },
  { key: 'medical', label: '의료/웰니스' },
  { key: 'family', label: '효도' },
];

const TRANSPORT_OPTIONS: { value: TransportMode; label: string }[] = [
  { value: 'mixed', label: '혼합' },
  { value: 'car', label: '자동차' },
  { value: 'bus', label: '버스' },
  { value: 'train', label: '기차' },
  { value: 'walking', label: '도보' },
  { value: 'bicycle', label: '자전거' },
];

export function AutoRoutePage() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);

  const [theme, setTheme] = useState<string>('nature');
  const [nSpots, setNSpots] = useState(5);
  const [budgetMax, setBudgetMax] = useState(100_000);
  const [minRating, setMinRating] = useState(3.5);
  const [maxDistanceKm, setMaxDistanceKm] = useState(50);
  const [transportMode, setTransportMode] = useState<TransportMode>('car');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Route | null>(null);

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
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const route = await autoRecommendRoute({
        theme,
        n_spots: nSpots,
        budget_max: budgetMax,
        min_rating: minRating,
        max_distance_km: maxDistanceKm,
        transport_mode: transportMode,
      });
      setResult(route);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 501) {
        setError('자동 추천 엔진은 아직 준비 중입니다. 추후 제공 예정이에요.');
      } else if (axios.isAxiosError(err)) {
        const msg =
          (err.response?.data as { error?: { message?: string } } | undefined)?.error?.message ??
          err.message;
        setError(msg);
      } else {
        setError(err instanceof Error ? err.message : '추천 요청 실패');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={pageStyle}>
      <h2 style={{ marginTop: 0 }}>자동 경로 추천</h2>
      <p style={{ color: '#666' }}>
        조건을 입력하면 점수 엔진이 최적 경로를 자동으로 만들어 드려요.
      </p>

      <form onSubmit={onSubmit} style={{ ...cardStyle, display: 'grid', gap: 12 }}>
        <label>
          테마
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            style={{ ...inputStyle, marginLeft: 8 }}
          >
            {THEMES.map((t) => (
              <option key={t.key} value={t.key}>{t.label}</option>
            ))}
          </select>
        </label>

        <div style={gridStyle}>
          <label>
            장소 수
            <input
              type="number"
              min={1}
              max={20}
              value={nSpots}
              onChange={(e) => setNSpots(Number(e.target.value))}
              style={inputStyle}
            />
          </label>
          <label>
            예산 한도 (원)
            <input
              type="number"
              min={0}
              step={10_000}
              value={budgetMax}
              onChange={(e) => setBudgetMax(Number(e.target.value))}
              style={inputStyle}
            />
          </label>
        </div>

        <div style={gridStyle}>
          <label>
            최소 별점
            <input
              type="number"
              step={0.1}
              min={0}
              max={5}
              value={minRating}
              onChange={(e) => setMinRating(Number(e.target.value))}
              style={inputStyle}
            />
          </label>
          <label>
            최대 이동 거리 (km)
            <input
              type="number"
              min={1}
              value={maxDistanceKm}
              onChange={(e) => setMaxDistanceKm(Number(e.target.value))}
              style={inputStyle}
            />
          </label>
        </div>

        <label>
          이동 수단
          <select
            value={transportMode}
            onChange={(e) => setTransportMode(e.target.value as TransportMode)}
            style={{ ...inputStyle, marginLeft: 8 }}
          >
            {TRANSPORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <button type="submit" disabled={submitting} style={primaryBtn}>
          {submitting ? '추천 중...' : '추천 받기'}
        </button>

        {error && <div style={{ color: '#c00', fontSize: 13 }}>{error}</div>}
      </form>

      {result && (
        <section style={{ ...cardStyle, marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>추천 결과: {result.title}</h3>
          <div style={{ color: '#555', fontSize: 14, marginBottom: 8 }}>
            총 거리 {result.total_distance_km} km · 예상 비용 {result.total_estimated_cost.toLocaleString()}원 · 장소 {result.route_spots.length}개
          </div>
          <ol style={{ paddingLeft: 20 }}>
            {[...result.route_spots]
              .sort((a, b) => a.sequence_order - b.sequence_order)
              .map((rs) => (
                <li key={rs.spot.id} style={{ marginBottom: 6 }}>
                  <strong>{rs.spot.name}</strong>
                  <span style={{ color: '#777', marginLeft: 6, fontSize: 13 }}>
                    {rs.spot.address}
                  </span>
                </li>
              ))}
          </ol>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button
              onClick={() => navigate('/map')}
              style={secondaryBtn}
            >
              지도에서 수정
            </button>
            <button
              onClick={() => navigate('/route/save')}
              style={primaryBtn}
            >
              저장 페이지로
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: 600,
  margin: '0 auto',
  padding: '32px 20px',
};

const cardStyle: React.CSSProperties = {
  border: '1px solid #e2e2e2',
  borderRadius: 8,
  padding: 20,
  background: '#fff',
};

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: 10,
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

const secondaryBtn: React.CSSProperties = {
  padding: '10px 16px',
  fontSize: 14,
  border: '1px solid #ccc',
  borderRadius: 6,
  background: '#fff',
  cursor: 'pointer',
};
