# Stock Sentiment Dashboard and Trading Bot

A comprehensive full-stack application for monitoring stock market assets, analyzing sentiment from news sources, and simulating automated trading strategies. The project features a modern React frontend and a robust Python backend with SQLite.

## Overview

This application provides real-time and historical insights into stock market data, coupled with a sentiment analysis engine that processes news headlines to gauge market moods. An integrated trading bot can be configured to execute trades based on these sentiment scores and other technical indicators.

### Key Features
- **Interactive Dashboard:** View live ticker tapes, price charts, and portfolio performance metrics.
- **Sentiment Analysis:** Fetch and score recent news articles corresponding to tracked stocks.
- **Automated Trading Bot:** A customizable trading engine that simulates buys and sells based on customizable risk and sentiment thresholds.
- **Secure Authentication:** User accounts are protected using JWT and optional OTP verification.
- **AI Chatbot Assistant:** Ask questions about market data and get insights powered by LLM interactions.

## Technology Stack

**Frontend:**
- [React 19](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Chart.js](https://www.chartjs.org/) & react-chartjs-2 for data visualization
- [Framer Motion](https://www.framer.com/motion/) for animations

**Backend:**
- Python 3.10+
- Flask (API serving)
- SQLite3 (Database management)
- External Integrations (News API, Market Data APIs)

## Project Structure

```text
stock/
├── data/               # SQLite database files
├── frontend/           # React frontend application
│   ├── src/            # React components, pages, and assets
│   ├── package.json    # Frontend dependencies
│   └── vite.config.js  # Vite bundler configuration
├── src/                # Python backend application
│   ├── app.py          # Main Flask application entry point
│   ├── database.py     # Database schemas and operations
│   ├── trading_bot/    # Automated trading bot logic
│   └── ...             # Core logic modules (sentiment, analytics, etc.)
├── check_db.py         # Utility script for database inspection
├── verify_all.py       # Utility script to test major endpoints
├── training_data.csv   # Historical data for testing/training models
└── .env.example        # Environment variable template
```

## Getting Started

### Prerequisites
- Node.js (v18 or higher)
- Python 3.11 or 3.12 recommended (3.10+ supported; see `.python-version`)
- API Keys:
  - [NewsAPI.org](https://newsapi.org/) (`NEWS_API_KEY`)
  - [Finnhub.io](https://finnhub.io/) (`FINNHUB_API_KEY`)
  - [Google AI Studio](https://aistudio.google.com/) (`GEMINI_API_KEY`)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Atul-1408/stock.git
   cd stock
   ```

2. **Backend Setup:**
   - Create a virtual environment:
     ```bash
     python -m venv venv
     ```
   - Activate the virtual environment:
     - **Windows PowerShell:**
       ```powershell
       .\venv\Scripts\Activate.ps1
       # If execution policy blocks script: Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
       ```
     - **Windows CMD:**
       ```cmd
       venv\Scripts\activate.bat
       ```
     - **Linux / macOS:**
       ```bash
       source venv/bin/activate
       ```
   - Install required dependencies:
     ```bash
     pip install -r requirements.txt
     # optional, large: FinBERT sentiment
     pip install -r requirements-ml.txt
     ```
   - Configure Environment Variables:
     ```bash
     cp .env.example .env
     ```
     Open `.env` and set your `JWT_SECRET_KEY`, `NEWS_API_KEY`, `FINNHUB_API_KEY`, and `GEMINI_API_KEY`.
   - Windows Console Unicode Support (Optional but recommended):
     ```powershell
     $env:PYTHONUTF8=1
     ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

1. **Start the Backend (Terminal 1):**
   ```bash
   # From the project root with your virtual environment active
   python src/app.py
   ```
   The API will listen on `http://127.0.0.1:5000` (or configured port).

2. **Start the Frontend (Terminal 2):**
   ```bash
   cd frontend
   npm run dev
   ```
   The institutional trading dashboard will be available at `http://127.0.0.1:5173/dashboard`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Tests & Quality

```bash
python -m pytest tests -q        # backend + frontend/backend route contract
python endpoint_audit.py         # 0 server errors expected on malformed input
cd frontend && npm run build     # production build
```

## Safety

Paper trading is the default. Live trading needs both `TRADING_MODE=LIVE` and `ALLOW_LIVE_TRADING=true`.
Nothing in this project is financial advice.

## Docker

```bash
docker compose up --build        # app on http://localhost:5000
```
