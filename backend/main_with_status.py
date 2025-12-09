from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test database connection
DB_STATUS = {"connected": False, "message": "Not tested"}
try:
    import psycopg2
    conn = psycopg2.connect(
        host="bdt-platform-db.postgres.database.azure.com",
        database="postgres",
        user="btadmin",  # Correct username
        password="PumpkinPi14$",
        sslmode="require"
    )
    conn.close()
    DB_STATUS = {"connected": True, "message": "PostgreSQL Connected"}
except Exception as e:
    DB_STATUS = {"connected": False, "message": str(e)[:100]}

@app.get("/", response_class=HTMLResponse)
async def root():
    # Keep your existing dashboard
    with open("dashboard.html", "r") as f:
        content = f.read()
        # Add a small status div at the top
        status_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; padding: 10px; background: {'#d4edda' if DB_STATUS['connected'] else '#f8d7da'}; border-radius: 5px; z-index: 1000;">
            Database: {' Connected' if DB_STATUS['connected'] else ' Not Connected'}
        </div>
        """
        content = content.replace("<body>", f"<body>{status_html}")
        return content

@app.get("/health")
async def health():
    return DB_STATUS

@app.get("/api/database-status")
async def database_status():
    return DB_STATUS

# Keep all your existing endpoints
@app.post("/api/tyler/sync")
async def sync_tyler(request: dict = {}):
    return {"emails": 3, "files": 2}

@app.post("/api/chat")
async def chat(request: dict):
    return {"answer": "Demo response"}
