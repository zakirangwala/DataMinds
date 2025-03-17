import React, { useState, useEffect } from "react";
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

// Register Chart.js components
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

// Allowed tickers list (modify as needed)
const allowedTickers = [
  'OTEX.TO', 'KXS.TO', 'DSG.TO', 'CSU.TO', 'SHOP.TO', 'LSPD.TO', 'DCBO.TO', 'ENGH.TO', 'HAI.TO', 'TIXT.TO', 
  'ET.TO', 'BLN.TO', 'DND.TO', 'TSAT.TO', 'ALYA.TO', 'ACX.TO', 'AKT-A.TO', 'ATH.TO', 'BTE.TO', 'BIR.TO', 
  'CNE.TO', 'CJ.TO', 'FRU.TO', 'FEC.TO', 'GFR.TO', 'IPCO.TO', 'JOY.TO', 'KEC.TO', 'MEG.TO', 'NVA.TO', 
  'BR.TO', 'TPX-A.TO', 'LAS-A.TO', 'SOY.TO', 'ADW-A.TO', 'CSW-B.TO', 'RSI.TO', 'EMP-A.TO', 'DOL.TO', 
  'WN-PA.TO', 'BU.TO', 'DTEA.V', 'HLF.TO', 'JWEL.TO', 'MFI.TO'
];

function CompanyDetail() {
  const { ticker } = useParams(); // e.g. "/company/ACX.TO"
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sectorCompanies, setSectorCompanies] = useState([]);
  const [sectorAverages, setSectorAverages] = useState([]);

  useEffect(() => {
    fetchData();
  }, [ticker]);

  const fetchData = async () => {
    try {
      // 1) Fetch basic company info from companies table
      const { data: compData, error: compError } = await supabase
        .from("companies")
        .select("ticker, name, sector, long_business_summary")
        .eq("ticker", ticker)
        .single();
      if (compError) throw compError;

      // 2) Fetch ESG summaries from esg_report_analysis table
      const { data: esgAnalysis, error: esgAnalysisError } = await supabase
        .from("esg_report_analysis")
        .select("environmental_summary, social_summary, governance_summary")
        .eq("ticker", ticker)
        .single();
      if (esgAnalysisError && esgAnalysisError.code !== "PGRST116") throw esgAnalysisError;

      // 3) Fetch numeric ESG scores from final_esg_scores table
      const { data: esgScores, error: esgScoresError } = await supabase
        .from("final_esg_scores")
        .select("environmental_score, social_score, governance_score, total_esg_score")
        .eq("ticker", ticker)
        .single();
      if (esgScoresError && esgScoresError.code !== "PGRST116") throw esgScoresError;

      // 4) Fetch sentiment articles from sentiment_data table
      const { data: sentimentData, error: sentimentError } = await supabase
        .from("sentiment_data")
        .select("article_title, article_text, article_published, article_top_image, article_resolved_url")
        .eq("ticker", ticker);
      if (sentimentError) throw sentimentError;

      const combined = {
        ...compData,
        environmental_summary: esgAnalysis?.environmental_summary || "Not available",
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
  };

  // Fetch companies in the same sector (for Chart 1/2/3)
  const fetchSectorCompanies = async (sector) => {
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
        .select("ticker, total_esg_score")
        .in("ticker", tickers);
      if (secESGError) {
        console.error("Error fetching sector ESG scores:", secESGError);
        setSectorCompanies([]);
        return;
      }
      const merged = (secData || []).map((comp) => {
        const matching = (secESGData || []).find((esg) => esg.ticker === comp.ticker);
        return {
          ...comp,
          total_esg_score: matching?.total_esg_score ?? 0,
        };
      });
      setSectorCompanies(merged);
    } catch (error) {
      console.error("Error in fetchSectorCompanies:", error);
      setSectorCompanies([]);
    }
  };

  // Fetch average ESG scores by sector (for Chart 4)
  const fetchSectorAverages = async () => {
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
        const matching = (allESGData || []).find((esg) => esg.ticker === comp.ticker);
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
        average_esg: groups[sec].count > 0 ? (groups[sec].total / groups[sec].count).toFixed(0) : 0,
      }));
      setSectorAverages(averages);
    } catch (error) {
      console.error("Error in fetchSectorAverages:", error);
      setSectorAverages([]);
    }
  };

  // Prepare chart data for same-sector companies (Chart 1/2/3)
  const getSectorChartData = () => {
    return {
      labels: sectorCompanies.map((c) => c.name),
      datasets: [
        {
          label: "Total ESG Score",
          data: sectorCompanies.map((c) => c.total_esg_score),
          borderColor: "rgba(75, 192, 192, 1)", // for line
          backgroundColor: "rgba(75, 192, 192, 0.6)", // for bar
          tension: 0.3,
          fill: false,
        },
      ],
    };
  };

  // chart data for sector averages (Chart 4)
  const getSectorAveragesChartData = () => {
    return {
      labels: sectorAverages.map((s) => s.sector),
      datasets: [
        {
          label: "Average ESG Score",
          data: sectorAverages.map((s) => s.average_esg),
          backgroundColor: "rgba(153, 102, 255, 0.6)",
        },
      ],
    };
  };

  // zoom in the y-axis for Chart 4
  const getSectorAveragesOptions = () => {
    const sectorVals = sectorAverages.map((s) => Number(s.average_esg));
    if (sectorVals.length === 0) {
      return { responsive: true };
    }
    const minVal = Math.min(...sectorVals);
    const maxVal = Math.max(...sectorVals);

    const yMin = minVal - 5 > 0 ? minVal - 5 : 0;
    const yMax = maxVal + 5;

    return {
      responsive: true,
      scales: {
        y: {
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

  // For Energy, Technology, or Consumer Goods -> use a line chart
  const isLineChart =
    sector === "Energy" ||
    sector === "Technology" ||
    sector === "Consumer Goods";

  return (
    <div style={{ backgroundColor: "#1B1D1E", minHeight: "100vh", color: "#fff" }}>
      <div style={{ maxWidth: "960px", margin: "0 auto", padding: "2rem" }}>
        {/* Company Name & Sector */}
        <h1 style={{ fontSize: "32px", marginBottom: "0.5rem" }}>
          {name?.toUpperCase() || "Not available"}
        </h1>
        <p style={{ margin: "0 0 1rem 0", fontSize: "14px", color: "#ccc" }}>
          Sector: {sector || "Not available"}
        </p>

        {/* Business Summary */}
        <h2 style={{ marginBottom: "1rem" }}>Business Summary</h2>
        <p style={{ color: "#ccc" }}>
          {long_business_summary || "Not available"}
        </p>

        {/* ESG Score Card */}
        <h2 style={{ marginTop: "2rem" }}>ESG Scores</h2>
        <ESGScoreCard esgScores={final_esg_scores} />

        {/* ESG Summaries */}
        <h2 style={{ marginTop: "2rem" }}>ESG Breakdown</h2>
        <h3 style={{ marginTop: "1rem" }}>Environmental (E) Summary:</h3>
        <p style={{ color: "#ccc" }}>
          {environmental_summary || "Not available"}
        </p>
        <h3 style={{ marginTop: "1rem" }}>Social (S) Summary:</h3>
        <p style={{ color: "#ccc" }}>
          {social_summary || "Not available"}
        </p>
        <h3 style={{ marginTop: "1rem" }}>Governance (G) Summary:</h3>
        <p style={{ color: "#ccc" }}>
          {governance_summary || "Not available"}
        </p>

        {/* Chart for Specific Sector (Chart 1, 2, or 3) */}
        {sectorCompanies.length > 0 && (
          <div style={{ marginTop: "2rem" }}>
            <h2>{sector} ESG Analysis Chart</h2>
            {isLineChart ? (
              <Line
                data={getSectorChartData()}
                options={{ responsive: true }}
              />
            ) : (
              <Bar
                data={getSectorChartData()}
                options={{ responsive: true }}
              />
            )}
          </div>
        )}

        {/* Chart for Sector Averages (Chart 4) */}
        {sectorAverages.length > 0 && (
          <div style={{ marginTop: "2rem" }}>
            <h2>Sector ESG Analysis Chart</h2>
            <Bar
              data={getSectorAveragesChartData()}
              options={getSectorAveragesOptions()}
            />
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
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default CompanyDetail;
