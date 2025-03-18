import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { supabase } from "../supabaseClient";
import CompanyCard from "../components/CompanyCard";
import ESGDefinitionCards from "../components/ESGDefinitionCards";
import "font-awesome/css/font-awesome.min.css";

function Home() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchCompaniesData = useCallback(async () => {
    // List of tickers to include
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
        .select(
          "ticker, environmental_score, social_score, governance_score, total_esg_score"
        )
        .in("ticker", allowedTickers);

      if (esgError) {
        console.error("Error fetching ESG scores:", esgError);
      }

      // Merge companies with ESG scores by matching ticker
      const combined = (companiesData || []).map((comp) => {
        const matchingESG = (esgData || []).find(
          (esg) => esg.ticker === comp.ticker
        );
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
  }, []);

  useEffect(() => {
    fetchCompaniesData();
  }, [fetchCompaniesData]);

  if (loading) {
    return <p style={{ color: "#fff", padding: "1rem" }}>Loading...</p>;
  }

  // Filter companies by name based on the search term
  const filteredCompanies = companies.filter((c) =>
    c.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group filtered companies by sector
  const groupedBySector = {};
  filteredCompanies.forEach((company) => {
    const sec = company.sector || "Unknown";
    if (!groupedBySector[sec]) {
      groupedBySector[sec] = [];
    }
    groupedBySector[sec].push(company);
  });

  return (
    <div
      style={{ backgroundColor: "#1B1D1E", minHeight: "100vh", color: "#fff" }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "960px",
          margin: "0 auto",
          padding: "1rem",
        }}
      >
        <ESGDefinitionCards />

        {/* Search Bar */}
        <div
          style={{
            position: "relative",
            marginTop: "1rem",
            marginBottom: "1rem",
          }}
        >
          <i
            className="fa fa-search"
            style={{
              position: "absolute",
              top: "50%",
              left: "1rem",
              transform: "translateY(-50%)",
              color: "#AAAAAD",
              fontSize: "16px",
            }}
          ></i>
          <input
            type="text"
            placeholder="Search company by name"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: "94%",
              padding: "1rem 1rem 1rem 2.5rem",
              borderRadius: "8px",
              border: "none",
              backgroundColor: "#232526",
              color: "#fff",
              fontSize: "14px",
            }}
          />
        </div>

        {/* Render sectors with their companies */}
        {Object.entries(groupedBySector).map(([sectorName, comps]) => (
          <div key={sectorName} style={{ marginBottom: "2rem" }}>
            <h2 style={{ fontSize: "16px", marginBottom: "1rem" }}>
              Sector: {sectorName}
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: "1rem",
                alignItems: "stretch",
              }}
            >
              {comps.map((company) => (
                <Link
                  key={company.ticker}
                  to={`/company/${company.ticker}`}
                  style={{ display: "block", textDecoration: "none" }}
                >
                  <CompanyCard
                    name={company.name || "Not available"}
                    summary={company.long_business_summary || "Not available"}
                    esgTotal={company.total_esg_score}
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
