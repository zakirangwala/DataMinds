import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { supabase } from "../supabaseClient";
import CompanyCard from "../components/CompanyCard";
import ESGDefinitionCards from "../components/ESGDefinitionCards";

function Home() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  // List of tickers to include
  const allowedTickers = [
    "OTEX.TO", "KXS.TO", "DSG.TO", "CSU.TO", "SHOP.TO", "LSPD.TO", "DCBO.TO", "ENGH.TO", "HAI.TO", "TIXT.TO",
    "ET.TO", "BLN.TO", "DND.TO", "TSAT.TO", "ALYA.TO", "ACX.TO", "AKT-A.TO", "ATH.TO", "BTE.TO", "BIR.TO",
    "CNE.TO", "CJ.TO", "FRU.TO", "FEC.TO", "GFR.TO", "IPCO.TO", "JOY.TO", "KEC.TO", "MEG.TO", "NVA.TO",
    "BR.TO", "TPX-A.TO", "LAS-A.TO", "SOY.TO", "ADW-A.TO", "CSW-B.TO", "RSI.TO", "EMP-A.TO", "DOL.TO",
    "WN-PA.TO", "BU.TO", "DTEA.V", "HLF.TO", "JWEL.TO", "MFI.TO",
  ];

  useEffect(() => {
    fetchCompaniesData();
  }, []);

  const fetchCompaniesData = async () => {
    try {
      // Fetch basic company info
      const { data: companiesData, error: companiesError } = await supabase
        .from("companies")
        .select("ticker, name, sector, long_business_summary")
        .in("ticker", allowedTickers);

      if (companiesError) {
        console.error("Error fetching companies:", companiesError);
      }

      // Fetch final ESG scores for allowed tickers
      const { data: esgData, error: esgError } = await supabase
        .from("final_esg_scores")
        .select("ticker, environmental_score, social_score, governance_score, total_esg_score")
        .in("ticker", allowedTickers);

      if (esgError) {
        console.error("Error fetching ESG scores:", esgError);
      }

      // Merge companies with ESG scores by matching ticker
      const combined = (companiesData || []).map((comp) => {
        const matchingESG = (esgData || []).find((esg) => esg.ticker === comp.ticker);
        return {
          ...comp,
          environmental_score: matchingESG?.environmental_score ?? 0,
          social_score: matchingESG?.social_score ?? 0,
          governance_score: matchingESG?.governance_score ?? 0,
          total_esg_score: matchingESG?.total_esg_score ?? 0,
        };
      });
      setCompanies(combined);
    } catch (err) {
      console.error("Error in fetchCompaniesData:", err);
      setCompanies([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <p style={{ color: "#fff", padding: "1rem" }}>Loading...</p>;
  }

  // 1) Filter companies by name based on the search term
  const filteredCompanies = companies.filter((c) =>
    c.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 2) Group filtered companies by sector
  const groupedBySector = {};
  filteredCompanies.forEach((company) => {
    const sec = company.sector || "Unknown";
    if (!groupedBySector[sec]) {
      groupedBySector[sec] = [];
    }
    groupedBySector[sec].push(company);
  });

  return (
    <div style={{ backgroundColor: "#1B1D1E", minHeight: "100vh", color: "#fff" }}>
      <div style={{ width: "100%", maxWidth: "960px", margin: "0 auto", padding: "1rem" }}>
        
        <ESGDefinitionCards />

        {/* Search Bar */}
        <div>
          <input
            type="text"
            placeholder="Search company by name"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: "100%",
              padding: "1rem",
              borderRadius: "8px",
              border: "none",
              backgroundColor: "#232526",
              color: "#fff",
              fontSize: "14px",
              marginBottom: "1rem",
            }}
          />
        </div>

        {/* Render all sectors with their companies */}
        {Object.entries(groupedBySector).map(([sectorName, comps]) => (
          <div key={sectorName} style={{ marginBottom: "2rem" }}>
            <h2 style={{ fontSize: "16px", marginBottom: "1rem" }}>
              Sector: {sectorName}
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: "1rem",
              }}
            >
              {comps.map((company) => (
                <Link
                  key={company.ticker}
                  to={`/company/${company.ticker}`}
                  style={{ textDecoration: "none" }}
                >
                  <CompanyCard
                    name={company.name || "Not available"}
                    sector={company.sector || "Not available"}
                    summary={company.long_business_summary || "Not available"}
                    environmental={company.environmental_score}
                    social={company.social_score}
                    governance={company.governance_score}
                    esgTotal={company.total_esg_score}
                    
                    stockPrice={typeof company.stock_price === "number" ? company.stock_price : 0}
                    stockChange={typeof company.stock_change === "number" ? company.stock_change : 0}
                  />
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Home;
