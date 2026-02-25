import { useState, useEffect, useRef } from "react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";

const API = "/api/competitive";

const TIER_COLORS = {
  A: "bg-emerald-900 text-emerald-200 border border-emerald-700",
  B: "bg-amber-900 text-amber-200 border border-amber-700",
  C: "bg-slate-700 text-slate-300 border border-slate-600",
};

const TIER_LABELS = {
  A: "Priority A",
  B: "Watch B",
  C: "Pipeline C",
};

function ScoreBar({ value, max = 100, color = "bg-blue-500" }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-6 text-right">{Math.round(value)}</span>
    </div>
  );
}

function StatCard({ label, value, sub, accent = false }) {
  return (
    <div className={`rounded-lg p-4 border ${accent ? "border-amber-700 bg-amber-950/40" : "border-slate-700 bg-slate-800/60"}`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? "text-amber-300" : "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function CompanyRow({ company, onSelect }) {
  const tier = company.priority_tier || "C";
  return (
    <tr
      onClick={() => onSelect(company)}
      className="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors"
    >
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded font-semibold ${TIER_COLORS[tier]}`}>
            {tier}
          </span>
          <div>
            <p className="text-sm text-white font-medium">{company.name}</p>
            {company.description && (
              <p className="text-xs text-slate-400 truncate max-w-xs">{company.description}</p>
            )}
          </div>
        </div>
      </td>
      <td className="py-3 px-4">
        <p className="text-sm text-slate-300">{company.vc_fund}</p>
        <div className="flex gap-1 mt-1">
          {company.nato_lp_backed && (
            <span className="text-xs bg-blue-900/60 text-blue-300 border border-blue-700 px-1.5 py-0.5 rounded">
              NATO LP
            </span>
          )}
          {company.eif_lp_backed && (
            <span className="text-xs bg-indigo-900/60 text-indigo-300 border border-indigo-700 px-1.5 py-0.5 rounded">
              EIF LP
            </span>
          )}
        </div>
      </td>
      <td className="py-3 px-4 w-32">
        <ScoreBar value={company.deal_quality_score} color="bg-amber-500" />
        <p className="text-xs text-slate-500 mt-1">{company.deal_quality_score.toFixed(0)}/100</p>
      </td>
      <td className="py-3 px-4">
        <div className="flex flex-col gap-0.5">
          {company.is_dual_use && (
            <span className="text-xs text-emerald-400">✓ Dual-use</span>
          )}
          {company.has_gov_contract && (
            <span className="text-xs text-blue-400">✓ Gov contract</span>
          )}
          {company.has_export_cert && (
            <span className="text-xs text-purple-400">✓ Export cert</span>
          )}
          {company.fund_exit_pressure && (
            <span className="text-xs text-amber-400">⚡ Exit pressure</span>
          )}
        </div>
      </td>
      <td className="py-3 px-4">
        {company.years_held != null ? (
          <span className="text-sm text-slate-300">{company.years_held.toFixed(1)}y</span>
        ) : (
          <span className="text-sm text-slate-500">—</span>
        )}
      </td>
      <td className="py-3 px-4">
        {company.in_radar_universe ? (
          <span className="text-xs bg-emerald-900/60 text-emerald-300 border border-emerald-700 px-2 py-0.5 rounded">
            In Universe
          </span>
        ) : (
          <span className="text-xs text-slate-500">Not tracked</span>
        )}
      </td>
    </tr>
  );
}

function CompanyDetailPanel({ company, onClose }) {
  if (!company) return null;
  const tier = company.priority_tier || "C";

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] bg-slate-900 border-l border-slate-700 shadow-2xl z-50 overflow-y-auto">
      <div className="p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${TIER_COLORS[tier]}`}>
                {TIER_LABELS[tier]}
              </span>
              <span className="text-xs text-slate-400">{company.vc_fund}</span>
            </div>
            <h2 className="text-xl font-bold text-white">{company.name}</h2>
            {company.website && (
              <a href={company.website} target="_blank" rel="noopener noreferrer"
                 className="text-xs text-blue-400 hover:underline mt-0.5 block">
                {company.website}
              </a>
            )}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">×</button>
        </div>

        {/* Score breakdown */}
        <Card className="bg-slate-800 border-slate-700 p-4 mb-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Deal Quality Score</h3>
          <div className="flex items-center gap-3 mb-4">
            <div className="text-4xl font-bold text-amber-400">{company.deal_quality_score.toFixed(0)}</div>
            <div className="text-slate-400 text-sm">/100</div>
          </div>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Exit Readiness</span><span>{company.exit_readiness_score?.toFixed(0)}/100</span>
              </div>
              <ScoreBar value={company.exit_readiness_score || 0} color="bg-emerald-500" />
            </div>
          </div>
        </Card>

        {/* Key signals */}
        <Card className="bg-slate-800 border-slate-700 p-4 mb-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Signals</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {[
              ["NATO LP Backed", company.nato_lp_backed],
              ["EIF LP Backed", company.eif_lp_backed],
              ["Dual-Use Flagged", company.is_dual_use],
              ["Gov Contract", company.has_gov_contract],
              ["Export Cert", company.has_export_cert],
              ["Fund Exit Pressure", company.fund_exit_pressure],
              ["In RADAR Universe", company.in_radar_universe],
            ].map(([label, value]) => (
              <div key={label} className={`flex items-center gap-1.5 p-2 rounded ${value ? "bg-emerald-900/40 text-emerald-300" : "bg-slate-700/40 text-slate-500"}`}>
                <span>{value ? "✓" : "·"}</span>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Description */}
        {company.description && (
          <Card className="bg-slate-800 border-slate-700 p-4 mb-4">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Description</h3>
            <p className="text-sm text-slate-300 leading-relaxed">{company.description}</p>
          </Card>
        )}

        {/* Rationale */}
        {company.notes && (
          <Card className="bg-slate-800 border-slate-700 p-4">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Scoring Rationale</h3>
            <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-wrap">{company.notes}</p>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function VCIntelligence() {
  const [targets, setTargets] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [filters, setFilters] = useState({ tier: "", dualUseOnly: false, exitPressureOnly: false });
  const [triggering, setTriggering] = useState(null);
  const [csvImporting, setCsvImporting] = useState(false);
  const csvInputRef = useRef(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.tier) params.append("priority_tier", filters.tier);
      if (filters.dualUseOnly) params.append("dual_use_only", "true");
      if (filters.exitPressureOnly) params.append("exit_pressure_only", "true");
      params.append("limit", "100");

      const [targetsRes, statsRes] = await Promise.all([
        fetch(`${API}/vc-portfolio/targets?${params}`).then(r => r.json()),
        fetch(`${API}/vc-portfolio/stats`).then(r => r.json()),
      ]);

      setTargets(targetsRes.data || []);
      setStats(statsRes.data || null);
    } catch (e) {
      console.error("Failed to fetch VC intelligence data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [filters]);

  const triggerAction = async (action) => {
    setTriggering(action);
    try {
      await fetch(`${API}/vc-portfolio/${action}`, { method: "POST" });
      setTimeout(fetchData, 3000);
    } finally {
      setTriggering(null);
    }
  };

  const handleCsvImport = async (e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    setCsvImporting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/vc-portfolio/import-csv`, { method: "POST", body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Import failed");
      alert(`Imported: ${data.created_companies || 0} companies created, ${data.new_holdings || 0} new holdings.${data.errors?.length ? ` ${data.errors.length} row(s) had errors.` : ""}`);
      fetchData();
    } catch (err) {
      alert(err.message || "CSV import failed");
    } finally {
      setCsvImporting(false);
      e.target.value = "";
    }
  };

  return (
    <div className="p-6 space-y-6 relative">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">VC Portfolio Intelligence</h1>
          <p className="text-slate-400 text-sm mt-1">
            Dual-use defense tech — sourcing funnel from 16 tracked VC funds
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!!triggering}
            onClick={() => triggerAction("scrape")}
            className="text-xs"
          >
            {triggering === "scrape" ? "Scraping…" : "↓ Scrape Portfolios"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!!triggering}
            onClick={() => triggerAction("score")}
            className="text-xs"
          >
            {triggering === "score" ? "Scoring…" : "⟳ Re-score Signals"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!!triggering}
            onClick={() => triggerAction("run-moat-pipeline")}
            className="text-xs"
            title="Sync portfolio companies to universe, run extraction + moat scoring"
          >
            {triggering === "run-moat-pipeline" ? "Running…" : "⊕ Moat scoring"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!!triggering}
            onClick={() => triggerAction("enrich-existing")}
            className="text-xs"
            title="Run extraction + moat scoring on companies already linked to universe"
          >
            {triggering === "enrich-existing" ? "Enriching…" : "⟳ Enrich existing"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!!triggering}
            onClick={() => triggerAction("crosscheck-contracts")}
            className="text-xs"
            title="Cross-check portfolio companies against UK Contracts Finder award notices; set Gov contract where matched"
          >
            {triggering === "crosscheck-contracts" ? "Cross-checking…" : "📋 Cross-check Contracts"}
          </Button>
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleCsvImport}
          />
          <Button
            variant="outline"
            size="sm"
            disabled={!!triggering || csvImporting}
            onClick={() => csvInputRef.current?.click()}
            className="text-xs"
            title="Bulk import from CSV (name, vc_fund, website, first_funding_date, sector)"
          >
            {csvImporting ? "Importing…" : "↑ Import CSV"}
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="Total Companies" value={stats.total_portfolio_companies} />
          <StatCard label="Priority A" value={stats.priority_a} accent sub="Top targets" />
          <StatCard label="Priority B" value={stats.priority_b} sub="Watch list" />
          <StatCard label="Dual-Use Flagged" value={stats.dual_use_flagged} sub="Auto-detected" />
          <StatCard label="Exit Pressure" value={stats.exit_pressure} sub="LP window open" />
          <StatCard label="In Universe" value={stats.already_in_universe} sub="Already tracked" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1">
          {["", "A", "B", "C"].map(tier => (
            <button
              key={tier}
              onClick={() => setFilters(f => ({ ...f, tier }))}
              className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                filters.tier === tier
                  ? "bg-amber-600 border-amber-500 text-white"
                  : "border-slate-600 text-slate-400 hover:border-slate-500"
              }`}
            >
              {tier === "" ? "All Tiers" : TIER_LABELS[tier]}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.dualUseOnly}
            onChange={e => setFilters(f => ({ ...f, dualUseOnly: e.target.checked }))}
            className="rounded"
          />
          Dual-use only
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.exitPressureOnly}
            onChange={e => setFilters(f => ({ ...f, exitPressureOnly: e.target.checked }))}
            className="rounded"
          />
          Exit pressure only
        </label>
        <span className="ml-auto text-xs text-slate-500">{targets.length} companies</span>
      </div>

      {/* Table */}
      <Card className="bg-slate-800/60 border-slate-700 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400">Loading VC portfolio data…</div>
        ) : targets.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-slate-400 mb-2">No portfolio companies yet.</p>
            <p className="text-xs text-slate-500">Run seed_vc_funds.py, then trigger a portfolio scrape and re-score.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-700 text-xs text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Company</th>
                  <th className="py-3 px-4">VC Fund</th>
                  <th className="py-3 px-4 w-32">Deal Quality</th>
                  <th className="py-3 px-4">Signals</th>
                  <th className="py-3 px-4">Held</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {targets.map(company => (
                  <CompanyRow
                    key={company.id}
                    company={company}
                    onSelect={setSelectedCompany}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Detail panel */}
      <CompanyDetailPanel company={selectedCompany} onClose={() => setSelectedCompany(null)} />
      {selectedCompany && (
        <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setSelectedCompany(null)} />
      )}
    </div>
  );
}
