# Script: 2_gerencia_conversao_md.ps1
# Propósito: criar e configurar ambiente virtual com logging, tratamento de erros

param()

# desliga o oneDNN custom ops
$env:TF_ENABLE_ONEDNN_OPTS = '0'
# só mostra WARNING e ERROR do TF, remove os INFO
$env:TF_CPP_MIN_LOG_LEVEL = '2'


$logFile = "$PSScriptRoot\docling_env_setup.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }
Start-Transcript -Path $logFile -Append

# variáveis
$pythonPath = 'C:\Program Files\Python310\python.exe'
$projectDir = 'C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\GIT\scripts\2_PDFs'
$venvDir    = 'C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\docling_env'
$scriptPath = Join-Path $projectDir '2b_converte_md.py'

Write-Host "[INFO] Projeto: $projectDir"
Write-Host "[INFO] Venv:     $venvDir"

# controla instalação de dependências
$installDeps = $true

# pergunta se deve recriar
$recreate = $false
if (Test-Path $venvDir) {
    $resp = Read-Host "Ambiente virtual em '$venvDir' já existe. Deseja sobrescrever? (S/N)"
    if ($resp -match '^[Ss]') {
        Write-Host "[INFO] Removendo ambiente existente..."
        Remove-Item -Recurse -Force $venvDir
        $recreate = $true
    } else {
        Write-Host "[INFO] Usando ambiente existente"
        $installDeps = $false
    }
} else {
    $recreate = $true
}

# (re)cria venv se preciso
if ($recreate) {
    Try {
        Write-Host "[INFO] Criando ambiente virtual em $venvDir..."
        & $pythonPath -m venv $venvDir
    } Catch {
        Write-Error "[ERROR] Falha ao criar venv: $_"
        Stop-Transcript; exit 1
    }
}

# ativa venv
Try {
    Write-Host "[INFO] Ativando ambiente virtual..."
    . (Join-Path $venvDir 'Scripts\Activate.ps1')
} Catch {
    Write-Error "[ERROR] Não foi possível ativar o ambiente: $_"
    Stop-Transcript; exit 1
}

$pythonExe = Join-Path $venvDir 'Scripts\python.exe'

if ($installDeps) {
    # garante que pip está atualizado
    Try {
        Write-Host "[INFO] Atualizando pip..."
        & $pythonExe -m pip install --upgrade pip --disable-pip-version-check
    } Catch {
        Write-Error "[ERROR] Falha ao atualizar pip: $_"
        Stop-Transcript; exit 1
    }

    # instala ou atualiza dependências
    Try {
        Write-Host "[INFO] Instalando/atualizando dependências..."
        & $pythonExe -m pip install --upgrade "numpy<2" docling transformers tensorflow docling-parse
        & $pythonExe -m pip install --upgrade --force-reinstall `
            "git+https://github.com/docling-project/docling-parse.git@main#egg=docling-parse"
    } Catch {
        Write-Error "[ERROR] Falha ao instalar dependências: $_"
        Stop-Transcript; exit 1
    }
} else {
    Write-Host "[INFO] Pulando atualização e instalação de dependências"
}

# verifica versões
Try {
    Write-Host "[INFO] Verificando versões instaladas..."
    & $pythonExe -c "import numpy; import docling; import tensorflow; from importlib.metadata import version; print('numpy', version('numpy')); print('docling', version('docling')); print('tensorflow', version('tensorflow'))"
} Catch {
    Write-Error "[ERROR] Falha na verificação de versões: $_"
    Stop-Transcript; exit 1
}


# executa conversão
Try {
    Write-Host "[INFO] Executando script de conversão..."
    & $pythonExe $scriptPath
} Catch {
    Write-Error "[ERROR] Falha ao executar converte.py: $_"
    Stop-Transcript; exit 1
}

Write-Host "[INFO] Processo concluído com sucesso."
Stop-Transcript
