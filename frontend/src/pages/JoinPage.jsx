import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api from "../lib/api";
import { Scale } from "lucide-react";

export default function JoinPage() {
  const { token } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("joining"); // joining | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!user) {
      // 로그인 안 됐으면 로그인 후 다시 이 링크로
      navigate(`/login?redirect=/join/${token}`);
      return;
    }

    api.post(`/cases/join/${token}`)
      .then((res) => {
        setStatus("success");
        setTimeout(() => navigate(`/cases/${res.data.id}/chat`), 1500);
      })
      .catch((e) => {
        setStatus("error");
        setMessage(e.response?.data?.detail || "유효하지 않은 링크입니다");
      });
  }, [token, user]);

  return (
    <div className="min-h-screen bg-ink flex items-center justify-center px-4">
      <div className="text-center animate-fade-in">
        <Scale className={`w-16 h-16 text-gold mx-auto mb-6 ${status === "joining" ? "animate-gavel" : ""}`} />

        {status === "joining" && (
          <>
            <p className="font-serif text-2xl text-gold mb-2">재판에 입정 중...</p>
            <p className="text-cream/40 font-sans text-sm">잠시만 기다려주세요</p>
          </>
        )}

        {status === "success" && (
          <>
            <p className="font-serif text-2xl text-gold mb-2">입정 완료!</p>
            <p className="text-cream/40 font-sans text-sm">채팅방으로 이동합니다</p>
          </>
        )}

        {status === "error" && (
          <>
            <p className="font-serif text-2xl text-verdict-lose mb-2">입장 실패</p>
            <p className="text-cream/40 font-sans text-sm mb-6">{message}</p>
            <button
              onClick={() => navigate("/cases")}
              className="text-gold font-sans text-sm hover:underline"
            >
              ← 목록으로
            </button>
          </>
        )}
      </div>
    </div>
  );
}
