import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import "./index.css";

import LoginPage from "./pages/LoginPage";
import CasesPage from "./pages/CasesPage";
import NewCasePage from "./pages/NewCasePage";
import ChatPage from "./pages/ChatPage";
import VerdictPage from "./pages/VerdictPage";
import JoinPage from "./pages/JoinPage";

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen bg-cream flex items-center justify-center">
      <p className="font-serif text-ink/40">로딩 중...</p>
    </div>
  );
  return user ? children : <Navigate to="/login" replace />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/join/:token" element={<JoinPage />} />
          <Route path="/cases" element={<PrivateRoute><CasesPage /></PrivateRoute>} />
          <Route path="/cases/new" element={<PrivateRoute><NewCasePage /></PrivateRoute>} />
          <Route path="/cases/:id/chat" element={<PrivateRoute><ChatPage /></PrivateRoute>} />
          <Route path="/cases/:id/verdict" element={<PrivateRoute><VerdictPage /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/cases" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
