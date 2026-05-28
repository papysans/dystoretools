@echo off
setlocal EnableExtensions

if /I "%~1"=="--help" goto help
if /I "%~1"=="-h" goto help

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%" >nul

set "MYSQL_CONTAINER=dystoretools-mysql-dev"
set "REDIS_CONTAINER=dystoretools-redis-dev"
set "MYSQL_HOST=127.0.0.1"
set "MYSQL_PORT=3307"
set "MYSQL_USER=dystore"
set "MYSQL_PASSWORD=changeme_dystore"
set "MYSQL_DATABASE=dystore"
set "MYSQL_ROOT_PASSWORD=changeme_root"
set "REDIS_HOST=127.0.0.1"
set "REDIS_PORT=6387"
set "REDIS_DB=0"
set "PLAYWRIGHT_USER_DATA_DIR=../.playwright-dev"

echo [1/6] Checking tools...
where docker >nul 2>nul || goto missing_docker
where python >nul 2>nul || goto missing_python
where pnpm >nul 2>nul || goto missing_pnpm
where uvicorn >nul 2>nul || goto missing_uvicorn
where alembic >nul 2>nul || goto missing_alembic

echo [2/6] Starting MySQL and Redis dev containers...
docker inspect "%MYSQL_CONTAINER%" >nul 2>nul
if errorlevel 1 (
  echo Creating %MYSQL_CONTAINER% on 127.0.0.1:%MYSQL_PORT%...
  docker run -d --name "%MYSQL_CONTAINER%" ^
    -e MYSQL_ROOT_PASSWORD=%MYSQL_ROOT_PASSWORD% ^
    -e MYSQL_DATABASE=%MYSQL_DATABASE% ^
    -e MYSQL_USER=%MYSQL_USER% ^
    -e MYSQL_PASSWORD=%MYSQL_PASSWORD% ^
    -e TZ=Asia/Shanghai ^
    -p 127.0.0.1:%MYSQL_PORT%:3306 ^
    mysql:8.0 ^
    --character-set-server=utf8mb4 ^
    --collation-server=utf8mb4_0900_ai_ci ^
    --default-time-zone=+08:00 ^
    --max_allowed_packet=64M || goto failed
) else (
  docker start "%MYSQL_CONTAINER%" >nul || goto failed
)

docker inspect "%REDIS_CONTAINER%" >nul 2>nul
if errorlevel 1 (
  echo Creating %REDIS_CONTAINER% on 127.0.0.1:%REDIS_PORT%...
  docker run -d --name "%REDIS_CONTAINER%" ^
    -p 127.0.0.1:%REDIS_PORT%:6379 ^
    redis:7-alpine ^
    redis-server --save 60 1000 --maxmemory-policy noeviction || goto failed
) else (
  docker start "%REDIS_CONTAINER%" >nul || goto failed
)

echo [3/6] Waiting for MySQL...
for /L %%i in (1,1,30) do (
  docker exec "%MYSQL_CONTAINER%" mysqladmin ping -h 127.0.0.1 -u root -p%MYSQL_ROOT_PASSWORD% --silent >nul 2>nul
  if not errorlevel 1 goto mysql_ready
  timeout /t 2 /nobreak >nul
)
echo MySQL did not become ready in time.
goto failed

:mysql_ready
echo [4/6] Running database migrations...
pushd backend >nul
set MYSQL_HOST=%MYSQL_HOST%
set MYSQL_PORT=%MYSQL_PORT%
set MYSQL_USER=%MYSQL_USER%
set MYSQL_PASSWORD=%MYSQL_PASSWORD%
set MYSQL_DATABASE=%MYSQL_DATABASE%
set REDIS_HOST=%REDIS_HOST%
set REDIS_PORT=%REDIS_PORT%
set REDIS_DB=%REDIS_DB%
alembic upgrade head || goto failed_pop_backend
popd >nul

echo [5/6] Starting backend dev server in a new window...
start "dystore backend dev" cmd /k "cd /d ""%ROOT_DIR%\backend"" && set MYSQL_HOST=%MYSQL_HOST%&& set MYSQL_PORT=%MYSQL_PORT%&& set MYSQL_USER=%MYSQL_USER%&& set MYSQL_PASSWORD=%MYSQL_PASSWORD%&& set MYSQL_DATABASE=%MYSQL_DATABASE%&& set REDIS_HOST=%REDIS_HOST%&& set REDIS_PORT=%REDIS_PORT%&& set REDIS_DB=%REDIS_DB%&& set PLAYWRIGHT_USER_DATA_DIR=%PLAYWRIGHT_USER_DATA_DIR%&& uvicorn dystore.main:app --host 127.0.0.1 --port 8080 --reload"

echo [6/6] Starting frontend dev server in a new window...
start "dystore web dev" cmd /k "cd /d ""%ROOT_DIR%\web"" && pnpm dev -- --host 127.0.0.1"

echo.
echo Dev environment started.
echo Frontend: http://127.0.0.1:5173/  ^(or the next free port shown by Vite^)
echo Backend:  http://127.0.0.1:8080/docs
echo MySQL:    127.0.0.1:%MYSQL_PORT%
echo Redis:    127.0.0.1:%REDIS_PORT%
popd >nul
exit /b 0

:failed_pop_backend
popd >nul
goto failed

:missing_docker
echo Missing docker. Install and start Docker Desktop first.
goto failed

:missing_python
echo Missing python. Install Python and add it to PATH first.
goto failed

:missing_pnpm
echo Missing pnpm. Install Node.js/corepack/pnpm first.
goto failed

:missing_uvicorn
echo Missing uvicorn. Run: cd backend && pip install -e ".[dev]"
goto failed

:missing_alembic
echo Missing alembic. Run: cd backend && pip install -e ".[dev]"
goto failed

:failed
echo.
echo Failed to start dev environment.
popd >nul
exit /b 1

:help
echo Usage: scripts\start-dev.cmd
echo.
echo Starts local dev dependencies, runs Alembic migrations, then opens backend and frontend dev servers.
echo Defaults:
echo   MySQL: 127.0.0.1:3307, container dystoretools-mysql-dev
echo   Redis: 127.0.0.1:6387, container dystoretools-redis-dev
echo   Backend: http://127.0.0.1:8080/docs
echo   Frontend: http://127.0.0.1:5173/ or next free Vite port
exit /b 0
