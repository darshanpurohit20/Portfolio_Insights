# Portfolio Insights 📈

A sophisticated wealth management dashboard designed to provide real-time insights into your NSE (National Stock Exchange) investments. Features advanced visualization, live tracking, and smart portfolio management.

## ✨ Key Features

- **Real-time Portfolio Tracking**: Live updates for NSE stocks using Yahoo Finance integration.
- **Visual Analytics**: Interactive sparklines and performance charts for a quick overview of your assets.
- **Smart Portfolio Management**: Effortlessly add, track, and manage your stock holdings.
- **Smart OCR Import (Coming Soon)**: Upload screenshots of your broker portfolio (Zerodha, Groww, etc.) and let AI extract your holdings automatically.
- **Mobile Responsive**: Access your portfolio insights from any device.

## 🚀 Tech Stack

- **Framework**: [Next.js 14](https://nextjs.org/) (App Router)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **UI Components**: [Radix UI](https://www.radix-ui.com/) & [shadcn/ui](https://ui.shadcn.com/)
- **Charts**: [Recharts](https://recharts.org/)
- **AI/OCR**: [Groq AI](https://groq.com/) for intelligent extraction
- **Language**: [TypeScript](https://www.typescript.org/)

## 🛠️ Getting Started

### Prerequisites

- Node.js 18+ 
- pnpm (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/portfolio-insights.git
   cd portfolio-insights
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Set up environment variables:
   Create a `.env.local` file in the root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. Run the development server:
   ```bash
   pnpm dev
   ```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## 📁 Project Structure

```text
app/          # Next.js App Router (Pages & API)
components/   # Reusable UI & Feature components
hooks/        # Custom React hooks
lib/          # Utilities, Auth, and Data logic
public/       # Static assets
styles/       # Global CSS
```

## 🪜 Roadmap

- [ ] AI-Powered Portfolio OCR Extraction
- [ ] Multi-broker import support
- [ ] Export to PDF/CSV reports
- [ ] Real-time price alerts (Desktop/Mobile)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
