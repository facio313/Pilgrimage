import { Link, useNavigate } from 'react-router-dom';
import { useRouteDraftStore } from '../store/route';

const THEMES: { key: string; label: string; emoji: string }[] = [
  { key: 'mixed', label: '혼합', emoji: '🌈' },
  { key: 'nature', label: '자연', emoji: '🌲' },
  { key: 'heritage', label: '유적', emoji: '🏯' },
  { key: 'urban', label: '도시', emoji: '🌆' },
  { key: 'festival', label: '축제', emoji: '🎉' },
  { key: 'leisure', label: '레저', emoji: '🚴' },
  { key: 'shopping', label: '쇼핑', emoji: '🛍️' },
  { key: 'food', label: '맛집', emoji: '🍜' },
  { key: 'camping', label: '캠핑', emoji: '🏕️' },
  { key: 'medical', label: '의료/웰니스', emoji: '🧘' },
  { key: 'family', label: '효도', emoji: '👨‍👩‍👧' },
];

export function ThemeSelectPage() {
  const navigate = useNavigate();
  const { setTheme, reset } = useRouteDraftStore();

  const onPick = (key: string) => {
    reset();
    setTheme(key);
    navigate('/');
  };

  return (
    <main className="theme-page">
      <section className="theme-panel">
        <div className="theme-panel__top">
          <button type="button" className="theme-back" onClick={() => navigate('/')}>
            ← 지도 화면으로 돌아가기
          </button>
          <Link className="theme-auto-link" to="/route/auto">
            자동 추천 받기 →
          </Link>
        </div>
        <h2>어떤 테마로 떠나시겠어요?</h2>
        <p>
          하나를 선택하면 지도에서 추천 장소를 보여드릴게요.
        </p>
        <div className="theme-grid">
        {THEMES.map((t) => (
          <button
            key={t.key}
            onClick={() => onPick(t.key)}
            className="theme-card"
          >
            <span className="theme-card__emoji">{t.emoji}</span>
            <span>{t.label}</span>
          </button>
        ))}
        </div>
      </section>
    </main>
  );
}
