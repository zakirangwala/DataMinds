import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import { supabase } from "../supabaseClient";
import ESGScoreCard from "../components/ESGScoreCard";
import NewsCard from "../components/NewsCard";

import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
);

// Allowed tickers list
const allowedTickers = [
  "OTEX.TO",
  "KXS.TO",
  "DSG.TO",
  "CSU.TO",
  "SHOP.TO",
  "LSPD.TO",
  "DCBO.TO",
  "ENGH.TO",
  "HAI.TO",
  "TIXT.TO",
  "ET.TO",
  "BLN.TO",
  "DND.TO",
  "TSAT.TO",
  "ALYA.TO",
  "ACX.TO",
  "AKT-A.TO",
  "ATH.TO",
  "BTE.TO",
  "BIR.TO",
  "CNE.TO",
  "CJ.TO",
  "FRU.TO",
  "FEC.TO",
  "GFR.TO",
  "IPCO.TO",
  "JOY.TO",
  "KEC.TO",
  "MEG.TO",
  "NVA.TO",
  "BR.TO",
  "TPX-A.TO",
  "LAS-A.TO",
  "SOY.TO",
  "ADW-A.TO",
  "CSW-B.TO",
  "RSI.TO",
  "EMP-A.TO",
  "DOL.TO",
  "WN-PA.TO",
  "BU.TO",
  "DTEA.V",
  "HLF.TO",
  "JWEL.TO",
  "MFI.TO",
];

function CompanyDetail() {
  const { ticker } = useParams();
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sectorCompanies, setSectorCompanies] = useState([]);
  const [sectorAverages, setSectorAverages] = useState([]);

  // Fetch companies in the same sector along with individual ESG component scores
  const fetchSectorCompanies = useCallback(async (sector) => {
    try {
      const { data: secData, error: secError } = await supabase
        .from("companies")
        .select("ticker, name, sector")
        .eq("sector", sector)
        .in("ticker", allowedTickers);
      if (secError) {
        console.error("Error fetching sector companies:", secError);
        setSectorCompanies([]);
        return;
      }
      const tickers = secData.map((c) => c.ticker);
      const { data: secESGData, error: secESGError } = await supabase
        .from("final_esg_scores")
        .select(
          "ticker, total_esg_score, environmental_score, social_score, governance_score"
        )
        .in("ticker", tickers);
      if (secESGError) {
        console.error("Error fetching sector ESG scores:", secESGError);
        setSectorCompanies([]);
        return;
      }
      const merged = (secData || []).map((comp) => {
        const matching = (secESGData || []).find(
          (esg) => esg.ticker === comp.ticker
        );
        return {
          ...comp,
          total_esg_score: matching?.total_esg_score ?? 0,
          environmental_score: matching?.environmental_score ?? 0,
          social_score: matching?.social_score ?? 0,
          governance_score: matching?.governance_score ?? 0,
        };
      });
      setSectorCompanies(merged);
    } catch (error) {
      console.error("Error in fetchSectorCompanies:", error);
      setSectorCompanies([]);
    }
  }, []);

  // Fetch average ESG scores by sector
  const fetchSectorAverages = useCallback(async () => {
    try {
      const { data: allCompanies, error: allError } = await supabase
        .from("companies")
        .select("ticker, sector, name")
        .in("ticker", allowedTickers);
      if (allError) {
        console.error("Error fetching all companies:", allError);
        setSectorAverages([]);
        return;
      }
      const tickers = allCompanies.map((c) => c.ticker);
      const { data: allESGData, error: allESGError } = await supabase
        .from("final_esg_scores")
        .select("ticker, total_esg_score")
        .in("ticker", tickers);
      if (allESGError) {
        console.error("Error fetching all ESG scores:", allESGError);
        setSectorAverages([]);
        return;
      }
      const merged = (allCompanies || []).map((comp) => {
        const matching = (allESGData || []).find(
          (esg) => esg.ticker === comp.ticker
        );
        return {
          ...comp,
          total_esg_score: matching?.total_esg_score ?? 0,
        };
      });
      // Group by sector and compute average
      const groups = {};
      merged.forEach((comp) => {
        const sec = comp.sector || "Unknown";
        if (!groups[sec]) {
          groups[sec] = { total: 0, count: 0 };
        }
        groups[sec].total += comp.total_esg_score;
        groups[sec].count += 1;
      });
      const averages = Object.keys(groups).map((sec) => ({
        sector: sec,
        average_esg:
          groups[sec].count > 0
            ? (groups[sec].total / groups[sec].count).toFixed(0)
            : 0,
      }));
      setSectorAverages(averages);
    } catch (error) {
      console.error("Error in fetchSectorAverages:", error);
      setSectorAverages([]);
    }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      // 1) Fetch basic company info
      const { data: compData, error: compError } = await supabase
        .from("companies")
        .select("ticker, name, sector, long_business_summary")
        .eq("ticker", ticker)
        .single();
      if (compError) throw compError;

      // 2) Fetch ESG summaries
      const { data: esgAnalysis, error: esgAnalysisError } = await supabase
        .from("esg_report_analysis")
        .select("environmental_summary, social_summary, governance_summary")
        .eq("ticker", ticker)
        .single();
      if (esgAnalysisError && esgAnalysisError.code !== "PGRST116")
        throw esgAnalysisError;

      // 3) Fetch numeric ESG scores
      const { data: esgScores, error: esgScoresError } = await supabase
        .from("final_esg_scores")
        .select(
          "environmental_score, social_score, governance_score, total_esg_score"
        )
        .eq("ticker", ticker)
        .single();
      if (esgScoresError && esgScoresError.code !== "PGRST116")
        throw esgScoresError;

      // 4) Fetch sentiment articles
      const { data: sentimentData, error: sentimentError } = await supabase
        .from("sentiment_data")
        .select(
          "article_title, article_text, article_published, article_top_image, article_resolved_url, search_source_title"
        )
        .eq("ticker", ticker);
      if (sentimentError) throw sentimentError;

      const combined = {
        ...compData,
        environmental_summary:
          esgAnalysis?.environmental_summary || "Not available",
        social_summary: esgAnalysis?.social_summary || "Not available",
        governance_summary: esgAnalysis?.governance_summary || "Not available",
        final_esg_scores: {
          environmental_score: esgScores?.environmental_score ?? 0,
          social_score: esgScores?.social_score ?? 0,
          governance_score: esgScores?.governance_score ?? 0,
          total_esg_score: esgScores?.total_esg_score ?? 0,
        },
        sentiment_data: sentimentData || [],
      };

      setCompany(combined);

      await fetchSectorCompanies(combined.sector);
      await fetchSectorAverages();
    } catch (err) {
      console.error("Error fetching data:", err);
      setCompany(null);
    } finally {
      setLoading(false);
    }
  }, [ticker, fetchSectorCompanies, fetchSectorAverages]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Helper function to generate chart data for a given score type
  const getSectorChartDataFor = (scoreField, label) => {
    return {
      labels: sectorCompanies.map((c) => c.name),
      datasets: [
        {
          label: label,
          data: sectorCompanies.map((c) => c[scoreField]),
          borderColor: "rgba(75, 192, 192, 1)",
          backgroundColor: "rgba(75, 192, 192, 0.6)",
          tension: 0.3,
          fill: false,
        },
      ],
    };
  };

  // Base chart options
  const baseChartOptions = {
    responsive: true,
    scales: {
      x: {
        ticks: { color: "#fff" },
        grid: { color: "#3A3A3A", borderColor: "#666" },
      },
      y: {
        ticks: { color: "#fff" },
        grid: { color: "#3A3A3A", borderColor: "#666" },
      },
    },
    plugins: {
      legend: { labels: { color: "#fff" } },
      title: { color: "#fff" },
    },
  };

  const smallFontChartOptions = {
    ...baseChartOptions,
    scales: {
      x: {
        ...baseChartOptions.scales.x,
        ticks: { ...baseChartOptions.scales.x.ticks, font: { size: 10 } },
      },
      y: {
        ...baseChartOptions.scales.y,
        ticks: { ...baseChartOptions.scales.y.ticks, font: { size: 10 } },
      },
    },
    plugins: {
      ...baseChartOptions.plugins,
      legend: {
        ...baseChartOptions.plugins.legend,
        labels: {
          ...baseChartOptions.plugins.legend.labels,
          font: { size: 10 },
        },
      },
      title: { ...baseChartOptions.plugins.title, font: { size: 12 } },
    },
  };

  // Zoom in the y-axis for sector averages
  const getSectorAveragesOptions = () => {
    const sectorVals = sectorAverages.map((s) => Number(s.average_esg));
    if (sectorVals.length === 0) return smallFontChartOptions;
    const minVal = Math.min(...sectorVals);
    const maxVal = Math.max(...sectorVals);
    const yMin = minVal - 5 > 0 ? minVal - 5 : 0;
    const yMax = maxVal + 5;

    return {
      ...smallFontChartOptions,
      scales: {
        x: { ...smallFontChartOptions.scales.x },
        y: {
          ...smallFontChartOptions.scales.y,
          beginAtZero: false,
          min: yMin,
          max: yMax,
        },
      },
    };
  };

  if (loading) {
    return <p style={{ color: "#fff", padding: "1rem" }}>Loading...</p>;
  }
  if (!company) {
    return (
      <div style={{ color: "#fff", padding: "1rem" }}>
        <h2>Company not found</h2>
      </div>
    );
  }

  // Destructure company data with fallbacks
  const {
    name,
    sector,
    long_business_summary,
    environmental_summary,
    social_summary,
    governance_summary,
    final_esg_scores,
    sentiment_data = [],
  } = company;

  const isLineChart =
    sector === "Energy" ||
    sector === "Technology" ||
    sector === "Consumer Defensive";

  return (
    <div
      style={{ backgroundColor: "#1B1D1E", minHeight: "100vh", color: "#fff" }}
    >
      <div style={{ maxWidth: "960px", margin: "0 auto", padding: "2rem" }}>
        {/* Company Name & Sector */}
        <h1
          style={{
            fontSize: "40px",
            marginBottom: "0.5rem",
            textAlign: "center",
          }}
        >
          {name?.toUpperCase() || "Not available"}
        </h1>
        <p
          style={{
            margin: "0 0 1rem 0",
            fontSize: "18px",
            textAlign: "center",
          }}
        >
          Sector: {sector || "Not available"}
        </p>

        {/* Business Summary */}
        <h2 style={{ marginBottom: "1rem" }}>Business Summary</h2>
        <p style={{ fontSize: "16px" }}>
          {long_business_summary || "Not available"}
        </p>

        {/* ESG Score Card */}
        <h2 style={{ marginTop: "2rem" }}>ESG Scores</h2>
        <ESGScoreCard esgScores={final_esg_scores} />

        {/* ESG Summaries */}
        <h2 style={{ marginTop: "2rem" }}>ESG Breakdown</h2>
        <h3 style={{ marginTop: "1rem" }}>Environmental (E) Summary:</h3>
        <p style={{ fontSize: "16px" }}>
          {environmental_summary || "Not available"}
        </p>
        <h3 style={{ marginTop: "1rem" }}>Social (S) Summary:</h3>
        <p style={{ fontSize: "16px" }}>{social_summary || "Not available"}</p>
        <h3 style={{ marginTop: "1rem" }}>Governance (G) Summary:</h3>
        <p style={{ fontSize: "16px" }}>
          {governance_summary || "Not available"}
        </p>

        {/* Sector Average ESG Chart (larger container) */}
        {sectorAverages.length > 0 && (
          <div style={{ marginTop: "2rem" }}>
            <h2 style={{ fontSize: "18px", marginTop: "1rem" }}>
              Sector Average ESG
            </h2>
            <div style={{ maxWidth: "600px", margin: "0 auto" }}>
              <Bar
                data={{
                  labels: sectorAverages.map((s) => s.sector),
                  datasets: [
                    {
                      label: "Average ESG Score",
                      data: sectorAverages.map((s) => s.average_esg),
                      backgroundColor: "rgba(153, 102, 255, 0.6)",
                    },
                  ],
                }}
                options={getSectorAveragesOptions()}
              />
            </div>
          </div>
        )}

        {/* Detailed Sector Analysis */}
        {sectorCompanies.length > 0 && (
          <div style={{ marginTop: "2rem" }}>
            <h2 style={{ marginBottom: "1rem" }}>Detailed {sector} Analysis</h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: "1rem",
              }}
            >
              <div>
                <h3 style={{ fontSize: "16px", textAlign: "center" }}>
                  Environmental Score
                </h3>
                {isLineChart ? (
                  <Line
                    data={getSectorChartDataFor(
                      "environmental_score",
                      "Environmental Score"
                    )}
                    options={smallFontChartOptions}
                  />
                ) : (
                  <Bar
                    data={getSectorChartDataFor(
                      "environmental_score",
                      "Environmental Score"
                    )}
                    options={smallFontChartOptions}
                  />
                )}
              </div>
              <div>
                <h3 style={{ fontSize: "16px", textAlign: "center" }}>
                  Social Score
                </h3>
                {isLineChart ? (
                  <Line
                    data={getSectorChartDataFor("social_score", "Social Score")}
                    options={smallFontChartOptions}
                  />
                ) : (
                  <Bar
                    data={getSectorChartDataFor("social_score", "Social Score")}
                    options={smallFontChartOptions}
                  />
                )}
              </div>
              <div>
                <h3 style={{ fontSize: "16px", textAlign: "center" }}>
                  Governance Score
                </h3>
                {isLineChart ? (
                  <Line
                    data={getSectorChartDataFor(
                      "governance_score",
                      "Governance Score"
                    )}
                    options={smallFontChartOptions}
                  />
                ) : (
                  <Bar
                    data={getSectorChartDataFor(
                      "governance_score",
                      "Governance Score"
                    )}
                    options={smallFontChartOptions}
                  />
                )}
              </div>
              <div>
                <h3 style={{ fontSize: "16px", textAlign: "center" }}>
                  Total ESG Score
                </h3>
                {isLineChart ? (
                  <Line
                    data={getSectorChartDataFor(
                      "total_esg_score",
                      "Total ESG Score"
                    )}
                    options={smallFontChartOptions}
                  />
                ) : (
                  <Bar
                    data={getSectorChartDataFor(
                      "total_esg_score",
                      "Total ESG Score"
                    )}
                    options={smallFontChartOptions}
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {/* Latest News */}
        <h2 style={{ marginTop: "2rem", marginBottom: "1rem" }}>Latest News</h2>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          {sentiment_data.map((article, index) => (
            <NewsCard
              key={index}
              articleTitle={article.article_title || "Not available"}
              articleText={article.article_text || "Not available"}
              articleResolvedUrl={article.article_resolved_url || "#"}
              articleTopImage={article.article_top_image || ""}
              articlePublished={article.article_published || "Not available"}
              searchSourceTitle={article.search_source_title || "Not available"}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default CompanyDetail;
