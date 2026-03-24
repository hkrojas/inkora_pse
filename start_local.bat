@echo off
echo ========================================================
echo Iniciando Ecosistema PrintFlow B2B SaaS
echo ========================================================

:: Iniciar FastAPI Backend en un nuevo proceso cmd
start "PrintFlow - Backend (FastAPI)" cmd /c "cd backend && call venv\Scripts\activate.bat && uvicorn main:app --reload --host 127.0.0.1 --port 8000"

:: Iniciar React Vite Frontend en un nuevo proceso cmd
start "PrintFlow - Frontend (React)" cmd /c "cd frontend && npm run dev"

echo [OK] Ecosistema Local Desplegado.
echo Accede al frontend en http://localhost:5173
echo Accede a la documentacion API en http://localhost:8000/docs
echo ========================================================
pause
