import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Scale, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [form, setForm] = useState({ email: "", nickname: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get("redirect") || "/cases";

  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(form.email, form.password);
      } else {
        await register(form.email, form.nickname, form.password);
      }
      navigate(redirect);
    } catch (e) {
      setError(e.response?.data?.detail || "오류가 발생했습니다");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink flex items-center justify-center px-4">
      {/* 배경 패턴 */}
      <div className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: "repeating-linear-gradient(45deg, #c9a84c 0, #c9a84c 1px, transparent 0, transparent 50%)",
          backgroundSize: "20px 20px",
        }}
      />

      <div className="relative w-full max-w-sm animate-slide-up">
        {/* 로고 */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full border-2 border-gold/50 mb-4">
            <Scale className="w-8 h-8 text-gold" />
          </div>
          <h1 className="font-serif text-3xl text-gold tracking-widest">커플 재판소</h1>
          <p className="text-cream/40 text-sm mt-2 font-sans">사랑싸움도 공정하게</p>
        </div>

        {/* 카드 */}
        <div className="bg-cream rounded-xl p-8 shadow-2xl border border-gold/20">
          {/* 탭 */}
          <div className="flex mb-8 border-b border-gold/20">
            {["login", "register"].map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(""); }}
                className={`flex-1 pb-3 text-sm font-bold font-sans transition-colors ${
                  mode === m
                    ? "text-ink border-b-2 border-gold -mb-px"
                    : "text-ink/40 hover:text-ink/60"
                }`}
              >
                {m === "login" ? "로그인" : "회원가입"}
              </button>
            ))}
          </div>

          {/* 폼 */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-ink/60 mb-1.5 uppercase tracking-wider">이메일</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-white border border-gold/30 rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-gold transition-colors"
                placeholder="example@email.com"
              />
            </div>

            {mode === "register" && (
              <div>
                <label className="block text-xs font-bold text-ink/60 mb-1.5 uppercase tracking-wider">닉네임</label>
                <input
                  type="text"
                  value={form.nickname}
                  onChange={(e) => setForm({ ...form, nickname: e.target.value })}
                  className="w-full bg-white border border-gold/30 rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-gold transition-colors"
                  placeholder="재판에서 사용할 이름"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-ink/60 mb-1.5 uppercase tracking-wider">비밀번호</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                className="w-full bg-white border border-gold/30 rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-gold transition-colors"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-verdict-lose text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full bg-ink hover:bg-ink-light text-gold font-serif font-bold py-3 rounded-lg transition-colors disabled:opacity-50 tracking-widest mt-2"
            >
              {loading ? "처리 중..." : mode === "login" ? "입정 ⚖️" : "등록"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
