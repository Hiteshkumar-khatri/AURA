
## Completed Phases

- [x] Phase 0 — Project architecture and setup
- [x] Phase 1 — Data ingestion and profiling (1.55M rows analyzed)
- [x] Phase 2 — Data quality engine with 0-100 scoring
- [x] Phase 3 — Analytics engine, KPI calculator, anomaly detection
- [x] Phase 4 — ML pipeline (K-Means RFM customer segmentation)
- [x] Phase 5 — Apache Superset BI dashboard
- [x] Phase 6 — FastAPI web interface with AI analyst
- [x] Phase 7 — Professional dark UI with sidebar navigation

## Remaining

- [ ] Deploy to Render + Supabase (public URL)
- [ ] Natural language root-cause analysis
- [ ] PDF report generation
- [ ] Continuous monitoring and alerts

## Setup

```bash
# Clone the repository
git clone https://github.com/Hiteshkumar-khatri/AURA.git
cd AURA

# Start database services
docker compose up -d

# Install Python dependencies
pip install fastapi uvicorn pandas psycopg2-binary scikit-learn scipy python-multipart openpyxl python-dotenv requests

# Create .env file
cp .env.example .env
# Add your OpenRouter API key to .env

# Run the web application
cd python/api
python -m uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000` to start analyzing data.

## Dataset

Built and tested on the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100,000 orders across 9 related tables.

## License

MIT
