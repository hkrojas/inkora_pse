@echo off
echo ========================================================
echo Iniciando Ecosistema Inkora B2B SaaS
echo ========================================================

:: Iniciar FastAPI Backend en un nuevo proceso cmd
start "Inkora - Backend (FastAPI)" cmd /c "cd backend && call venv\Scripts\activate.bat && uvicorn main:app --reload --host 127.0.0.1 --port 8000"

:: Iniciar Worker de emision en un nuevo proceso cmd
start "Inkora - Worker (Emision)" cmd /c "cd backend && call venv\Scripts\activate.bat && python run_emission_worker.py"

:: Iniciar React Vite Frontend en un nuevo proceso cmd
start "Inkora - Frontend (React)" cmd /c "cd frontend && npm run dev"

echo [OK] Ecosistema Local Desplegado.
echo Accede al frontend en http://localhost:5173
echo Accede a la documentacion API en http://localhost:8000/docs
echo ========================================================
pause
