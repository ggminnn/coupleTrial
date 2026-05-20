import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../lib/api";
import { Scale, Copy, Check } from "lucide-react";

const JUDGE_STYLES = [
  {
    value: "default",
    label: "기본 판사",
    emoji: "⚖️",
    desc: "공정하고 차분한 톤으로 판결합니다",
    cardClass: "border-gold/40 bg-white",
    selectedClass: "border-gold bg-gold/5 ring-2 ring-gold/30",
  },
  {
    value: "spicy",
    label: "매운맛 판사",
    emoji: "🌶️",
    desc: "직설적이고 독설 넘치는 판결을 내립니다",
    cardClass: "border-red-200 bg-white",
    selectedClass: "border-red-400 bg-red-50 ring-2 ring-red-300/40",
  },
];

export default function NewCasePage() {
  const [title, setTitle] = useState("");
  const [judgeStyle, setJudgeStyle] = useState("default");
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState(null);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  const handleCreate = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      const res = await api.post("/cases", { title, judgeStyle });
      setCreated(res.data);
    } finally {
      setLoading(false);
    }
  };

  const inviteLink = created
    ? `${window.location.origin}/join/${created.invite_token}`
    : "";

  const copyLink = () => {
    navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (created) {
    const selectedStyle = JUDGE_STYLES.find((s) => s.value === created.judge_style);
    return (
      <Layout>
        <div className="max-w-lg mx-auto text-center animate-slide-up">
          <div className="w-20 h-20 rounded-full bg-ink flex items-center justify-center mx-auto mb-6">
            <Scale className="w-10 h-10 text-gold animate-gavel" />
          </div>
          <h1 className="font-serif text-3xl text-ink mb-2">재판이 개정되었습니다</h1>
          <p className="text-ink/50 font-sans mb-8">아래 링크를 상대방에게 전달하세요</p>

          <div className="verdict-card mb-6">
            <p className="font-serif text-lg text-ink mb-1">{created.title}</p>
            <p className="text-ink/40 text-xs font-sans">사건번호: {created.id.slice(0, 8).toUpperCase()}</p>
            {selectedStyle && (
              <p className="text-ink/50 text-xs font-sans mt-2">
                {selectedStyle.emoji} {selectedStyle.label}
              </p>
            )}
          </div>

          {/* 초대 링크 */}
          <div className="bg-white border-2 border-dashed border-gold/40 rounded-xl p-4 mb-6">
            <p className="text-xs text-ink/50 font-sans mb-2 uppercase tracking-wider">피고 초대 링크</p>
            <p className="text-sm text-ink/70 font-sans break-all mb-3">{inviteLink}</p>
            <button
              onClick={copyLink}
              className="flex items-center gap-2 mx-auto bg-ink text-gold font-bold px-5 py-2 rounded-lg hover:bg-ink-light transition-colors"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied ? "복사됨!" : "링크 복사"}
            </button>
          </div>

          <button
            onClick={() => navigate(`/cases/${created.id}/chat`)}
            className="w-full bg-gold hover:bg-gold-light text-ink font-serif font-bold py-3 rounded-xl transition-colors text-lg"
          >
            내 주장 입력하러 가기 →
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-lg mx-auto animate-slide-up">
        <div className="text-center mb-10">
          <h1 className="font-serif text-3xl text-ink mb-2">새 재판 열기</h1>
          <p className="text-ink/50 font-sans text-sm">무엇 때문에 싸웠나요?</p>
        </div>

        <div className="bg-white border border-gold/20 rounded-2xl p-8 shadow-sm">
          <div className="court-divider">
            <span className="font-serif text-ink/40 text-sm">사건 개요</span>
          </div>

          <div className="mb-6">
            <label className="block text-xs font-bold text-ink/60 mb-2 uppercase tracking-wider">
              사건 제목
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              className="w-full bg-cream border border-gold/30 rounded-xl px-4 py-3 text-ink font-sans focus:outline-none focus:border-gold transition-colors text-sm"
              placeholder="예: 카톡 답장 늦게 한 사건, 약속 취소 관련"
              maxLength={50}
            />
            <p className="text-right text-xs text-ink/30 mt-1 font-sans">{title.length}/50</p>
          </div>

          {/* 판사 스타일 선택 */}
          <div className="mb-6">
            <label className="block text-xs font-bold text-ink/60 mb-3 uppercase tracking-wider">
              판사 스타일
            </label>
            <div className="grid grid-cols-2 gap-3">
              {JUDGE_STYLES.map((style) => (
                <button
                  key={style.value}
                  type="button"
                  onClick={() => setJudgeStyle(style.value)}
                  className={`border-2 rounded-xl p-4 text-left transition-all ${
                    judgeStyle === style.value ? style.selectedClass : style.cardClass
                  }`}
                >
                  <span className="text-2xl block mb-1">{style.emoji}</span>
                  <p className="font-serif text-sm font-bold text-ink">{style.label}</p>
                  <p className="text-xs text-ink/50 font-sans mt-1 leading-tight">{style.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-cream rounded-xl p-4 mb-6 text-sm text-ink/60 font-sans space-y-2">
            <p>📋 재판 진행 방식</p>
            <ol className="list-decimal list-inside space-y-1 text-xs">
              <li>재판 생성 후 상대방에게 초대 링크 전송</li>
              <li>양측이 각자의 방에서 주장 입력</li>
              <li>양측 모두 제출하면 AI 판결 시작</li>
              <li>잘못 비율 + 판결문 + 화해미션 공개</li>
            </ol>
          </div>

          <button
            onClick={handleCreate}
            disabled={!title.trim() || loading}
            className="w-full bg-ink hover:bg-ink-light text-gold font-serif font-bold py-3.5 rounded-xl transition-colors disabled:opacity-40 text-lg tracking-wider"
          >
            {loading ? "재판 개정 중..." : "⚖️ 재판 열기"}
          </button>
        </div>
      </div>
    </Layout>
  );
}
