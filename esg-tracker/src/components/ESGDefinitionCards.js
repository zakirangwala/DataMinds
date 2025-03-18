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
            width: "80px",
            height: "80px",
            borderRadius: "50%",
            backgroundColor: "#1C1C1C",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "10px",
          }}
        >
          <span style={{ color: "#48EB6C", fontSize: "55px", fontWeight: "bold" }}>E</span>
        </div>
        <h3 style={{ color: "#fff", fontWeight: "bold", margin: 0 }}>Environmental</h3>
        <p style={{ color: "#fff", margin: 0 }}>
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
            width: "80px",
            height: "80px",
            borderRadius: "50%",
            backgroundColor: "#1C1C1C",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "10px",
          }}
        >
          <span style={{ color: "#2BC6FF", fontSize: "55px", fontWeight: "bold" }}>S</span>
        </div>
        <h3 style={{ color: "#fff", fontWeight: "bold", margin: 0 }}>Social</h3>
        <p style={{ color: "#fff", margin: 0 }}>
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
            width: "80px",
            height: "80px",
            borderRadius: "50%",
            backgroundColor: "#1C1C1C",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "10px",
          }}
        >
          <span style={{ color: "#AD6CDE", fontSize: "55px", fontWeight: "bold" }}>G</span>
        </div>
        <h3 style={{ color: "#fff", fontWeight: "bold", margin: 0 }}>Governance</h3>
        <p style={{ color: "#fff", margin: 0 }}>
          Assesses the integrity and accountability of a company's leadership, including board diversity, 
          executive pay, transparency, regulatory compliance, and ethical business practices.
        </p>
      </div>
    </div>
  );
};

export default ESGDefinitionCards;
