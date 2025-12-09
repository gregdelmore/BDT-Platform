from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BDT Platform", version="STABLE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database config with CORRECT username
DB_STATUS = "Not Connected"
try:
    import psycopg2
    # Try connection with correct username: btadmin
    conn = psycopg2.connect(
        host="bdt-platform-db.postgres.database.azure.com",
        database="postgres",
        user="btadmin",  # CORRECT username from Azure portal
        password="PumpkinPi14$",
        sslmode="require"
    )
    conn.close()
    DB_STATUS = "Connected"
    logger.info("Database connected")
except:
    DB_STATUS = "Not Connected (Demo Mode)"
    logger.info("Running in demo mode")

# Tyler's demo data
tyler_data = {
    "emails": [
        {"subject": "Customer Portal Migration", "from": "manager@airiam.com"},
        {"subject": "API Documentation", "from": "tyler.helwig@airiam.com"}
    ],
    "files": [
        {"name": "Architecture.pptx", "modified": "2024-11-28"},
        {"name": "API_Docs.docx", "modified": "2024-11-27"}
    ]
}

@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("dashboard.html", "r") as f:
            return f.read()
    except:
        # Fallback HTML
        return f"""
        <html>
        <body>
            <h1>BDT Platform</h1>
            <p>Database: {DB_STATUS}</p>
            <p>Tyler: tyler.helwig@airiam.com</p>
            <ul>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/tyler/sync">Sync Tyler Data</a></li>
            </ul>
        </body>
        </html>
        """

@app.get("/health")
async def health():
    return {"status": "healthy", "database": DB_STATUS}

@app.post("/api/tyler/sync")
async def sync_tyler(request: dict = {}):
    return {
        "emails": len(tyler_data["emails"]),
        "files": len(tyler_data["files"]),
        "status": "success"
    }

@app.post("/api/chat")
async def chat(request: dict):
    question = request.get("question", "")
    return {"answer": f"Searching for: {question} (Demo Mode)"}
