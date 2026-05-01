import React, { useState, useEffect, useRef, useCallback } from "react";

// --- CONFIGURATION ---
// Replace with your live Render backend URL
const API_URL = "https://backend-carbonemission2.onrender.com/api/data";

// Time between data updates (in milliseconds)
const POLL_INTERVAL = 5000;

// Maximum number of data points to keep in the history chart
const MAX_HISTORY = 30;

// --- STYLING METADATA ---
const STATUS_STYLES = {
  SAFE: {
    bg: "#EAF3DE",
    color: "#3B6D11",
    label: "SAFE",
    sub: "Below 300 threshold",
  },
  WARNING: {
    bg: "#FAEEDA",
    color: "#854F0B",
    label: "WARNING",
    sub: "Approaching limit",
  },
  UNSAFE: {
    bg: "#FCEBEB",
    color: "#A32D2D",
    label: "UNSAFE",
    sub: "Exceeds 300 threshold",
  },
};

const SUGGESTION_META = {
  "Redistribute workload": {
    icon: "💻", // Add icons
    bg: "#E6F1FB",
    detail:
      "CPU above 80% - balance load across nodes to reduce per-core strain.",
  },
  "Improve cooling": {
    icon: "❄️",
    bg: "#E1F5EE",
    detail:
      "Temperature above 35°C - check fans and airflow to prevent thermal throttling.",
  },
  "Shift to low-carbon hours": {
    icon: "☀️",
    bg: "#FAEEDA",
    detail:
      "Emission above 300 - schedule heavy jobs during off-peak or renewable hours.",
  },
};

// --- Sparkline Component ---
function Sparkline({ data }) {
  const W = 300, H = 120, PAD = 8;
  if (data.length < 2)
    return (
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "100%" }}
      />
    );

  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const xs = data.map((_, i) => PAD + (i / (data.length - 1)) * (W - PAD * 2));
  const ys = data.map((v) => PAD + (1 - (v - min) / range) * (H - PAD * 2));
  let d = `M${xs[0]},${ys[0]}`;

  for (let i = 1; i < xs.length; i++) {
    const cx = (xs[i - 1] + xs[i]) / 2;
    d += `C${cx},${ys[i - 1]} ${cx},${ys[i]} ${xs[i]},${ys[i]}`;
  }

  const area = d + ` L${xs[xs.length - 1]},${H} L${xs[0]},${H} Z`;
  const lx = xs[xs.length - 1], ly = ys[ys.length - 1];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ width: "100%", height: "100%" }}
    >
      <defs>
        <linearGradient id="fadeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#BA7517" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#BA7517" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#fadeGrad)" />
      <path d={d} fill="none" stroke="#BA7517" strokeWidth="2" />
      <circle cx={lx} cy={ly} r="4" fill="#BA7517" />
    </svg>
  );
}

// --- Bar Component ---
function Bar({ label, pct, valText, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
      <span style={{ fontSize: 13, color: "#888", width: 90, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 8, background: "#f0f0ec", borderRadius: 99, overflow: "hidden" }}>
        <div style={{
          height: "100%", borderRadius: 99, background: color,
          width: `${Math.min(100, pct)}%`, transition: "width 0.8s cubic-bezier(.4,0,.2,1)"
        }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 500, width: 46, textAlign: "right", flexShrink: 0 }}>
        {valText}
      </span>
    </div>
  );
}
// --- MetricCard Component ---
function MetricCard({ label, value, sub, subEl }) {
  return (
    <div style={{ background: "#f7f6f2", borderRadius: 8, padding: "1rem" }}>
      <div style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 500, color: "#1a1a18" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>{subEl || sub}</div>
    </div>
  );
}

// --- Main App Component ---
export default function App() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [prevEmission, setPrevEmission] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  // We use a ref to track the previous emission without causing infinite loops
  const prevEmissionRef = useRef(null); 

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      
      // Calculate emission change safely
      setPrevEmission(prevEmissionRef.current);
      prevEmissionRef.current = json.emission;
      
      setData(json);
      setError(null);
      setLastUpdated(new Date());
      setHistory(prev => {
        const next = [...prev, json.emission];
        return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
      });

    } catch (e) {
      console.error(e);
      setError("Unable to reach backend. Retrying...");
      setData(null); 
    }
  }, []); // <-- Empty array here fixes the loop!

  useEffect(() => {
    fetchData();
    const intervalId = setInterval(fetchData, POLL_INTERVAL);
    return () => clearInterval(intervalId);
  }, [fetchData]);

  // Derive values, handling nulls
  const emission = data ? Math.round(data.emission * 10) / 10 : null;
  const cpu = data?.sensor?.cpu ?? null;
  const power = data?.sensor?.power ?? null;
  const temp = data?.sensor?.temperature ?? null;
  const dbConnected = data?.db_connected ?? false;

  // Determine status
  const statusKey = !data ? null : data.emission < 250 ? "SAFE" : data.emission < 300 ? "WARNING" : "UNSAFE";
  const statusStyle = statusKey ? STATUS_STYLES[statusKey] : null;

  // Calculate emission difference
  const diff = prevEmission !== null && emission !== null ? +(emission - prevEmission).toFixed(1) : null;
  const suggestions = data?.suggestions ?? [];

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: "1.5rem", paddingBottom: "1rem", borderBottom: "0.5px solid #e0dfd7"
      }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, margin: 0 }}>Carbon Monitor</h1>
          <p style={{ fontSize: 13, color: "#888", marginTop: 3 }}>
            <span style={{
              display: "inline-block", width: 8, height: 8, borderRadius: "50%",
              background: error ? "#E24B4A" : "#639922", marginRight: 6
            }} />
            {error ? "Disconnected" : dbConnected ? "Cloud Connected" : "Static Preview Mode (DB Offline)"}
            {lastUpdated &&
              <span style={{ marginLeft: 8, color: "#aaa" }}>
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            }
          </p>
        </div>
        <button onClick={fetchData}
          style={{
            background: "#f7f6f2", border: "0.5px solid #ccc", borderRadius: 8,
            padding: "6px 14px", fontSize: 13, cursor: "pointer"
          }}>
          Refresh
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div style={{
          background: "#FCEBEB", color: "#A32D2D", border: "0.5px solid #F09595",
          borderRadius: 8, padding: "10px 14px", fontSize: 13, marginBottom: "1.5rem"
        }}>
          {error}
        </div>
      )}

      {/* Metric cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: 12, marginBottom: "1.5rem" }}>
        <MetricCard label="Emission" value={emission ?? "-"} sub={
          diff === null ? "-" :
            diff > 0 ? `▲ ${Math.abs(diff)} vs last` :
              diff < 0 ? `▼ ${Math.abs(diff)} vs last` : "- no change"
        } />
        <MetricCard label="Status" value="" subEl={statusStyle ? (
          <>
            <span style={{
              background: statusStyle.bg, color: statusStyle.color,
              padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 500
            }}>
              {statusStyle.label}
            </span>
            <span style={{ display: "block", marginTop: 4 }}>{statusStyle.sub}</span>
          </>
        ) : "-"} />
        <MetricCard label="CPU Usage" value={cpu !== null ? `${cpu}%` : "-"} sub="percent" />
        <MetricCard label="Temperature" value={temp !== null ? `${temp}°` : "-"} sub="celsius" />
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 12, marginBottom: "1.5rem" }}>
        {/* Sensor bars */}
        <div style={{ background: "#fff", border: "0.5px solid #e0dfd7", borderRadius: 12, padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 14 }}>
            Sensor readings
          </div>
          <Bar label="CPU" pct={cpu} valText={cpu !== null ? `${cpu}%` : "-"} color="#378ADD" />
          <Bar label="Power (W)" pct={(power / 500) * 100} valText={power !== null ? `${power}W` : "-"} color="#1D9E75" />
          <Bar label="Temperature" pct={((temp - 20) / 25) * 100} valText={temp !== null ? `${temp}°` : "-"} color="#D85A30" />
          <Bar label="Emission" pct={(emission / 500) * 100} valText={emission ?? "-"} color="#BA7517" />
        </div>

        {/* Sparkline */}
        <div style={{ background: "#fff", border: "0.5px solid #e0dfd7", borderRadius: 12, padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
            Emission trend
          </div>
          <div style={{ height: 140, marginTop: 8 }}>
            <Sparkline data={history} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#aaa", marginTop: 4 }}>
            <span>older</span><span>now</span>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div style={{ background: "#fff", border: "0.5px solid #e0dfd7", borderRadius: 12, padding: "1rem 1.25rem" }}>
        <div style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
          Recommendations
        </div>
        {!data && !error ? (
          <p style={{ fontSize: 13, color: "#aaa" }}>Fetching recommendations...</p>
        ) : suggestions.length === 0 ? (
          <p style={{ fontSize: 13, color: "#888" }}>All systems nominal, no action required.</p>
        ) : suggestions.map((s, i) => {
          const meta = SUGGESTION_META[s] || { icon: "📝", bg: "#f7f6f2", detail: s };
          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 0", borderBottom: i < suggestions.length - 1 ? "0.5px solid #e0dfd7" : "none" }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: meta.bg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>
                {meta.icon}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{s}</div>
                <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>{meta.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}