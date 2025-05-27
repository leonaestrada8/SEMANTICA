# Script: create_trata_pdf_env.ps1
# Propósito: criar e configurar ambiente virtual com logging, tratamento de erros

param()

# Início do log de sessão
$logFile = "$PSScriptRoot\docling_env_setup.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }
Start-Transcript -Path $logFile -Append

# 1. Definições de variáveis usando $PSScriptRoot em vez de caminho fixo
$pythonPath  = 'C:\Program Files\Python310\python.exe'
$projectDir  = 'C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\scripts\2_PDFs'
$venvDir     = Join-Path $projectDir 'docling_env'
$scriptPath  = Join-Path $projectDir '2B_converte_md.py'

Write-Host "[INFO] Projeto: $projectDir"
Write-Host "[INFO] Venv:     $venvDir"

# 2. Verificar existência do venv
$recreate = $false
if (Test-Path $venvDir) {
    $resp = Read-Host "Ambiente virtual em '$venvDir' já existe. Deseja sobrescrever? (S/N)"
    if ($resp -match '^[Ss]') {
        Write-Host "[INFO] Removendo ambiente existente..."
        Remove-Item -Recurse -Force $venvDir -ErrorAction Stop
        $recreate = $true
    } else {
        Write-Host "[INFO] Usando ambiente existente em $venvDir"
    }
} else {
    $recreate = $true
}

# 3. Criar o ambiente virtual se necessário
if ($recreate) {
    Try {
        Write-Host "[INFO] Criando ambiente virtual em $venvDir..."
        & $pythonPath -m venv $venvDir 2>&1 | Write-Host
    } Catch {
        Write-Error "[ERROR] Falha ao criar venv: $_"
        Stop-Transcript; exit 1
    }
}

# 4. Ativar o venv
Try {
    Write-Host "[INFO] Ativando ambiente virtual..."
    . "$venvDir\Scripts\Activate.ps1"
} Catch {
    Write-Error "[ERROR] Não foi possível ativar o ambiente: $_"
    Stop-Transcript; exit 1
}

# 5. Atualizar pip
Try {
    Write-Host "[INFO] Atualizando pip..."
    python -m pip install --upgrade pip --disable-pip-version-check | Write-Host
} Catch {
    Write-Error "[ERROR] Falha ao atualizar pip: $_"
    Stop-Transcript; exit 1
}

# 6. Instalar NumPy <2.0 para evitar incompatibilidades
Try {
    Write-Host "[INFO] Instalando NumPy <2.0..."
    pip install "numpy<2" | Write-Host
} Catch {
    Write-Error "[ERROR] Falha ao instalar NumPy: $_"
    Stop-Transcript; exit 1
}

# 7. Instalar dependências principais
$packages = @('docling', 'transformers', 'tensorflow', 'docling-parse')
foreach ($pkg in $packages) {
    Try {
        Write-Host "[INFO] Instalando/reinstalando $pkg..."
        pip install --upgrade --force-reinstall $pkg | Write-Host
    } Catch {
        Write-Error "[ERROR] Falha ao instalar $($pkg): $_"
        Stop-Transcript; exit 1
    }
}

# 8. Instalar docling-parse diretamente do GitHub
Try {
    Write-Host "[INFO] Instalando docling-parse v2 diretamente do GitHub..."
    pip install --upgrade --force-reinstall 'git+https://github.com/docling-project/docling-parse.git@main#egg=docling-parse' | Write-Host
} Catch {
    Write-Error "[ERROR] Falha ao instalar docling-parse do GitHub: $_"
    Stop-Transcript; exit 1
}

# 9. Verificação de versões instaladas
Try {
    Write-Host "[INFO] Verificando versões instaladas..."
    $pyCode = @"
import numpy, docling, tensorflow, importlib.metadata as m
print('numpy        :', numpy.__version__)
print('docling      :', docling.__version__)
print('tensorflow   :', tensorflow.__version__)
print('docling-parse:', m.version('docling-parse'))
"@
    $pyCode | python
} Catch {
    Write-Error "[ERROR] Falha na verificação de versões: $_"
    Stop-Transcript; exit 1
}

# 10. Execução do script de conversão
Try {
    Write-Host "[INFO] Executando converte.py..."
    python $scriptPath | Write-Host
} Catch {
    Write-Error "[ERROR] Falha ao executar converte.py: $_"
    Stop-Transcript; exit 1
}

Write-Host "[INFO] Processo concluído com sucesso."
Stop-Transcript
