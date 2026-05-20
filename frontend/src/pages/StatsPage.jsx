import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../lib/api";
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  BarChart, Bar,
} from "recharts";
import { Scale, TrendingUp, BarChart2 } from "lucide-react";

const PIE_COLORS = ["#EF4444", "#22C55E"];

const CustomTooltipLine = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gold/20 rounded-xl px-3 py-2 text-xs font-sans shadow-sm">
      <p className="text-ink/50 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value}%
        </p>
      ))}
    </div>
  );
};

const CustomTooltipBar = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gold/20 rounded-xl px-3 py-2 text-xs font-sans shadow-sm">
      <p className="text-ink font-bold">{label}</p>
      <p className="text-gold">{payload[0].value}회</p>
    </div>
  );
};

export default function StatsPage() {
  const { caseId } = useParams();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get(`/stats/${caseId}`)
      .then((res) => {
        setStats(res.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "통계를 불러오지 못했습니다");
        setLoading(false);
      });
  }, [caseId]);

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-20">
          <Scale className="w-12 h-12 text-gold mx-auto mb-4 animate-gavel" />
          <p className="font-serif text-xl text-ink">통계 분석 중...</p>
          <p className="text-ink/40 text-sm font-sans mt-2">잠시만 기다려주세요</p>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="text-center py-20">
          <p className="font-serif text-xl text-ink/60">{error}</p>
          <Link
            to={`/cases/${caseId}/verdict`}
            className="mt-6 inline-block text-gold hover:underline text-sm font-sans"
          >
            ← 판결문으로 돌아가기
          </Link>
        </div>
      </Layout>
    );
  }

  const {
    totalCases,
    plaintiffNickname,
    defendantNickname,
    avgPlaintiffRatio,
    avgDefendantRatio,
    trend,
    fightTypes,
  } = stats;

  const pieData = [
    { name: `${plaintiffNickname} (원고)`, value: avgPlaintiffRatio },
    { name: `${defendantNickname} (피고)`, value: avgDefendantRatio },
  ];

  return (
    <Layout>
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in pb-10">

        {/* 헤더 */}
        <div className="text-center py-6 animate-slide-up">
          <h1 className="font-serif text-3xl text-ink mb-1">우리의 재판 통계</h1>
          <p className="text-ink/50 font-sans text-sm">
            {plaintiffNickname} vs {defendantNickname} · 총{" "}
            <span className="text-gold font-bold">{totalCases}</span>회 재판
          </p>
        </div>

        {/* 파이차트: 평균 잘못 비율 */}
        <div className="bg-white border border-gold/20 rounded-2xl p-6">
          <h2 className="font-serif text-lg text-ink mb-4 flex items-center gap-2">
            <Scale className="w-5 h-5 text-gold" /> 평균 잘못 비율
          </h2>
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1 bg-cream rounded-xl p-3 text-center">
              <p className="text-xs text-ink/40 font-sans mb-1">{plaintiffNickname} (원고)</p>
              <p className="font-serif text-2xl text-verdict-lose">{avgPlaintiffRatio}%</p>
            </div>
            <div className="text-ink/30 font-serif text-xl">vs</div>
            <div className="flex-1 bg-cream rounded-xl p-3 text-center">
              <p className="text-xs text-ink/40 font-sans mb-1">{defendantNickname} (피고)</p>
              <p className="font-serif text-2xl text-verdict-win">{avgDefendantRatio}%</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={4}
                dataKey="value"
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `${v}%`} />
              <Legend iconType="circle" iconSize={10} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 라인차트: 재판별 비율 추이 */}
        {trend.length >= 2 ? (
          <div className="bg-white border border-gold/20 rounded-2xl p-6">
            <h2 className="font-serif text-lg text-ink mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-gold" /> 잘못 비율 추이
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0E6C0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "#9b8a6a" }}
                  tickFormatter={(d) => d.slice(5)}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: "#9b8a6a" }}
                  unit="%"
                />
                <Tooltip content={<CustomTooltipLine />} />
                <Legend iconType="circle" iconSize={10} />
                <Line
                  type="monotone"
                  dataKey="plaintiffRatio"
                  name={`${plaintiffNickname}`}
                  stroke={PIE_COLORS[0]}
                  strokeWidth={2}
                  dot={{ r: 4, fill: PIE_COLORS[0] }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="defendantRatio"
                  name={`${defendantNickname}`}
                  stroke={PIE_COLORS[1]}
                  strokeWidth={2}
                  dot={{ r: 4, fill: PIE_COLORS[1] }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="bg-white border border-gold/20 rounded-2xl p-6 text-center">
            <TrendingUp className="w-8 h-8 text-gold/30 mx-auto mb-2" />
            <p className="text-ink/40 font-sans text-sm">
              추이 차트는 2회 이상 재판 후 표시됩니다
            </p>
          </div>
        )}

        {/* 바차트: 싸움 유형별 빈도 */}
        {fightTypes.length > 0 && (
          <div className="bg-white border border-gold/20 rounded-2xl p-6">
            <h2 className="font-serif text-lg text-ink mb-4 flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-gold" /> 싸움 유형
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={fightTypes}
                margin={{ top: 5, right: 10, left: -10, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#F0E6C0" />
                <XAxis dataKey="type" tick={{ fontSize: 10, fill: "#9b8a6a" }} />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 10, fill: "#9b8a6a" }}
                />
                <Tooltip content={<CustomTooltipBar />} />
                <Bar
                  dataKey="count"
                  name="재판 횟수"
                  fill="#B8960C"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
            {/* 범례 카드 */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              {fightTypes.map((ft) => (
                <div
                  key={ft.type}
                  className="flex items-center justify-between bg-cream rounded-xl px-3 py-2"
                >
                  <span className="text-xs text-ink font-sans">{ft.type}</span>
                  <span className="text-xs font-bold text-gold">{ft.count}회</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <Link
          to={`/cases/${caseId}/verdict`}
          className="block text-center text-gold font-sans text-sm hover:underline py-4"
        >
          ← 판결문으로 돌아가기
        </Link>
      </div>
    </Layout>
  );
}
