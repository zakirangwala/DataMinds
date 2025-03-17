import React from "react";

const ESGScoreCard = ({ esgScores }) => {
  const {
    environmental_score = 0,
    social_score = 0,
    governance_score = 0,
    total_esg_score = 0,
  } = esgScores;

  const eScore = environmental_score.toFixed(0);
  const sScore = social_score.toFixed(0);
  const gScore = governance_score.toFixed(0);
  const totalScore = total_esg_score.toFixed(0);

  const cardStyle = {
    backgroundColor: "#2D2F30",
    borderRadius: "8px",
    padding: "1rem",
    display: "flex",
    alignItems: "center",
    minWidth: "80px",
    justifyContent: "center",
  };

  const circleStyle = {
    width: "40px",
    height: "40px",
    borderRadius: "50%",
    backgroundColor: "black",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginRight: "0.5rem",
  };

  return (
    <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
      {/* Environmental */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={{ color: "green", fontSize: "20px", fontWeight: "bold" }}>E</span>
        </div>
        <span style={{ color: "green", fontSize: "20px", fontWeight: "bold" }}>
          {eScore}/100
        </span>
      </div>

      {/* Social */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={{ color: "blue", fontSize: "20px", fontWeight: "bold" }}>S</span>
        </div>
        <span style={{ color: "blue", fontSize: "20px", fontWeight: "bold" }}>
          {sScore}/100
        </span>
      </div>

      {/* Governance */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={{ color: "purple", fontSize: "20px", fontWeight: "bold" }}>G</span>
        </div>
        <span style={{ color: "purple", fontSize: "20px", fontWeight: "bold" }}>
          {gScore}/100
        </span>
      </div>

      {/* Total */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={{ color: "gold", fontSize: "20px", fontWeight: "bold" }}>T</span>
        </div>
        <span style={{ color: "gold", fontSize: "20px", fontWeight: "bold" }}>
          {totalScore}/100
        </span>
      </div>
    </div>
  );
};

export default ESGScoreCard;
