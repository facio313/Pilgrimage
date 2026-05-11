import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MapPage } from './pages/MapPage';
import { ThemeSelectPage } from './pages/ThemeSelectPage';
import { RouteSavePage } from './pages/RouteSavePage';
import { VisitPage } from './pages/VisitPage';
import { ReviewPage } from './pages/ReviewPage';
import { SharedRoutePage } from './pages/SharedRoutePage';
import { AutoRoutePage } from './pages/AutoRoutePage';
import { SpotDetailPage } from './pages/SpotDetailPage';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
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
