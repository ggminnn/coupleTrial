import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import Layout from "../components/Layout";
import api from "../lib/api";
import { Send, AlertTriangle, CheckCircle, Scale, Copy, Check } from "lucide-react";

export default function ChatPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [copied, setCopied] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [caseData, setCaseData] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sending, setSending] = useState(false);
  const [blocked, setBlocked] = useState(null);
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    let cancelled = false;

    const load = async () => {
      try {
        const [caseRes, msgsRes] = await Promise.all([
          api.get(`/cases/${id}`, { signal }),
          api.get(`/chat/${id}/messages`, { signal }),
        ]);
        if (!cancelled) {
          setCaseData(caseRes.data);
          setMessages(msgsRes.data);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isWaiting = caseData?.status === "waiting";
  const isPlaintiff = caseData?.plaintiff_id === user?.id;
  const inviteLink = caseData ? `${window.location.origin}/join/${caseData.invite_token}` : "";

  const copyInviteLink = () => {
    navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sendMessage = async () => {
    const content = input.trim();
    if (!content || sending || loading) return;

    setInput("");
    setSending(true);
    setBlocked(null);
    setMessages((prev) => [...prev, { id: `t${Date.now()}`, content }]);

    try {
      await api.post(`/chat/${id}/messages`, { content });
      const res = await api.get(`/chat/${id}/messages`);
      setMessages(res.data);
    } catch (e) {
      setInput(content);
      setMessages((prev) => prev.filter((m) => !String(m.id).startsWith("t")));
      const detail = e.response?.data?.detail;
      if (detail) setBlocked({ reason: detail });
    } finally {
      setSending(false);
    }
  };

  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    if (!submitted) return;
    const interval = setInterval(async () => {
      try {
        await api.get(`/verdicts/${id}`);
        navigate(`/cases/${id}/verdict`);
      } catch {
        // 아직 판결 안 남
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [submitted, id, navigate]);

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const res = await api.post(`/cases/${id}/submit`);
      setSubmitted(true);
      if (res.data.judging) {
        navigate(`/cases/${id}/verdict`);
      }
    } catch (e) {
      setSubmitError(e.response?.data?.detail || "제출 중 오류가 발생했습니다");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-6">
          <h1 className="font-serif text-2xl text-ink">{caseData?.title || "로딩 중..."}</h1>
          <p className="text-ink/40 text-sm font-sans mt-1">
            이 방은 나만 볼 수 있습니다. 자유롭게 주장하세요.
          </p>
        </div>

        {isWaiting && isPlaintiff && (
          <div className="mb-4 px-4 py-3 bg-gold/10 border border-gold/30 rounded-xl">
            <p className="text-sm font-sans text-ink/70 mb-2 text-center">⏳ 상대방이 아직 입장하지 않았습니다. 미리 주장을 작성해두세요.</p>
            <button
              onClick={copyInviteLink}
              className="flex items-center gap-2 mx-auto text-xs bg-ink text-gold font-bold px-4 py-2 rounded-lg hover:bg-ink-light transition-colors"
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? "복사됨!" : "초대 링크 복사"}
            </button>
          </div>
        )}

        <div className="bg-white border border-gold/20 rounded-2xl overflow-hidden shadow-sm">
          <div className="h-96 overflow-y-auto p-4 space-y-3 bg-cream/50">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-ink/30">
                <Scale className="w-12 h-12 mb-3 text-gold/30" />
                <p className="font-sans text-sm">주장을 입력해주세요</p>
                <p className="font-sans text-xs mt-1">상대방은 볼 수 없어요</p>
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id} className="flex justify-end animate-slide-up">
                <div className={`max-w-xs rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm font-sans ${
                  msg.id?.startsWith("temp-") ? "bg-ink/60 text-cream" : "bg-ink text-cream"
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {blocked && (
            <div className="px-4 py-2 bg-verdict-lose/10 border-t border-verdict-lose/20 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-verdict-lose flex-shrink-0 mt-0.5" />
              <div className="text-xs font-sans">
                <p className="text-verdict-lose font-bold">메시지가 차단되었습니다</p>
                <p className="text-ink/60">{blocked.reason}</p>
                {blocked.suggestion && (
                  <p className="text-ink/50 mt-1">💡 대신: {blocked.suggestion}</p>
                )}
              </div>
            </div>
          )}

          {!submitted ? (
            <div className="p-3 border-t border-gold/20 flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                disabled={submitted || sending || loading}
                className="flex-1 bg-cream border border-gold/30 rounded-xl px-4 py-2.5 text-sm font-sans focus:outline-none focus:border-gold transition-colors disabled:opacity-50"
                placeholder={loading ? "로딩 중..." : "내 입장에서 주장하세요..."}
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || sending || loading}
                className="bg-ink text-gold p-2.5 rounded-xl hover:bg-ink-light transition-colors disabled:opacity-40"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="p-4 border-t border-gold/20 flex items-center justify-center gap-2 text-verdict-win">
              <CheckCircle className="w-5 h-5" />
              <span className="font-sans text-sm font-bold">제출 완료! 상대방을 기다리는 중...</span>
            </div>
          )}
        </div>

        {!submitted && messages.length > 0 && (
          isWaiting ? (
            <div className="w-full mt-4 py-4 text-center text-ink/50 font-sans text-sm border border-gold/20 rounded-xl">
              ⏳ 상대방이 입장해야 제출할 수 있습니다
            </div>
          ) : (
            <>
              {submitError && (
                <p className="text-center text-verdict-lose text-sm mt-3 font-sans">{submitError}</p>
              )}
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="w-full mt-4 bg-gold hover:bg-gold-light text-ink font-serif font-bold py-4 rounded-xl transition-colors text-lg disabled:opacity-50"
              >
                {submitting ? "제출 중..." : "⚖️ 주장 제출 완료"}
              </button>
            </>
          )
        )}

        <p className="text-center text-xs text-ink/30 font-sans mt-3">
          제출 후에는 수정할 수 없습니다. 양측 모두 제출하면 판결이 시작됩니다.
        </p>
      </div>
    </Layout>
  );
}
