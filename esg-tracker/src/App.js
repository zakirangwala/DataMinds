import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import CompanyDetail from "./pages/CompanyDetail";

function App() {
  return (
    <Router>
      <Routes>
        {/* Home page */}
        <Route path="/" element={<Home />} />
        {/* Detail page, accessed via /company/:slug */}
        <Route path="/company/:ticker" element={<CompanyDetail />} />
      </Routes>
    </Router>
  );
}

export default App;
