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

  const containerStyle = {
    display: "flex",
    gap: "1rem",
    marginBottom: "2rem",
    width: "100%",
  };

  const cardStyle = {
    backgroundColor: "#2D2F30",
    borderRadius: "8px",
    padding: "1rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
    minWidth: "80px",
  };

  const circleStyle = {
    width: "80px",
    height: "80px",
    borderRadius: "50%",
    backgroundColor: "black",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginRight: "0.5rem",
  };

  const letterStyle = (color) => ({
    color: "#fff",
    fontSize: "50px",
    fontWeight: 600,
  });

  const numericScoreStyle = {
    fontSize: "45px",
    fontWeight: "bold",
  };

  const slashStyle = {
    fontSize: "25px",
    fontWeight: "bold",
  };

  return (
    <div style={containerStyle}>
      {/* Environmental */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={letterStyle("#48EB6C")}>E</span>
        </div>
        <span style={{ color: "#48EB6C" }}>
          <span style={numericScoreStyle}>{eScore}</span>
          <span style={slashStyle}>/100</span>
        </span>
      </div>

      {/* Social */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={letterStyle("#2BC6FF")}>S</span>
        </div>
        <span style={{ color: "#2BC6FF" }}>
          <span style={numericScoreStyle}>{sScore}</span>
          <span style={slashStyle}>/100</span>
        </span>
      </div>

      {/* Governance */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={letterStyle("#AD6CDE")}>G</span>
        </div>
        <span style={{ color: "#AD6CDE" }}>
          <span style={numericScoreStyle}>{gScore}</span>
          <span style={slashStyle}>/100</span>
        </span>
      </div>

      {/* Total */}
      <div style={cardStyle}>
        <div style={circleStyle}>
          <span style={letterStyle("#FAD320")}>T</span>
        </div>
        <span style={{ color: "#FAD320" }}>
          <span style={numericScoreStyle}>{totalScore}</span>
          <span style={slashStyle}>/100</span>
        </span>
      </div>
    </div>
  );
};

export default ESGScoreCard;
