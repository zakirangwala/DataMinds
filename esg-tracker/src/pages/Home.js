import React from "react";
import { Link } from "react-router-dom";
import CompanyCard from "../components/CompanyCard";
import ESGDefinitionCards from "../components/ESGDefinitionCards"; // Import the new component
import { companiesData } from "../data/companies";

function Home() {
  return (
    <div style={{ backgroundColor: "#1B1D1E", minHeight: "100vh", color: "#fff" }}>
      <div style={{ width: "100%", maxWidth: "960px", margin: "0 auto", padding: "1rem" }}>
        
        <ESGDefinitionCards />

        {/* Search Bar */}
        <div>
          <input
            type="text"
            placeholder="Search company"
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

        {/* Consumer Goods Sector Section */}
        <h2 style={{ fontSize: "16px", marginBottom: "1rem" }}>Sector: Consumer Goods</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: "1rem",
            marginBottom: "2rem",
          }}
        >
          {companiesData.slice(0, 6).map((company) => (
            <Link
              key={company.id}
              to={`/company/${company.slug}`}
              style={{ textDecoration: "none" }}
            >
              <CompanyCard
                name={company.name}
                summary={company.summary}
                environmental={company.esgScores.environmental}
                social={company.esgScores.social}
                governance={company.esgScores.governance}
                esgTotal={company.esgScores.total}
                stockPrice={company.stockPrice}
                stockChange={company.stockChange}
              />
            </Link>
          ))}
        </div>

      </div>
    </div>
  );
}

export default Home;
