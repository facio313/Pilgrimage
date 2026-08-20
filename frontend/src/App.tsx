import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MapPage } from './pages/MapPage';
import { ThemeSelectPage } from './pages/ThemeSelectPage';
import { RouteSavePage } from './pages/RouteSavePage';
import { VisitPage } from './pages/VisitPage';
import { ReviewPage } from './pages/ReviewPage';
import { SharedRoutePage } from './pages/SharedRoutePage';
import { AutoRoutePage } from './pages/AutoRoutePage';
import { SpotDetailPage } from './pages/SpotDetailPage';
import { exchangeSso } from './api/auth';
import { useAuthStore } from './store/auth';

const queryClient = new QueryClient();

function App() {
  const ssoEnabled = import.meta.env.VITE_SSO_ENABLED === 'true';
  const publicShare = /^\/pilgrimage\/shared\/[^/]+\/?$/.test(window.location.pathname);
  const setTokens = useAuthStore((state) => state.setTokens);
  const clear = useAuthStore((state) => state.clear);
  const [ssoState, setSsoState] = useState<'ready' | 'loading' | 'error'>(
    ssoEnabled && !publicShare ? 'loading' : 'ready',
  );

  useEffect(() => {
    if (!ssoEnabled || publicShare) return;
    let active = true;
    exchangeSso()
      .then((response) => {
        if (!active) return;
        setTokens(response.access, response.refresh, response.email, response.nickname);
        setSsoState('ready');
      })
      .catch(() => {
        if (!active) return;
        clear();
        setSsoState('error');
      });
    return () => {
      active = false;
    };
  }, [clear, publicShare, setTokens, ssoEnabled]);

  if (ssoState !== 'ready') {
    return (
      <main style={{ padding: 24 }} role="status">
        {ssoState === 'loading' ? '통합 로그인을 확인하고 있습니다…' : (
          <>
            <p>통합 로그인 정보를 확인하지 못했습니다.</p>
            <a href={`/sso/?rd=${encodeURIComponent(window.location.href)}`}>다시 로그인</a>
          </>
        )}
      </main>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/pilgrimage/">
        <Routes>
          <Route path="/" element={<MapPage />} />
          <Route path="/themes" element={<ThemeSelectPage />} />
          <Route path="/spot/:spotId" element={<SpotDetailPage />} />
          <Route path="/route/save" element={<RouteSavePage />} />
          <Route path="/route/auto" element={<AutoRoutePage />} />
          <Route path="/visit/:spotId" element={<VisitPage />} />
          <Route path="/review/:spotId" element={<ReviewPage />} />
          <Route path="/shared/:token" element={<SharedRoutePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
