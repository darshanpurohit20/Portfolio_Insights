# Portfolio Insights 📈

A high-performance wealth management dashboard providing real-time insights into your NSE (National Stock Exchange) investments. Features sub-second latency, advanced diversification analytics, and seamless portfolio management.

## ✨ Key Features

- **Blazing Fast Performance**: Hybrid bulk-index strategy retrieves up to 500 stocks in sub-200ms using parallel processing.
- **Portfolio Diversification Charts**: Interactive Pie Charts for viewing allocation by **Stock**, **Sector**, and **Market Cap** (Large, Mid, Small Cap).
- **Advanced Metadata**: Automatic classification of **ETFs and Mutual Funds** with live industry metadata from NSE.
- **Editable Portfolio**: Modify your holdings (quantity and buy price) directly from the dashboard with instant P&L recalculation.
- **Real-time Tracking**: Live price updates and interactive sparklines for every holding.
- **Smart OCR Import**: (In-Progress) AI-powered extraction from broker screenshots using Groq.

## 📸 Screenshots

<div align="center">

<div style="border:1px solid #ddd; border-radius:10px; padding:10px; margin:20px; width:80%;">
  <h3>📊 Dashboard Overview</h3>
  <img src="https://github.com/user-attachments/assets/4cc469fd-4630-40e4-b276-b16a8b7b4c4b" width="100%" />
</div>

<div style="border:1px solid #ddd; border-radius:10px; padding:10px; margin:20px; width:80%;">
  <h3>📈 Portfolio Allocation</h3>
  <img src="https://github.com/user-attachments/assets/ff46bb4d-bba7-49ae-935f-41802f996b05" width="100%" />
  <img width="1470" height="846" alt="image" src="https://github.com/user-attachments/assets/1d652ed2-d3a8-4e17-b1bd-5e3f7ed9873c" />

</div>

<div style="border:1px solid #ddd; border-radius:10px; padding:10px; margin:20px; width:80%;">
  <h3>🔍 Stock Cards & Search</h3>
  <img src="https://github.com/user-attachments/assets/546301fc-9437-4241-b4b2-8d1599cfe0ed" width="100%" />
</div>

<div style="border:1px solid #ddd; border-radius:10px; padding:10px; margin:20px; width:80%;">
  <h3>📉 Performance Sparklines</h3>
  <img src="https://github.com/user-attachments/assets/7da46d91-19a7-4874-b697-e545eda8a3ff" width="100%" />
</div>

</div>

## 🚀 Tech Stack

- **Frontend**: [Next.js 14](https://nextjs.org/) (App Router), [TypeScript](https://www.typescript.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Charts**: [Recharts](https://recharts.org/) for high-performance visualizations.
- **Backend**: Python 3.9+, [FastAPI](https://fastapi.tiangolo.com/), [nsepython](https://github.com/aero31aero/nsepython)
- **Concurrency**: `ThreadPoolExecutor` (50 workers) for parallel data fetching.
- **AI/OCR**: [Groq AI](https://groq.com/) (Llama-3)

## 🛠️ Getting Started

### Prerequisites

- **Node.js**: 18+ and `npm` or `pnpm`
- **Python**: 3.9+

### 1. Setup Environment Variables

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
2. Add your keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   NEXT_PUBLIC_BACKEND_URL=http://localhost:7860
   ```

### 2. Frontend Installation

1. Install dependencies:
   ```bash
   npm install
   ```
2. Run the development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000).

### 3. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the backend server:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 7860
   ```

## 📁 Project Structure

```text
app/          # Next.js App Router (Pages & API)
backend/      # Python FastAPI Optimized Backend
components/   # Dashboard, Charts, and Table components
lib/          # Types, Utilities, and Auth logic
```

## 🪜 Roadmap

- [x] High-performance Parallel Backend
- [x] Portfolio Diversification Charts (Sector/Cap)
- [x] Editable Holdings Management
- [/] AI-Powered Portfolio OCR Extraction
- [ ] Multi-broker import support
- [ ] Export to PDF/CSV reports

## 📄 License

MIT License.
