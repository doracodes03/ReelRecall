import { useEffect, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import AuthPage from './routes/AuthPage';
import HomePage from './routes/HomePage';
import LibraryPage from './routes/LibraryPage';
import SearchPage from './routes/SearchPage';
import VideoDetailsPage from './routes/VideoDetailsPage';
import { getAccessToken } from './services/api';
import { getCurrentUser, signOut } from './services/auth';

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checkingSession, setCheckingSession] = useState(Boolean(getAccessToken()));

  useEffect(() => {
    if (!getAccessToken()) return;
    getCurrentUser()
      .then(() => setAuthenticated(true))
      .catch(() => {
        signOut();
        setAuthenticated(false);
      })
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) {
    return <main className="grid min-h-screen place-items-center text-slate-600">Loading your library...</main>;
  }
  if (!authenticated) {
    return <AuthPage onAuthenticated={() => setAuthenticated(true)} />;
  }

  return (
    <AppLayout onSignOut={() => {
      signOut();
      setAuthenticated(false);
    }}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/videos/:id" element={<VideoDetailsPage />} />
      </Routes>
    </AppLayout>
  );
}
