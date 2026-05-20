import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../contexts/AuthContext";
import api from "../lib/api";
import { Scale, Trophy, Target, Heart } from "lucide-react";

const TOTAL_STEPS = 6;

function RatioBar({ plaintiff, defendant }) {
  return (
    <div className="my-6">
      <div className="flex justify-between text-sm font-sans mb-2">
        <span className="text-ink/60">원고 잘못</span>
        <span className="text-ink/60">피고 잘못</span>
      </div>
      <div className="flex h-8 rounded-full overflow-hidden border border-gold/20">
        <div
          className="bg-verdict-lose flex items-center justify-center text-white text-sm font-bold transition-all duration-1000"
          style={{ width: `${plaintiff}%` }}
        >
          {plaintiff}%
        </div>
        <div
          className="bg-verdict-win flex items-center justify-center text-white text-sm font-bold transition-all duration-1000"
          style={{ width: `${defendant}%` }}
        >
          {defendant}%
        </div>
      </div>
      <div className="flex justify-between text-xs text-ink/40 font-sans mt-1">
        <span>원고</span>
        <span>피고</span>
      </div>
    </div>
  );
}

function ProgressScreen({ step, message }) {
  const pct = step > 0 ? Math.round((step / TOTAL_STEPS) * 100) : 4;

  return (
    <Layout>
      <div className="max-w-lg mx-auto text-center py-20 animate-slide-up">
        <Scale className="w-16 h-16 text-gold mx-auto mb-6 animate-gavel" />
        <h2 className="font-serif text-2xl text-ink mb-2">AI 판사 심의 중</h2>
        <p className="text-gold font-sans font-semibold text-base mb-8 min-h-[1.5rem]">
          {message}
        </p>

        {/* 프로그레스 바 */}
        <div className="bg-cream rounded-full h-3 overflow-hidden mb-4 mx-4">
          <div
            className="bg-gold h-full rounded-full transition-all duration-700 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* 단계 도트 */}
        <div className="flex justify-center gap-2 mb-6">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-colors duration-500 ${
                i < step ? "bg-gold" : "bg-gold/20"
              }`}
            />
          ))}
        </div>

        <p className="text-xs text-ink/30 font-sans">
          {step > 0 ? `${step} / ${TOTAL_STEPS} 단계 완료` : "시작 중..."}
        </p>
      </div>
    </Layout>
  );
}

export default function VerdictPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [verdict, setVerdict] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [caseData, setCaseData] = useState(null);
  const [progressStep, setProgressStep] = useState(0);
  const [progressMsg, setProgressMsg] = useState("판결 준비 중...");

  useEffect(() => {
    let cancelled = false;
    let ws = null;

    const loadVerdict = async () => {
      try {
        const [caseRes, verdictRes] = await Promise.all([
          api.get(`/cases/${id}`),
          api.get(`/verdicts/${id}`),
        ]);
        if (cancelled) return true;
        setCaseData(caseRes.data);
        setVerdict(verdictRes.data);
        api
          .get(`/verdicts/${id}/similar`)
          .then((res) => { if (!cancelled) setSimilar(res.data.similar_cases || []); })
          .catch(() => {});
        return true;
      } catch {
        return false;
      }
    };

    const connectWs = () => {
      const token = localStorage.getItem("token");
      const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const wsBase = apiBase.replace(/^http/, "ws");
      ws = new WebSocket(`${wsBase}/ws/trial/${id}?token=${token}`);

      ws.onmessage = (e) => {
        if (cancelled) return;
        const data = JSON.parse(e.data);
        if (data.type === "progress") {
          setProgressStep(data.step);
          setProgressMsg(data.message);
        } else if (data.type === "done") {
          setProgressStep(TOTAL_STEPS);
          setProgressMsg("✅ 판결 완료!");
          setTimeout(() => loadVerdict(), 600);
        }
      };

      ws.onerror = () => {
        // WebSocket 실패 시 폴링으로 폴백
        if (cancelled) return;
        const poll = () => {
          loadVerdict().then((loaded) => {
            if (!loaded && !cancelled) setTimeout(poll, 2000);
          });
        };
        setTimeout(poll, 2000);
      };
    };

    // 이미 판결 완료된 경우 즉시 로드, 아니면 WebSocket 연결
    loadVerdict().then((loaded) => {
      if (!loaded && !cancelled) connectWs();
    });

    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [id]);

  // 판결 로드 전: 진행 상태 화면
  if (!verdict) {
    return <ProgressScreen step={progressStep} message={progressMsg} />;
  }

  // 판결 완료 화면
  const isPlaintiff = caseData?.plaintiff_id === user?.id;
  const myRatio = isPlaintiff ? verdict.plaintiff_ratio : verdict.defendant_ratio;
  const isWinner = myRatio < 50;
  const isDraw = verdict.plaintiff_ratio === verdict.defendant_ratio;

  return (
    <Layout>
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">

        {/* 결과 헤더 */}
        <div className="text-center py-8 animate-slide-up">
          <div className={`inline-flex items-center gap-2 stamp mb-4 text-base px-5 py-2 ${
            isDraw ? "text-verdict-draw border-verdict-draw" :
            isWinner ? "text-verdict-win border-verdict-win" : "text-verdict-lose border-verdict-lose"
          }`}>
            <Trophy className="w-5 h-5" />
            {isDraw ? "무승부" : isWinner ? "승소" : "패소"}
          </div>
          <h1 className="font-serif text-3xl text-ink">{caseData?.title}</h1>
          <p className="text-ink/40 font-sans text-sm mt-2">
            사건번호: {id.slice(0, 8).toUpperCase()}
          </p>
        </div>

        {/* 잘못 비율 */}
        <div className="bg-white border border-gold/20 rounded-2xl p-6">
          <h2 className="font-serif text-lg text-ink mb-1 flex items-center gap-2">
            <Target className="w-5 h-5 text-gold" /> 잘못 비율
          </h2>
          <RatioBar
            plaintiff={verdict.plaintiff_ratio}
            defendant={verdict.defendant_ratio}
          />
        </div>

        {/* 판결문 */}
        <div className="bg-white border border-gold/20 rounded-2xl p-6">
          <h2 className="font-serif text-lg text-ink mb-4 flex items-center gap-2">
            <Scale className="w-5 h-5 text-gold" /> 판결문
          </h2>
          <div className="verdict-card">
            <p className="font-serif text-ink/80 leading-relaxed text-sm whitespace-pre-wrap">
              {verdict.judgment}
            </p>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="bg-cream rounded-xl p-3">
              <p className="text-xs text-ink/40 font-sans mb-1">원고 주장 요약</p>
              <p className="text-sm text-ink font-sans">{verdict.plaintiff_summary}</p>
            </div>
            <div className="bg-cream rounded-xl p-3">
              <p className="text-xs text-ink/40 font-sans mb-1">피고 주장 요약</p>
              <p className="text-sm text-ink font-sans">{verdict.defendant_summary}</p>
            </div>
          </div>
        </div>

        {/* 화해 미션 */}
        <div className="bg-white border border-gold/20 rounded-2xl p-6">
          <h2 className="font-serif text-lg text-ink mb-4 flex items-center gap-2">
            <Heart className="w-5 h-5 text-gold" /> 화해 미션
          </h2>
          <div className="space-y-3">
            {verdict.missions.map((mission, i) => (
              <div key={i} className="flex items-start gap-3 bg-cream rounded-xl p-4">
                <span className="w-6 h-6 rounded-full bg-gold/20 text-gold font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <p className="text-sm text-ink font-sans">{mission}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 유사 판례 */}
        {similar.length > 0 && (
          <div className="bg-white border border-gold/20 rounded-2xl p-6">
            <h2 className="font-serif text-lg text-ink mb-4">📚 유사 판례</h2>
            <div className="space-y-2">
              {similar.map((s, i) => (
                <div key={i} className="flex items-center justify-between bg-cream rounded-xl px-4 py-3">
                  <div>
                    <p className="text-sm text-ink font-sans">{s.title}</p>
                    <p className="text-xs text-ink/40 font-sans">유사도 {s.similarity}%</p>
                  </div>
                  <div className="text-right text-xs font-sans">
                    <span className="text-verdict-lose">원고 {s.plaintiff_ratio}%</span>
                    <span className="text-ink/30 mx-1">/</span>
                    <span className="text-verdict-win">피고 {s.defendant_ratio}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <Link
          to={`/stats/${id}`}
          className="block w-full text-center bg-ink hover:bg-ink-light text-gold font-serif font-bold py-3.5 rounded-xl transition-colors text-base tracking-wide"
        >
          📊 우리 통계 보기
        </Link>

        <Link
          to="/cases"
          className="block text-center text-gold font-sans text-sm hover:underline py-2"
        >
          ← 목록으로 돌아가기
        </Link>
      </div>
    </Layout>
  );
}
