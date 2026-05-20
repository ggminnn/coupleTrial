import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import Layout from "../components/Layout";
import api from "../lib/api";
import { Scale, Clock, CheckCircle, Plus, Copy, Check } from "lucide-react";

const STATUS_MAP = {
  waiting: { label: "피고 대기중", color: "text-gold border-gold", icon: Clock },
  in_progress: { label: "진행중", color: "text-blue-600 border-blue-400", icon: Scale },
  judged: { label: "판결완료", color: "text-verdict-win border-verdict-win", icon: CheckCircle },
};

function CaseCard({ c, userId }) {
  const [copied, setCopied] = useState(false);
  const status = STATUS_MAP[c.status];
  const StatusIcon = status.icon;
  const isPlaintiff = c.plaintiff_id === userId;

  const copyInviteLink = () => {
    const link = `${window.location.origin}/join/${c.invite_token}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white border border-gold/20 rounded-xl p-5 hover:border-gold/50 hover:shadow-md transition-all animate-slide-up">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`stamp ${status.color} text-xs`}>
              <StatusIcon className="w-3 h-3 mr-1 inline" />
              {status.label}
            </span>
            <span className="text-xs text-ink/40 font-sans">
              {isPlaintiff ? "원고" : "피고"}
            </span>
          </div>
          <h3 className="font-serif text-lg text-ink truncate">{c.title}</h3>
          <p className="text-xs text-ink/40 font-sans mt-1">
            {new Date(c.created_at).toLocaleDateString("ko-KR")}
          </p>
        </div>

        <div className="flex flex-col gap-2 flex-shrink-0">
          {/* 피고 초대 링크 복사 (원고이고 피고 미입장) */}
          {isPlaintiff && !c.defendant_id && (
            <button
              onClick={copyInviteLink}
              className="flex items-center gap-1 text-xs bg-cream border border-gold/30 hover:border-gold px-3 py-1.5 rounded-lg transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-verdict-win" /> : <Copy className="w-3 h-3" />}
              {copied ? "복사됨!" : "초대링크"}
            </button>
          )}

          {/* 판결 진행 중 (양측 모두 제출했지만 아직 AI 처리 중) */}
          {c.status === "in_progress" && c.plaintiff_submitted && c.defendant_submitted && (
            <span className="text-xs text-gold border border-gold/40 bg-gold/10 px-3 py-1.5 rounded-lg text-center animate-pulse">
              판결 진행 중...
            </span>
          )}

          {/* 주장하기 버튼 (아직 제출 안 한 경우) */}
          {(c.status === "waiting" || (c.status === "in_progress" && !(c.plaintiff_submitted && c.defendant_submitted))) && (
            <Link
              to={`/cases/${c.id}/chat`}
              className="text-xs bg-ink text-gold font-bold px-3 py-1.5 rounded-lg hover:bg-ink-light transition-colors text-center"
            >
              주장하기 →
            </Link>
          )}

          {/* 판결 보기 버튼 */}
          {c.status === "judged" && (
            <Link
              to={`/cases/${c.id}/verdict`}
              className="text-xs bg-gold text-ink font-bold px-3 py-1.5 rounded-lg hover:bg-gold-light transition-colors text-center"
            >
              판결 보기 ⚖️
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CasesPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const res = await api.get("/cases");
        setCases(res.data);
        setLoading(false);
      } catch {
        setLoading(false);
      }
    };

    fetchCases();
    const interval = setInterval(fetchCases, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Layout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-serif text-3xl text-ink">내 재판 목록</h1>
          <p className="text-ink/50 text-sm mt-1 font-sans">총 {cases.length}건의 사건</p>
        </div>
        <Link
          to="/cases/new"
          className="flex items-center gap-2 bg-ink text-gold font-serif font-bold px-5 py-2.5 rounded-xl hover:bg-ink-light transition-colors"
        >
          <Plus className="w-4 h-4" />
          새 재판 열기
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-20 text-ink/30 font-sans">불러오는 중...</div>
      ) : cases.length === 0 ? (
        <div className="text-center py-20">
          <Scale className="w-16 h-16 text-gold/30 mx-auto mb-4" />
          <p className="font-serif text-xl text-ink/40">아직 사건이 없습니다</p>
          <p className="text-ink/30 text-sm mt-2 font-sans">첫 번째 재판을 열어보세요</p>
          <Link
            to="/cases/new"
            className="inline-flex items-center gap-2 mt-6 bg-ink text-gold font-serif px-6 py-3 rounded-xl hover:bg-ink-light transition-colors"
          >
            <Plus className="w-4 h-4" /> 재판 열기
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => (
            <CaseCard key={c.id} c={c} userId={user?.id} />
          ))}
        </div>
      )}
    </Layout>
  );
}
