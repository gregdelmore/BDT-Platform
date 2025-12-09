import psycopg2
import sys

# Try different connection strings
connections_to_try = [
    {
        "name": "With .postgres",
        "string": "host=bdt-platform-db.postgres.database.azure.com dbname=bdtplatform user=bdtadmin password=PumpkinPi14$ sslmode=require"
    },
    {
        "name": "Without .postgres", 
        "string": "host=bdt-platform-db.database.azure.com dbname=bdtplatform user=bdtadmin password=PumpkinPi14$ sslmode=require"
    },
    {
        "name": "With postgres DB",
        "string": "host=bdt-platform-db.postgres.database.azure.com dbname=postgres user=bdtadmin password=PumpkinPi14$ sslmode=require"
    }
]

for conn_info in connections_to_try:
    print(f"\nTrying: {conn_info['name']}")
    print(f"Connection: {conn_info['string'][:50]}...")
    try:
        conn = psycopg2.connect(conn_info['string'])
        print(f" SUCCESS with {conn_info['name']}!")
        cur = conn.cursor()
        cur.execute("SELECT current_database()")
        db = cur.fetchone()
        print(f"   Connected to database: {db[0]}")
        cur.close()
        conn.close()
        break
    except Exception as e:
        print(f" Failed: {str(e)[:100]}")
