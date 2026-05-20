import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Scale, LogOut, Plus } from "lucide-react";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-cream">
      {/* 헤더 */}
      <header className="bg-ink border-b-2 border-gold/50 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/cases" className="flex items-center gap-2 group">
            <Scale className="w-6 h-6 text-gold group-hover:animate-gavel transition-all" />
            <span className="font-serif text-xl text-gold tracking-wider">커플 재판소</span>
          </Link>

          {user && (
            <div className="flex items-center gap-4">
              <span className="text-cream/60 text-sm font-sans">{user.nickname}</span>
              <Link
                to="/cases/new"
                className="flex items-center gap-1 bg-gold hover:bg-gold-light text-ink text-sm font-bold px-3 py-1.5 rounded transition-colors"
              >
                <Plus className="w-4 h-4" />
                새 재판
              </Link>
              <button
                onClick={handleLogout}
                className="text-cream/40 hover:text-cream transition-colors"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 메인 */}
      <main className="max-w-4xl mx-auto px-4 py-8 animate-fade-in">
        {children}
      </main>

      {/* 푸터 */}
      <footer className="text-center py-6 text-ink/30 text-xs font-sans">
        <p>⚖️ 커플 재판소 — 사랑싸움도 공정하게</p>
      </footer>
    </div>
  );
}
