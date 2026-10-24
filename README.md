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

**Backend:
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
- Python 3.10+
- An API key from [NewsAPI.org](https://newsapi.org/)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Atul-1408/stock.git
   cd stock
   ```

2. **Backend Setup:**
   - Create a virtual environment and attach it:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\\Scripts\\activate
     ```
   - Install required packages:
     ```bash
     pip install -r requirements.txt  # (if applicable, or install via pyproject.toml)
     ```
   - Configure Environment Variables:
     Copy the `.env.example` file to `.env` and provide your keys:
     ```bash
     cp .env.example .env
     ```
     Edit `.env` to add your `NEWS_API_KEY`.

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

1. **Start the Backend:**
   ```bash
   # From the project root with your virtualenv activated
   python src/app.py
   ```
   The API should start on `http://localhost:5000` (or the port defined in `app.py`).

2. **Start the Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```
   The React application will be accessible at `http://localhost:5173`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
