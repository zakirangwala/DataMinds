// src/components/NewsCard.js
import React from "react";

/**
 * Converts a string like "2024-12-23 15:47:57" into:
 * { formattedDate: "Dec 23, 2024", formattedTime: "3:47 PM" }
 */
function formatDateTime(dateString) {
  // 1) Split into [datePart, timePart], e.g. ["2024-12-23", "15:47:57"]
  const [datePart, timePart] = dateString.split(" ");
  if (!datePart || !timePart) {
    return { formattedDate: "Invalid Date", formattedTime: "" };
  }

  // 2) Split datePart into [year, month, day]
  const [year, month, day] = datePart.split("-");

  // 3) Split timePart into [hour, minute, second]
  const [hour, minute, second] = timePart.split(":");

  // 4) Create a JavaScript Date object -> month is zero-indexed
  const dateObj = new Date(year, month - 1, day, hour, minute, second);
  if (isNaN(dateObj.getTime())) {
    return { formattedDate: "Invalid Date", formattedTime: "" };
  }

  // 5) Format date as "Dec 23, 2024"
  const dateOptions = { month: "short", day: "numeric", year: "numeric" };
  const formattedDate = dateObj.toLocaleDateString("en-US", dateOptions);

  // 6) Format time as "3:47 PM" (12-hour clock)
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
}) => {
  const { formattedDate, formattedTime } = formatDateTime(articlePublished);

  // Truncate article text to 77 characters
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
        borderRadius: "8px",
        backgroundColor: "#1B1D1E",
        cursor: "pointer",
        position: "relative",
        boxShadow: "0 4px 10px rgba(0, 0, 0, 0.2)",
      }}
    >
      {/* Background Image */}
      <div
        style={{
          backgroundImage: `url(${encodeURI(articleTopImage)})`,
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
      
      {/* Content Overlay */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          color: "#fff",
          padding: "1rem",
        }}
      >
        {/* Title & Snippet at the top */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
          }}
        >
          <h4 style={{ margin: "0 0 0.25rem 0", fontSize: "16px" }}>
            {articleTitle}
          </h4>
          <p
            style={{
              margin: "0 0 0.5rem 0",
              fontSize: "12px",
              lineHeight: "1.4",
            }}
          >
            {snippet}
          </p>
        </div>
        
        {/* Date (bottom-left) and Time (bottom-right) */}
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: "12px" }}>{formattedDate}</span>
          <span style={{ fontSize: "12px" }}>{formattedTime}</span>
        </div>
      </div>
    </div>
  );
};

export default NewsCard;
