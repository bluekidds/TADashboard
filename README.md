# TADashboard

## Local setup

1. Copy the example environment file and update values as needed:
   ```bash
   cp .env.example .env
   ```
2. Start the database services:
   ```bash
   docker compose up -d
   ```
3. Initialize Postgres and Neo4j schemas:
   ```bash
   python backend/app/db/init_db.py
   ```
