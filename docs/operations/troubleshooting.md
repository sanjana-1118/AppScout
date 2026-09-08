# AppScout Troubleshooting Guide

This guide covers common operational, development, and network issues encountered when running AppScout, along with concrete solutions.

---

## 1. Database Issues

### 1.1 "Connection Refused" or Cannot Connect to PostgreSQL
* **Symptom**: `OperationalError: connection to server at "localhost", port 5432 failed: Connection refused`.
* **Causes**:
  * Local PostgreSQL service is not running.
  * `DATABASE_URL` in `.env` has an incorrect host, port, username, or password.
* **Solutions**:
  1. Verify PostgreSQL service status:
     ```bash
     # Windows (PowerShell)
     Get-Service -Name postgresql*
     
     # Linux
     sudo systemctl status postgresql
     ```
  2. Verify your `.env` connection string:
     ```ini
     DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/appscout
     ```
  3. If using Neon Cloud PostgreSQL, ensure your connection string includes SSL mode:
     ```ini
     DATABASE_URL=postgresql+psycopg://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

### 1.2 "QueuePool limit of size 20 overflow 30 reached"
* **Symptom**: `TimeoutError: QueuePool limit of size 20 overflow 30 reached, connection timed out`.
* **Causes**: High concurrent queries exhaust pooled connections without releasing them.
* **Solutions**:
  * Ensure every route uses the `get_db_session` dependency (which automatically closes sessions upon route completion).
  * Increase pool settings in `.env`:
     ```ini
     DB_POOL_SIZE=30
     DB_MAX_OVERFLOW=50
     DB_POOL_TIMEOUT=45
     ```

---

## 2. Backend Startup Issues

### 2.1 "ModuleNotFoundError: No module named 'backend'" or "'experiment'"
* **Symptom**: Running scripts fails with `ModuleNotFoundError`.
* **Causes**: Python cannot locate the root workspace in its `sys.path`.
* **Solutions**:
  * Execute commands from the repository root:
     ```bash
     # Ensure virtual environment is activated
     .venv\Scripts\Activate.ps1
     
     # Run module directly
     python -m backend.main
     ```

### 2.2 "Port 8000 is already in use"
* **Symptom**: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`.
* **Causes**: A previous Uvicorn or Python process is still occupying port 8000.
* **Solutions**:
  ```powershell
  # Find process occupying port 8000
  Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess
  
  # Terminate process by PID
  Stop-Process -Id <PID> -Force
  ```

---

## 3. Frontend & API Connection Issues

### 3.1 Network Error / Failed to Fetch on Frontend
* **Symptom**: Views display `"Could not connect to backend"` or API requests fail in browser console.
* **Causes**:
  * Backend server is not running on port 8000.
  * Cross-Origin Resource Sharing (CORS) is blocking requests.
* **Solutions**:
  1. Confirm the backend responds:
     ```bash
     curl http://127.0.0.1:8000/api/overview
     ```
  2. Check `CORS_ORIGINS` in root `.env`:
     ```ini
     CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
     ```
  3. If hosting the frontend on a different port or remote domain, specify `VITE_API_URL` in `frontend/.env`:
     ```ini
     VITE_API_URL=http://127.0.0.1:8000/api
     ```

### 3.2 "Vite dev server proxy error: ECONNREFUSED"
* **Symptom**: Terminal shows `[vite] http proxy error at /api/overview: AggregateError [ECONNREFUSED]`.
* **Causes**: Vite is trying to proxy `/api` calls to `127.0.0.1:8000`, but FastAPI is offline.
* **Solutions**:
  * Start the FastAPI backend before launching the Vite dev server.

---

## 4. Build & Typecheck Issues

### 4.1 TypeScript Errors During `npm run build`
* **Symptom**: `tsc -b` fails with compiler errors.
* **Solutions**:
  * Run `npx tsc --noEmit` to locate type mismatches.
  * Ensure imports match current interface definitions in [`frontend/src/types.ts`](file:///c:/Sanjana/Spryntworks/Projects/AppScout/frontend/src/types.ts).
  * Run `npm run lint` with Oxlint to catch hook or syntax issues.
