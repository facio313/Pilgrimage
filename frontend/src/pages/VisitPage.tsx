import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getSpot } from '../api/spots';
import { certifyVisit, type VisitLog } from '../api/visits';
import { useGpsTracking } from '../hooks/useGpsTracking';
import { useAuthStore } from '../store/auth';

export function VisitPage() {
  const { spotId = '' } = useParams<{ spotId: string }>();
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [tracking, setTracking] = useState(false);
  const [visit, setVisit] = useState<VisitLog | null>(null);
  const [certifying, setCertifying] = useState(false);
  const [certifyError, setCertifyError] = useState<string | null>(null);

  const gps = useGpsTracking(tracking);

  const { data: spot, isLoading } = useQuery({
    queryKey: ['spot', spotId],
    queryFn: () => getSpot(spotId),
    enabled: !!spotId,
  });

  const onClose = () => navigate(-1);

  if (!accessToken) {
    return (
      <div style={backdropStyle} onClick={onClose}>
        <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
          <button style={closeBtnStyle} onClick={onClose} aria-label="닫기">&times;</button>
          <p>로그인이 필요합니다.</p>
          <Link to="/">홈으로</Link>
        </div>
      </div>
    );
  }

  const onCertify = async () => {
    setCertifying(true);
    setCertifyError(null);
    try {
      const log = await certifyVisit(spotId);
      setVisit(log);
      if (log.status === 'CERTIFIED') {
        setTracking(false);
      }
    } catch (err) {
      setCertifyError(err instanceof Error ? err.message : '인증 요청 실패');
    } finally {
      setCertifying(false);
    }
  };

  return (
    <div style={backdropStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <button style={closeBtnStyle} onClick={onClose} aria-label="닫기">&times;</button>

        <h2 style={{ marginTop: 0, marginBottom: 4, paddingRight: 28, fontSize: 18 }}>
          {isLoading ? '...' : spot?.name ?? '장소'}
        </h2>
        <p style={{ color: '#888', fontSize: 13, margin: '0 0 16px' }}>{spot?.address}</p>

        <section style={cardStyle}>
          <h3 style={{ marginTop: 0, fontSize: 15 }}>GPS 체류 인증</h3>
          <p style={{ color: '#555', fontSize: 13, margin: '0 0 12px' }}>
            200m 반경 내에서 30분 이상 머무르면 인증됩니다. 탭이 비활성화되면 일시 중지됩니다.
          </p>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {!tracking ? (
              <button onClick={() => setTracking(true)} style={primaryBtn}>
                GPS 추적 시작
              </button>
            ) : (
              <button onClick={() => setTracking(false)} style={secondaryBtn}>
                추적 중지
              </button>
            )}
            <button onClick={onCertify} disabled={certifying} style={primaryBtn}>
              {certifying ? '확인 중...' : '인증 요청'}
            </button>
          </div>

          <div style={{ fontSize: 13, color: '#666' }}>
            상태: {gps.active ? (gps.paused ? '일시정지 (탭 비활성)' : '추적 중') : '중지'}
            {gps.lastPosition && (
              <div>
                마지막 좌표: ({gps.lastPosition.lat.toFixed(5)}, {gps.lastPosition.lng.toFixed(5)})
              </div>
            )}
            {gps.error && <div style={{ color: '#c00' }}>{gps.error}</div>}
          </div>

          {visit && (
            <div style={{ marginTop: 16, padding: 12, background: '#f4f6fb', borderRadius: 6 }}>
              <strong>인증 결과:</strong> {visit.status}
              {visit.status === 'CERTIFIED' && (
                <div style={{ marginTop: 8 }}>
                  체류 {visit.stay_minutes}분 — 리뷰 작성 가능
                  <button
                    onClick={() => navigate(`/review/${spotId}`, { state: { visitLogId: visit.id } })}
                    style={{ ...primaryBtn, marginLeft: 12 }}
                  >
                    리뷰 작성
                  </button>
                </div>
              )}
              {visit.status === 'REJECTED' && (
                <div style={{ marginTop: 8, color: '#c00' }}>
                  속도 이상 감지 등으로 인증 거부됨
                </div>
              )}
            </div>
          )}
          {certifyError && <div style={{ color: '#c00', marginTop: 8 }}>{certifyError}</div>}
        </section>
      </div>
    </div>
  );
}

const backdropStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0, 0, 0, 0.45)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
  padding: '20px 16px',
};

const modalStyle: React.CSSProperties = {
  position: 'relative',
  width: '100%',
  maxWidth: 520,
  maxHeight: 'calc(100vh - 40px)',
  overflowY: 'auto',
  background: '#fff',
  borderRadius: 14,
  padding: '24px 20px 20px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.22)',
};

const closeBtnStyle: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  right: 14,
  width: 28,
  height: 28,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'none',
  border: '1.5px solid #d0d0d0',
  borderRadius: '50%',
  fontSize: 16,
  lineHeight: 1,
  color: '#555',
  cursor: 'pointer',
};

const cardStyle: React.CSSProperties = {
  border: '1px solid #e2e2e2',
  borderRadius: 8,
  padding: 16,
  background: '#fafafa',
};

const primaryBtn: React.CSSProperties = {
  padding: '9px 14px',
  fontSize: 13,
  border: 'none',
  borderRadius: 6,
  background: '#1a73e8',
  color: '#fff',
  cursor: 'pointer',
};

const secondaryBtn: React.CSSProperties = {
  padding: '9px 14px',
  fontSize: 13,
  border: '1px solid #ccc',
  borderRadius: 6,
  background: '#fff',
  cursor: 'pointer',
};
