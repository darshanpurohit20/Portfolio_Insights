# Portfolio Insights 📈

A sophisticated wealth management dashboard designed to provide real-time insights into your NSE (National Stock Exchange) investments. Features advanced visualization, live tracking, and smart portfolio management.

## ✨ Key Features

- **Real-time Portfolio Tracking**: Live updates for NSE stocks using Yahoo Finance integration.
- **Visual Analytics**: Interactive sparklines and performance charts for a quick overview of your assets.
- **Smart Portfolio Management**: Effortlessly add, track, and manage your stock holdings.
- **Smart OCR Import (Coming Soon)**: Upload screenshots of your broker portfolio (Zerodha, Groww, etc.) and let AI extract your holdings automatically.
- **Mobile Responsive**: Access your portfolio insights from any device.

## 🚀 Tech Stack

- **Frontend**: [Next.js 14](https://nextjs.org/) (App Router), [TypeScript](https://www.typescript.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/), [Radix UI](https://www.radix-ui.com/), [shadcn/ui](https://ui.shadcn.com/)
- **Backend**: Python, [FastAPI](https://fastapi.tiangolo.com/), [yfinance](https://github.com/ranaroussi/yfinance)
- **Charts**: [Recharts](https://recharts.org/)
- **AI/OCR**: [Groq AI](https://groq.com/) for intelligent extraction

## 🛠️ Getting Started

### Prerequisites

- **Node.js**: 18+ and `pnpm` (recommended)
- **Python**: 3.9+ for the backend

### 1. Setup Environment Variables

The project uses environment variables for both the frontend and backend connection.

1. Copy the template:
   ```bash
   cp .env.example .env.local
   ```
2. Open `.env.local` and add your keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   NEXT_PUBLIC_BACKEND_URL=http://localhost:7860
   ```
   > [!TIP]
   > Use `http://localhost:7860` for local development. If you've deployed the backend, use its URL (e.g., `https://your-backend.hf.space`).

### 2. Frontend Installation

1. Install dependencies:
   ```bash
   pnpm install
   ```
2. Run the development server:
   ```bash
   pnpm dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to see the dashboard.

### 3. Backend Setup

The backend fetches live stock data from the NSE. To run it locally:

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 7860
   ```
   The backend will run on [http://localhost:7860](http://localhost:7860).

## 📁 Project Structure

```text
app/          # Next.js App Router (Pages & API)
backend/      # Python FastAPI Backend
components/   # Reusable UI & Feature components
hooks/        # Custom React hooks
lib/          # Utilities, Auth, and Data logic
public/       # Static assets
styles/       # Global CSS
```

## 🏗️ Deployment

- **Frontend**: Best deployed on [Vercel](https://vercel.com).
- **Backend**: Containerized and ready for [Hugging Face Spaces](https://huggingface.co/spaces) or any Docker-compatible host.

## 🪜 Roadmap

- [ ] AI-Powered Portfolio OCR Extraction
- [ ] Multi-broker import support
- [ ] Export to PDF/CSV reports
- [ ] Real-time price alerts (Desktop/Mobile)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
