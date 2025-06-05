@echo off
echo 🚀 Instalando Semântica Consignação API
echo =======================================

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado!
    echo 📥 Instale Python 3.8+ de: https://python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python encontrado
python --version

REM Remover ambiente existente
if exist "venv" (
    echo 🗑️ Removendo ambiente existente...
    rmdir /s /q venv
)

REM Criar ambiente virtual
echo 📦 Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo ❌ Erro ao criar ambiente virtual
    pause
    exit /b 1
)

REM Ativar ambiente
echo 🔄 Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Erro ao ativar ambiente
    pause
    exit /b 1
)

REM Atualizar pip
echo 📦 Atualizando pip...
python -m pip install --upgrade pip

REM Instalar dependências
echo 📋 Instalando dependências...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erro ao instalar dependências
    pause
    exit /b 1
)

REM Verificar instalação
echo 🧪 Verificando instalação...
python -c "import fastapi, uvicorn, aiohttp, requests; print('✅ Dependências OK')"
if errorlevel 1 (
    echo ❌ Erro na verificação
    pause
    exit /b 1
)

REM Criar pastas
echo 📁 Criando pastas...
if not exist "justificativas" mkdir justificativas
if not exist "JSON" mkdir JSON
if not exist "logs" mkdir logs
if not exist "templates" mkdir templates

echo.
echo 🎉 INSTALAÇÃO CONCLUÍDA!
echo ======================
echo.
echo 📋 Próximos passos:
echo 1. Configure as credenciais em config.py
echo 2. Execute: run.bat
echo 3. Acesse: http://localhost:8000
echo.
echo 📚 URLs úteis:
echo    Interface: http://localhost:8000
echo    Swagger:   http://localhost:8000/docs
echo    Health:    http://localhost:8000/health
echo.
echo ✅ Pronto para usar!
echo.
pause