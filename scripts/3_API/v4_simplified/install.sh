#!/bin/bash
# install.sh - Instalador Simplificado

echo "🚀 Instalando Semântica Consignação API"
echo "======================================="

# Detectar sistema operacional
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON_CMD="python"
    VENV_ACTIVATE="venv\\Scripts\\activate"
else
    PYTHON_CMD="python3"
    VENV_ACTIVATE="venv/bin/activate"
fi

# Verificar Python
echo "🔍 Verificando Python..."
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Python não encontrado!"
    echo "📥 Instale Python 3.8+ de: https://python.org/downloads/"
    exit 1
fi

echo "✅ Python encontrado"
$PYTHON_CMD --version

# Verificar versão Python
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
    echo "❌ Python 3.8+ necessário. Versão atual: $PYTHON_VERSION"
    exit 1
fi

# Remover ambiente virtual existente
if [ -d "venv" ]; then
    echo "🗑️ Removendo ambiente virtual existente..."
    rm -rf venv
fi

# Criar ambiente virtual
echo "📦 Criando ambiente virtual..."
$PYTHON_CMD -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Erro ao criar ambiente virtual"
    exit 1
fi

# Ativar ambiente virtual
echo "🔄 Ativando ambiente virtual..."
source $VENV_ACTIVATE
if [ $? -ne 0 ]; then
    echo "❌ Erro ao ativar ambiente virtual"
    exit 1
fi

# Atualizar pip
echo "📦 Atualizando pip..."
python -m pip install --upgrade pip

# Instalar dependências
echo "📋 Instalando dependências..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Erro ao instalar dependências"
    exit 1
fi

# Verificar instalação
echo "🧪 Verificando instalação..."
python -c "import fastapi, uvicorn, aiohttp, requests; print('✅ Dependências OK')"
if [ $? -ne 0 ]; then
    echo "❌ Erro na verificação"
    exit 1
fi

# Criar pastas necessárias
echo "📁 Criando pastas..."
mkdir -p justificativas JSON logs templates

# Criar script de execução
echo "📝 Criando script de execução..."
cat > run.sh << 'EOF'
#!/bin/bash
echo "🚀 Iniciando API..."
source venv/bin/activate
python main.py
EOF
chmod +x run.sh

echo ""
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "======================"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure as credenciais em config.py"
echo "2. Execute: ./run.sh"
echo "3. Acesse: http://localhost:8000"
echo ""
echo "📚 URLs úteis:"
echo "   Interface: http://localhost:8000"
echo "   Swagger:   http://localhost:8000/docs"
echo "   Health:    http://localhost:8000/health"
echo ""
echo "🛠️ Para desenvolvimento:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload"
echo ""
echo "✅ Pronto para usar!"