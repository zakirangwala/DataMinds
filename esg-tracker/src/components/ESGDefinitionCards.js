import React from "react";

const ESGDefinitionCards = () => {
  return (
    <div style={{ display: "flex", gap: "1rem" }}>
      {/* Environmental Card */}
      <div
        style={{
          backgroundColor: "#2D2F30",
          padding: "1.5rem",
          borderRadius: "8px",
          width: "33%",
          display: "flex",
          flexDirection: "column",
          alignItems: "start",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "50%",
            backgroundColor: "black",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "10px",
          }}
        >
          <span style={{ color: "green", fontSize: "20px", fontWeight: "bold" }}>E</span>
        </div>
        <h3 style={{ color: "#fff", fontWeight: "bold" }}>Environmental</h3>
        <p style={{ color: "#ccc" }}>
          Evaluates how a company affects the environment, including carbon emissions, renewable energy use, 
          water conservation, waste management, and climate risk strategies.
        </p>
      </div>

      {/* Social Card */}
      <div
        style={{
          backgroundColor: "#2D2F30",
          padding: "1.5rem",
          borderRadius: "8px",
          width: "33%",
          display: "flex",
          flexDirection: "column",
          alignItems: "start",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "50%",
            backgroundColor: "black",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "10px",
          }}
        >
          <span style={{ color: "blue", fontSize: "20px", fontWeight: "bold" }}>S</span>
        </div>
        <h3 style={{ color: "#fff", fontWeight: "bold" }}>Social</h3>
        <p style={{ color: "#ccc" }}>
          Examines how a company interacts with employees, customers, and communities, focusing on fair labor 
          practices, diversity, human rights, social responsibility, and product safety.
        </p>
      </div>

      {/* Governance Card */}
      <div
        style={{
          backgroundColor: "#2D2F30",
          padding: "1.5rem",
          borderRadius: "8px",
          width: "33%",
          display: "flex",
          flexDirection: "column",
          alignItems: "start",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "50%",
            backgroundColor: "black",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "10px",
          }}
        >
          <span style={{ color: "purple", fontSize: "20px", fontWeight: "bold" }}>G</span>
        </div>
        <h3 style={{ color: "#fff", fontWeight: "bold" }}>Governance</h3>
        <p style={{ color: "#ccc" }}>
          Assesses the integrity and accountability of a company's leadership, including board diversity, 
          executive pay, transparency, regulatory compliance, and ethical business practices.
        </p>
      </div>
    </div>
  );
};

export default ESGDefinitionCards;
