from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import psycopg2
import traceback

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    results = []
    
    # Test different configurations
    tests = [
        ("bdtplatform", "bdtadmin"),
        ("postgres", "bdtadmin"),
        ("bdtplatform", "btadmin")
    ]
    
    for db_name, username in tests:
        try:
            conn_str = f"host=bdt-platform-db.postgres.database.azure.com dbname={db_name} user={username} password=PumpkinPi14$ sslmode=require connect_timeout=10"
            results.append(f"<li>Trying database='{db_name}', user='{username}'...</li>")
            
            conn = psycopg2.connect(conn_str)
            cur = conn.cursor()
            cur.execute("SELECT current_database(), current_user")
            db, user = cur.fetchone()
            results.append(f"<li style='color:green'> SUCCESS! Connected to '{db}' as '{user}'</li>")
            
            # Check if bdtplatform database exists
            cur.execute("SELECT datname FROM pg_database WHERE datname = 'bdtplatform'")
            if cur.fetchone():
                results.append(f"<li style='color:green'> Database 'bdtplatform' EXISTS</li>")
            else:
                results.append(f"<li style='color:orange'> Database 'bdtplatform' does NOT exist - need to create it</li>")
            
            cur.close()
            conn.close()
            break
            
        except Exception as e:
            error = str(e).replace("password", "***")
            results.append(f"<li style='color:red'> Failed: {error}</li>")
    
    return f"""
    <html>
    <body>
        <h1>SQL Connection Test</h1>
        <ul>
            {''.join(results)}
        </ul>
        <hr>
        <p>If all failed, the issue is likely firewall rules blocking Azure services.</p>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    return {"status": "testing"}
