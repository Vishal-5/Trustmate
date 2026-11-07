"use client";

import React, { useState, useEffect } from 'react';

const API_BASE = 'http://127.0.0.1:8000';

export default function Home() {
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [mcpStatusText, setMcpStatusText] = useState("MCP Connecting...");
  const [orders, setOrders] = useState([]);
  const [recentSearches, setRecentSearches] = useState([]);

  // Explain modal state
  const [explainModalOpen, setExplainModalOpen] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState(null);
  const [aiSummary, setAiSummary] = useState("Generating compact AI explanation via TRUSTMATE MCP explain_score...");

  // Risk modal state
  const [riskModalOpen, setRiskModalOpen] = useState(false);
  const [pendingRiskOffer, setPendingRiskOffer] = useState(null);

  // Initialize status & window message listener
  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();
        setMcpStatusText('TRUSTMATE: ' + (data.trust_mcp_url?.includes('8001') ? 'Mock Mode' : 'Live MCP'));
      } catch {
        setMcpStatusText('TRUSTMATE: Connected');
      }
    }
    fetchStatus();

    const handleMessage = (event) => {
      if (event.data && event.data.type === 'PAYPAL_ORDER_CAPTURED') {
        alert(`✅ Payment Completed Successfully via PayPal Sandbox!\nOrder ID: ${event.data.order_id}`);
        loadDashboard();
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleSearch = async (overrideQuery) => {
    const q = (overrideQuery !== undefined ? overrideQuery : searchInput).trim();
    if (!q) return;

    setLoading(true);
    setResults(null);
    setDashboardOpen(false);

    try {
      const res = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      setLoading(false);

      if (!data.success && data.error) {
        alert(data.error);
        return;
      }
      setResults(data);
    } catch (err) {
      setLoading(false);
      alert('Search failed: ' + err.message);
    }
  };

  const setQueryAndSearch = (q) => {
    setSearchInput(q);
    handleSearch(q);
  };

  const openExplainModal = async (offer) => {
    setSelectedOffer(offer);
    setAiSummary("Generating compact AI explanation via TRUSTMATE MCP explain_score...");
    setExplainModalOpen(true);

    try {
      const res = await fetch(`${API_BASE}/api/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seller: offer.seller, url: offer.url }),
      });
      const data = await res.json();
      setAiSummary(data.summary || "No explanation summary available.");
    } catch (e) {
      setAiSummary("Could not load AI explanation: " + e.message);
    }
  };

  const closeExplainModal = () => {
    setExplainModalOpen(false);
    setSelectedOffer(null);
  };

  const startCheckout = (offer) => {
    // High-Risk gating check
    if (offer.trust && offer.trust.score !== null && offer.trust.score < 2.5) {
      setPendingRiskOffer(offer);
      setRiskModalOpen(true);
      return;
    }
    executeOrderCreation(offer, false);
  };

  const confirmRiskPayment = () => {
    setRiskModalOpen(false);
    if (pendingRiskOffer) {
      executeOrderCreation(pendingRiskOffer, true);
    }
  };

  const closeRiskModal = () => {
    setRiskModalOpen(false);
    setPendingRiskOffer(null);
  };

  const executeOrderCreation = async (offer, riskConfirmed) => {
    try {
      const res = await fetch(`${API_BASE}/api/order/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_title: offer.title,
          seller_name: offer.seller,
          price_inr: offer.price_inr,
          trust_score: offer.trust ? offer.trust.score : null,
          trust_label: offer.trust ? offer.trust.label : 'Unrated',
          risk_confirmed: riskConfirmed,
        }),
      });

      const data = await res.json();
      if (data.error) {
        alert('Order creation failed: ' + data.message);
        return;
      }

      // Open PayPal approval popup
      const width = 500, height = 650;
      const left = (window.screen.width / 2) - (width / 2);
      const top = (window.screen.height / 2) - (height / 2);
      const approveUrl = data.approve_url?.startsWith('http') ? data.approve_url : `${API_BASE}${data.approve_url}`;
      window.open(approveUrl, 'PayPalApproval', `width=${width},height=${height},top=${top},left=${left}`);
    } catch (e) {
      alert('Failed to initiate PayPal order: ' + e.message);
    }
  };

  const toggleDashboard = async () => {
    const nextState = !dashboardOpen;
    setDashboardOpen(nextState);
    if (nextState) {
      await loadDashboard();
    }
  };

  const loadDashboard = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard`);
      const data = await res.json();
      setOrders(data.orders || []);
      setRecentSearches(data.recent_searches || []);
    } catch {}
  };

  const renderBadge = (trust) => {
    if (!trust || trust.score === null) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-300">
          <i className="fa-solid fa-circle-question text-slate-400"></i>
          <span>Unrated</span>
        </span>
      );
    }
    const score = trust.score.toFixed(1);
    if (trust.score >= 4.0) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shadow-xs">
          <i className="fa-solid fa-shield-check text-emerald-600"></i>
          <span>{score} • {trust.label}</span>
        </span>
      );
    } else if (trust.score >= 2.5) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
          <i className="fa-solid fa-triangle-exclamation text-amber-600"></i>
          <span>{score} • {trust.label}</span>
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">
          <i className="fa-solid fa-shield-xmark text-rose-600"></i>
          <span>{score} • Risky</span>
        </span>
      );
    }
  };

  return (
    <>
      {/* Top Header Navigation */}
      <header className="glass sticky top-0 z-30 border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <i className="fa-solid fa-shield-halved text-lg"></i>
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-800 bg-clip-text text-transparent">
                TRUSTMATE
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                PayPal AI Agent
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-2 text-xs px-3 py-1.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>{mcpStatusText}</span>
            </div>
            <button
              onClick={toggleDashboard}
              className="flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 transition shadow-xs"
            >
              <i className="fa-solid fa-clock-rotate-left text-slate-500"></i>
              <span>Audit Dashboard</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto space-y-4 pt-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-xs font-semibold text-indigo-700">
            <i className="fa-solid fa-scale-balanced"></i>
            <span>Trust comes first, price second</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Never get scammed by a <span className="underline decoration-blue-500 decoration-wavy decoration-2">&quot;too good&quot;</span> deal again.
          </h1>
          <p className="text-base text-slate-600 max-w-2xl mx-auto">
            TRUSTMATE scores seller authenticity via Places, domain history, and Safe Browsing. We gate untrusted sellers before you pay with PayPal.
          </p>

          {/* Search Input Box */}
          <div className="pt-2">
            <div className="relative max-w-2xl mx-auto">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                <i className="fa-solid fa-magnifying-glass text-lg"></i>
              </div>
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="e.g. laptop under 60000 for programming"
                className="w-full pl-12 pr-32 py-4 rounded-2xl bg-white border-2 border-slate-200 focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-100 text-slate-800 text-base shadow-lg shadow-slate-200/50 transition"
                onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
              />
              <div className="absolute inset-y-2 right-2 flex items-center">
                <button
                  onClick={() => handleSearch()}
                  className="h-full px-5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition shadow-md flex items-center space-x-2"
                >
                  <span>Inspect</span>
                  <i className="fa-solid fa-arrow-right text-xs"></i>
                </button>
              </div>
            </div>

            {/* Prompt Suggestion Chips */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-3 text-xs text-slate-500">
              <span className="font-medium">Try:</span>
              <button
                onClick={() => setQueryAndSearch('laptop under 60000 for programming')}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
              >
                💻 Laptop under ₹60,000 for programming
              </button>
              <button
                onClick={() => setQueryAndSearch('noise cancelling headphones under 15000')}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
              >
                🎧 Headphones under ₹15,000
              </button>
              <button
                onClick={() => setQueryAndSearch('mechanical keyboard under 4000')}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
              >
                ⌨️ Keyboard under ₹4,000
              </button>
            </div>
          </div>
        </div>

        {/* Loading Indicator */}
        {loading && (
          <div className="text-center py-12 space-y-4">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent"></div>
            <p className="text-sm font-semibold text-slate-700">
              Agent executing <code className="text-xs bg-slate-100 px-2 py-1 rounded text-blue-700">rank_offers</code> tool on TRUSTMATE MCP...
            </p>
            <p className="text-xs text-slate-400">Verifying domain age, HTTPS certificates, Places listings &amp; Safe Browsing</p>
          </div>
        )}

        {/* Search Results Section */}
        {!loading && results && !dashboardOpen && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 text-sm">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  Verified Offers for &quot;{results.query}&quot;
                </h2>
                <p className="text-xs text-slate-500">
                  Ranked trust-first. Sellers below 2.5 are gated.
                </p>
              </div>
              <div className="mt-2 sm:mt-0 flex items-center space-x-2 text-xs font-semibold text-slate-600 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs">
                <i className="fa-solid fa-arrow-down-wide-short text-blue-600"></i>
                <span>Sort: 70% Trust + 30% Price</span>
              </div>
            </div>

            {/* Unverified Notes Banner */}
            {results.unverified_notes && results.unverified_notes.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 space-y-1">
                <div className="font-bold flex items-center space-x-1.5 text-amber-800">
                  <i className="fa-solid fa-circle-info"></i>
                  <span>Verification Notice (Honest Limits)</span>
                </div>
                <ul className="list-disc pl-5 space-y-0.5 text-amber-800/90">
                  {results.unverified_notes.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Offers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {results.offers.map((offer, idx) => {
                const priceUsd = (offer.price_inr * 0.012).toFixed(2);
                return (
                  <div
                    key={offer.id || idx}
                    className={`bg-white rounded-3xl border ${
                      offer.recommended
                        ? 'border-2 border-blue-500 shadow-lg shadow-blue-500/5 ring-4 ring-blue-50'
                        : 'border-slate-200 shadow-sm'
                    } p-6 flex flex-col justify-between transition hover:shadow-md relative overflow-hidden`}
                  >
                    <div>
                      {offer.recommended && (
                        <div className="bg-blue-600 text-white text-[10px] uppercase tracking-wider font-extrabold px-3 py-1 rounded-full inline-flex items-center space-x-1 mb-3 self-start shadow-xs">
                          <i className="fa-solid fa-star text-amber-300"></i>
                          <span>Recommended Pick (Trust-First)</span>
                        </div>
                      )}

                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-base font-bold text-slate-900 leading-snug">{offer.title}</h3>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Sold by <span className="font-semibold text-slate-700">{offer.seller}</span>
                          </p>
                        </div>
                        <div className="cursor-pointer" onClick={() => openExplainModal(offer)}>
                          {renderBadge(offer.trust)}
                        </div>
                      </div>

                      {offer.tradeoff_note && (
                        <div className="mt-3 p-3 bg-amber-50/80 border border-amber-200 rounded-xl flex items-start space-x-2 text-xs text-amber-900">
                          <i className="fa-solid fa-triangle-exclamation text-amber-600 mt-0.5 flex-shrink-0"></i>
                          <span><strong>Trade-off Alert:</strong> {offer.tradeoff_note}</span>
                        </div>
                      )}

                      <div className="mt-4 pt-4 border-t border-slate-100 flex items-baseline justify-between">
                        <div>
                          <div className="text-2xl font-extrabold text-slate-900">
                            ₹{offer.price_inr.toLocaleString('en-IN')}
                          </div>
                          <div className="text-xs text-slate-400">
                            ≈ ${priceUsd} USD (PayPal Sandbox)
                          </div>
                        </div>
                        <button
                          onClick={() => openExplainModal(offer)}
                          className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                        >
                          <span>Inspect signals</span>
                          <i className="fa-solid fa-chevron-right text-[10px]"></i>
                        </button>
                      </div>
                    </div>

                    <div className="mt-5 pt-3">
                      <button
                        onClick={() => startCheckout(offer)}
                        className={`w-full ${
                          offer.recommended
                            ? 'bg-blue-600 hover:bg-blue-700 text-white'
                            : 'bg-slate-900 hover:bg-black text-white'
                        } py-3 px-4 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-2 shadow-xs`}
                      >
                        <i className="fa-brands fa-paypal text-sm text-[#0070BA]"></i>
                        <span>Approve &amp; Pay with PayPal</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Dashboard Section */}
        {dashboardOpen && (
          <div className="space-y-6 pt-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Purchase &amp; Trust Audit Dashboard</h2>
                <p className="text-xs text-slate-500">Record of verified searches and authorized PayPal Sandbox transactions.</p>
              </div>
              <button
                onClick={toggleDashboard}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800"
              >
                ← Back to Search
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Captured PayPal Orders */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-800 flex items-center space-x-2">
                    <i className="fa-brands fa-paypal text-blue-600"></i>
                    <span>Captured PayPal Orders</span>
                  </h3>
                  <span className="text-xs bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded-full">
                    {orders.length} orders
                  </span>
                </div>
                <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                  {orders.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">No transactions captured yet.</p>
                  ) : (
                    orders.map((o) => (
                      <div key={o.id} className="p-3 rounded-xl border border-slate-100 bg-slate-50 text-xs space-y-1">
                        <div className="flex items-center justify-between font-bold text-slate-800">
                          <span>{o.item_title}</span>
                          <span className="text-emerald-600">${o.amount_usd.toFixed(2)} USD</span>
                        </div>
                        <div className="flex items-center justify-between text-slate-500 text-[11px]">
                          <span>
                            {o.seller_name} (Score: {o.trust_score !== null ? o.trust_score.toFixed(1) : 'Unrated'})
                          </span>
                          <span className="font-mono text-slate-400">
                            {o.order_id.substring(0, 15)}...
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Recent Searches */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-800 flex items-center space-x-2">
                    <i className="fa-solid fa-list-check text-indigo-600"></i>
                    <span>Recent Trust Checks</span>
                  </h3>
                </div>
                <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                  {recentSearches.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">No recent searches recorded.</p>
                  ) : (
                    recentSearches.map((s) => (
                      <div key={s.id} className="p-3 rounded-xl border border-slate-100 bg-slate-50 text-xs space-y-1">
                        <div className="flex items-center justify-between font-semibold text-slate-800">
                          <span>&quot;{s.query}&quot;</span>
                          <span className="text-slate-500">Max ₹{s.budget_inr.toLocaleString('en-IN')}</span>
                        </div>
                        <div className="text-[10px] text-slate-400">{s.created_at}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Tap-To-Explain Factors Slide-Over Modal */}
      {explainModalOpen && selectedOffer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-100 flex flex-col">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                  <span>{selectedOffer.seller}</span>
                  <span>{renderBadge(selectedOffer.trust)}</span>
                </h3>
                <p className="text-xs text-slate-500">Tap-to-Explain Signal Breakdown</p>
              </div>
              <button
                onClick={closeExplainModal}
                className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500"
              >
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* AI Summary Card */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-4 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-bold text-blue-900">
                  <i className="fa-solid fa-sparkles text-blue-600"></i>
                  <span>AI Authenticity Summary (explain_score)</span>
                </div>
                <p className="text-xs text-blue-950/80 leading-relaxed">{aiSummary}</p>
              </div>

              {/* Factors Checklist */}
              <div className="space-y-3">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Verified Signals</p>
                <div className="space-y-2.5">
                  {(selectedOffer.trust.factors || []).map((f, i) => {
                    let icon = 'fa-check text-emerald-500 bg-emerald-50';
                    let border = 'border-slate-100';
                    if (f.status === 'bad') {
                      icon = 'fa-xmark text-rose-500 bg-rose-50';
                      border = 'border-rose-100 bg-rose-50/20';
                    } else if (f.status === 'warn') {
                      icon = 'fa-exclamation text-amber-500 bg-amber-50';
                      border = 'border-amber-100 bg-amber-50/20';
                    } else if (f.status === 'unverified') {
                      icon = 'fa-question text-slate-400 bg-slate-50';
                    }

                    return (
                      <div key={i} className={`p-3 rounded-xl border ${border} flex items-start space-x-3 text-xs`}>
                        <div className={`w-6 h-6 rounded-full ${icon} flex items-center justify-center flex-shrink-0 text-xs mt-0.5`}>
                          <i className={`fa-solid ${icon.split(' ')[0]}`}></i>
                        </div>
                        <div className="flex-grow">
                          <div className="font-bold text-slate-800 flex items-center justify-between">
                            <span>{f.name}</span>
                            <span
                              className={`uppercase text-[9px] font-extrabold px-1.5 py-0.5 rounded ${
                                f.status === 'ok'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : f.status === 'bad'
                                  ? 'bg-rose-100 text-rose-800'
                                  : 'bg-slate-100 text-slate-600'
                              }`}
                            >
                              {f.status}
                            </span>
                          </div>
                          <div className="text-slate-600 mt-0.5 text-[11px]">{f.detail}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-end">
              <button
                onClick={closeExplainModal}
                className="px-5 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold text-xs rounded-xl transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* High Risk Gating Warning Modal (< 2.5 Score Second Confirm) */}
      {riskModalOpen && pendingRiskOffer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border-2 border-rose-200 text-center space-y-4">
            <div className="w-14 h-14 bg-rose-100 text-rose-600 rounded-2xl flex items-center justify-center mx-auto text-2xl shadow-inner">
              <i className="fa-solid fa-triangle-exclamation"></i>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-bold text-slate-900">High Risk Warning</h3>
              <p className="text-xs text-slate-600">
                This seller scored{' '}
                <span className="font-bold text-rose-600">
                  {pendingRiskOffer.trust?.score?.toFixed(1) || '1.9'} (Risky)
                </span>{' '}
                and has multiple authenticity red flags.
              </p>
            </div>

            <div className="bg-rose-50 border border-rose-100 rounded-xl p-3 text-left text-xs text-rose-900 space-y-1">
              <p className="font-semibold">Why this was flagged:</p>
              <p className="text-rose-800">
                {pendingRiskOffer.tradeoff_note || 'Newly registered domain and lack of physical business verification.'}
              </p>
            </div>

            <div className="space-y-2 pt-2">
              <button
                onClick={confirmRiskPayment}
                className="w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition shadow-md"
              >
                I understand the risks, proceed to PayPal anyway
              </button>
              <button
                onClick={closeRiskModal}
                className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2.5 px-4 rounded-xl text-xs transition"
              >
                Cancel (Recommended: Pick a Trusted Seller)
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

