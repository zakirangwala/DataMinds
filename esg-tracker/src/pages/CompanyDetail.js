import React from "react";
import { useParams } from "react-router-dom";
import { companiesData } from "../data/companies";
import ESGScoreCard from "../components/ESGScoreCard";
import NewsCard from "../components/NewsCard"; // Import the updated NewsCard

function CompanyDetail() {
  const { slug } = useParams();
  const company = companiesData.find((c) => c.slug === slug);

  if (!company) {
    return (
      <div style={{ color: "#fff", padding: "1rem" }}>
        <h2>Company not found</h2>
      </div>
    );
  }

  // Ensure numeric values are valid
  const safeStockPrice =
    typeof company.stockPrice === "number" ? company.stockPrice : 0;
  const safeStockChange =
    typeof company.stockChange === "number" ? company.stockChange : 0;

  // Identify the company's ticker
  const { ticker } = company;

  // Filter all companies that share the same ticker
  const sameTickerCompanies = companiesData.filter((c) => c.ticker === ticker);

  // Collect all articles from those companies (using flatMap)
  const allArticles = sameTickerCompanies.flatMap((co) => co.sentimentData || []);

  return (
    <div style={{ backgroundColor: "#1B1D1E", minHeight: "100vh", color: "#fff" }}>
      <div style={{ maxWidth: "960px", margin: "0 auto", padding: "2rem" }}>
        <h1 style={{ fontSize: "32px", marginBottom: "1rem" }}>
          {company.name.toUpperCase()}
        </h1>

        {/* New ESG Score Card (E, S, G, and total) */}
        <ESGScoreCard esgScores={company.esgScores} />

        {/* Display all articles in NewsCards */}
        <h2 style={{ marginTop: "2rem", marginBottom: "1rem" }}>Latest News</h2>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  {allArticles.map((article, index) => (
                    <NewsCard
                      key={index}
                      articleTitle={article.article_title}
                      articleText={article.article_text}
                      articleResolvedUrl={article.article_resolved_url}
                      articleTopImage={article.article_top_image}
                      articlePublished={article.article_published}
                    />
                  ))}
                </div>
                
        {/* Stock Price Card */}
        <div style={{ display: "flex", gap: "2rem", marginBottom: "2rem", marginTop: "2rem" }}>
          <div
            style={{
              backgroundColor: "#2D2F30",
              borderRadius: "8px",
              padding: "1rem",
              flex: 1,
            }}
          >
            <h2 style={{ margin: 0 }}>Stock Price</h2>
            <p style={{ fontSize: "2rem", margin: 0 }}>
              ${safeStockPrice.toFixed(2)}
            </p>
            <p
              style={{
                color: safeStockChange >= 0 ? "green" : "red",
                fontSize: "1rem",
                margin: 0,
              }}
            >
              {safeStockChange >= 0 ? "▲" : "▼"} {Math.abs(safeStockChange)}%
            </p>
          </div>
        </div>

        <h2 style={{ marginBottom: "1rem" }}>Business Summary</h2>
        <p style={{ color: "#ccc" }}>
          {company.summary} Lorem ipsum dolor sit amet, consectetur adipiscing elit...
        </p>

        <h2 style={{ marginTop: "2rem" }}>ESG Breakdown</h2>
        <p style={{ color: "#ccc" }}>
          Environmental, Social, and Governance details...
        </p>
      </div>
    </div>
  );
}

export default CompanyDetail;
