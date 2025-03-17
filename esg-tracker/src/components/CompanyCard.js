import React from "react";
import { FaCaretUp, FaCaretDown } from "react-icons/fa";

const CompanyCard = ({
  name,
  summary,
  esgTotal,
  stockPrice,
  stockChange,
  onClick,
}) => {
  // Truncate summary to 100 characters
  const snippetLength = 100;
  const snippet =
    summary.length > snippetLength
      ? summary.substring(0, snippetLength) + "..."
      : summary;

  // For stock price arrow:
  const stockIcon =
    stockChange >= 0 ? (
      <FaCaretUp style={{ color: "green" }} />
    ) : (
      <FaCaretDown style={{ color: "red" }} />
    );

  // For ESG score arrow (based on esgTotal):
  const threshold = 50;
  const esgIcon =
    esgTotal >= threshold ? (
      <FaCaretUp style={{ color: "green" }} />
    ) : (
      <FaCaretDown style={{ color: "red" }} />
    );

  return (
    <div
      onClick={onClick}
      style={{
        backgroundColor: "#2D2F30",
        padding: "1.5rem",
        borderRadius: "8px",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        boxShadow: "0 4px 10px rgba(0, 0, 0, 0.2)",
        color: "#fff",
        cursor: "pointer",
      }}
    >
      <h3 style={{ fontSize: "16px", fontWeight: "bold", margin: 0 }}>
        {name}
      </h3>
      {/* Use truncated snippet instead of full summary */}
      <p style={{ fontSize: "13px", color: "#ccc", margin: 0 }}>{snippet}</p>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        {/* ESG Score */}
        <div
          style={{
            backgroundColor: "#1B1D1E",
            padding: "0.8rem",
            borderRadius: "8px",
            textAlign: "center",
            flex: 1,
          }}
        >
          <p style={{ fontSize: "10px", color: "#888", margin: 0 }}>
            ESG Score
          </p>
          <p style={{ fontSize: "14px", fontWeight: "bold", margin: 0 }}>
            {esgTotal.toFixed(2)} {esgIcon}
          </p>
        </div>

        {/* Stock Price */}
        <div
          style={{
            backgroundColor: "#1B1D1E",
            padding: "0.8rem",
            borderRadius: "8px",
            textAlign: "center",
            flex: 1,
          }}
        >
          <p style={{ fontSize: "10px", color: "#888", margin: 0 }}>
            Stock Price
          </p>
          <p style={{ fontSize: "14px", fontWeight: "bold", margin: 0 }}>
            {stockPrice.toFixed(2)} {stockIcon} {Math.abs(stockChange)}%
          </p>
        </div>
      </div>
    </div>
  );
};

export default CompanyCard;
