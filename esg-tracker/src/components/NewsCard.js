// src/components/NewsCard.js
import React from "react";

/**
 * Converts a string like "2024-12-23 15:47:57" into:
 * { formattedDate: "Dec 23, 2024", formattedTime: "3:47 PM" }
 */
function formatDateTime(dateString) {
  if (!dateString) return { formattedDate: "Invalid Date", formattedTime: "" };
  
  const [datePart, timePart] = dateString.split(" ");
  if (!datePart || !timePart) {
    return { formattedDate: "Invalid Date", formattedTime: "" };
  }

  const [year, month, day] = datePart.split("-");
  const [hour, minute, second] = timePart.split(":");

  const dateObj = new Date(year, month - 1, day, hour, minute, second);
  if (isNaN(dateObj.getTime())) {
    return { formattedDate: "Invalid Date", formattedTime: "" };
  }

  const dateOptions = { month: "short", day: "numeric", year: "numeric" };
  const formattedDate = dateObj.toLocaleDateString("en-US", dateOptions);

  const timeOptions = { hour: "numeric", minute: "2-digit" };
  const formattedTime = dateObj.toLocaleTimeString("en-US", timeOptions);

  return { formattedDate, formattedTime };
}

const NewsCard = ({
  articleTitle,
  articleText,
  articleResolvedUrl,
  articleTopImage,
  articlePublished,
  searchSourceTitle, // Fallback if date isn't available
}) => {
  const { formattedDate, formattedTime } = formatDateTime(articlePublished);
  const isValidDate = articlePublished && formattedDate !== "Invalid Date";
  const topImage = articleTopImage ? articleTopImage : "https://imgur.com/wynmV0s.jpg";
  
  const snippetLength = 77;
  const snippet =
    articleText.length > snippetLength
      ? articleText.substring(0, snippetLength) + "..."
      : articleText;

  const handleClick = () => {
    window.open(articleResolvedUrl, "_blank");
  };

  return (
    <div
      onClick={handleClick}
      style={{
        width: "280px",
        height: "320px",
        borderRadius: "3rem",
        backgroundColor: "#1B1D1E",
        cursor: "pointer",
        position: "relative",
        boxShadow: "0 4px 10px rgba(0, 0, 0, 0.2)",
      }}
    >
      {/* Background Image */}
      <div
        style={{
          backgroundImage: `url("${topImage}")`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          width: "100%",
          height: "100%",
          filter: "brightness(0.5)",
          position: "absolute",
          top: 0,
          left: 0,
        }}
      />

      {/* Bottom Overlay Container */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          padding: "1rem",
          backgroundColor: "rgba(0, 0, 0, 0.6)",
          color: "#fff",
          boxSizing: "border-box",
        }}
      >
        <h4 style={{ margin: "0 0 0.25rem 0", fontSize: "16px" }}>
          {articleTitle}
        </h4>
        <p style={{ margin: "0 0 0.5rem 0", fontSize: "12px", lineHeight: "1.4" }}>
          {snippet}
        </p>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: "12px" }}>
            {isValidDate ? formattedDate : searchSourceTitle}
          </span>
          <span style={{ fontSize: "12px" }}>
            {isValidDate ? formattedTime : ""}
          </span>
        </div>
      </div>
    </div>
  );
};

export default NewsCard;
