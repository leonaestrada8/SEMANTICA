// script.js
let ws;
let statsInterval;

// Conectar WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/semantica-consignacao`);
    
    ws.onopen = function() {
        addLog("✅ WebSocket conectado");
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = function() {
        addLog("❌ WebSocket desconectado - Reconectando...");
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = function(error) {
        addLog(`💥 Erro WebSocket: ${error.message || 'Erro desconhecido'}`);
    };
}

// Tratar mensagens WebSocket
function handleWebSocketMessage(data) {
    const timestamp = new Date().toLocaleTimeString();
    
    if (data.error) {
        addLog(`[${timestamp}] ❌ Erro: ${data.error}`);
        return;
    }
    
    if (data.status) {
        if (data.status === "started") {
            addLog(`[${timestamp}] 🚀 Processamento iniciado: ${data.total} itens`);
            showProgress(`Iniciando processamento de ${data.total} itens...`);
        } else if (data.status === "completed") {
            addLog(`[${timestamp}] 🎉 Processamento concluído`);
            hideProgress();
        }
        return;
    }
    
    if (data.progress) {
        addLog(`[${timestamp}] 📊 ${data.progress} (${data.percentage}%) - ${data.item} - ${data.status}`);
        showProgress(`${data.progress} (${data.percentage}%) - ${data.item}: ${data.status}`);
        return;
    }
    
    // Resposta de análise individual
    if (data.analysis_id || data.diagnostico_llm) {
        const status = data.status || 'UNKNOWN';
        const confidence = data.confidence ? ` (${(data.confidence * 100).toFixed(1)}%)` : '';
        addLog(`[${timestamp}] 🎯 ${status}${confidence} - ${data.diagnostico_llm || 'N/A'}`);
    }
}

// Adicionar log
function addLog(message) {
    const logArea = document.getElementById('logArea');
    logArea.textContent += message + '\n';
    logArea.scrollTop = logArea.scrollHeight;
}

// Limpar log
function clearLog() {
    document.getElementById('logArea').textContent = '[Log limpo]\n';
}

// Mostrar progresso
function showProgress(message) {
    const progress = document.getElementById('fileProgress');
    progress.textContent = message;
    progress.classList.add('active');
}

// Esconder progresso
function hideProgress() {
    const progress = document.getElementById('fileProgress');
    progress.classList.remove('active');
}

// Função auxiliar para mostrar loading
function showLoading(buttonId, resultId, message = "🔄 Processando...") {
    const button = document.getElementById(buttonId);
    const resultDiv = document.getElementById(resultId);
    
    // Desabilitar botão e mostrar loading
    button.disabled = true;
    button.innerHTML = message;
    
    // Mostrar resultado de loading
    resultDiv.className = 'result loading';
    resultDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <div class="spinner"></div>
            <span>Analisando com Serpro LLM...</span>
        </div>
    `;
    resultDiv.style.display = 'block';
}

// Função auxiliar para esconder loading
function hideLoading(buttonId, originalText) {
    const button = document.getElementById(buttonId);
    button.disabled = false;
    button.innerHTML = originalText;
}

// Testar JSON estruturado
async function testJson() {
    const input = document.getElementById('jsonInput').value;
    const resultDiv = document.getElementById('jsonResult');
    const buttonId = 'jsonBtn';
    
    // Mostrar loading
    showLoading(buttonId, 'jsonResult');
    
    try {
        const data = JSON.parse(input);
        const response = await fetch('/analise-semantica', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            resultDiv.className = 'result success';
            resultDiv.innerHTML = `
                <strong>✅ Sucesso!</strong><br>
                <strong>Status:</strong> ${result.status}<br>
                <strong>Diagnóstico:</strong> ${result.diagnostico_llm}<br>
                <strong>Confiança:</strong> ${(result.confidence * 100).toFixed(1)}%<br>
                <strong>Tempo:</strong> ${result.processing_time.toFixed(2)}s<br>
                <strong>ID da Análise:</strong> ${result.analysis_id}<br>
                <details style="margin-top: 10px;">
                    <summary>Ver resposta completa</summary>
                    <pre style="margin-top: 5px; font-size: 11px;">${JSON.stringify(result, null, 2)}</pre>
                </details>
            `;
            
            // Log da operação
            addLog(`✅ Análise: ${result.status} - ${result.diagnostico_llm} (${(result.confidence * 100).toFixed(1)}%)`);
        } else {
            resultDiv.className = 'result error';
            resultDiv.innerHTML = `
                <strong>❌ Erro!</strong><br>
                ${result.detail || JSON.stringify(result, null, 2)}
            `;
            
            addLog(`❌ Erro na análise: ${result.detail || 'Erro desconhecido'}`);
        }
        
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `
            <strong>❌ Erro!</strong><br>
            ${error.message}
        `;
        
        addLog(`❌ Erro na análise: ${error.message}`);
    } finally {
        // Restaurar botão
        hideLoading(buttonId, '🧪 Analisar JSON');
    }
}

// Carregar exemplo
function loadExample() {
    const examples = [
        {
            "id_termo": "314166",
            "cpf": "48956314785",
            "pratica_vedada": "10,11",
            "justificativa": "Estou sendo descontado sem autorização prévia do empréstimo consignado no valor de R$ 450,00 mensais. Nunca solicitei este empréstimo e não recebi nenhum valor creditado em minha conta."
        },
        {
            "id_termo": "314167",
            "cpf": "12345678901",
            "pratica_vedada": "12",
            "justificativa": "Foi descontado empréstimo consignado do meu benefício, porém nunca recebi o valor creditado na minha conta bancária. Solicito o estorno imediato dos valores."
        },
        {
            "id_termo": "314168",
            "cpf": "98765432100",
            "pratica_vedada": "Contrato liquidado",
            "justificativa": "Continuo sendo descontado mesmo após ter quitado completamente o empréstimo consignado há 3 meses. Tenho comprovante de quitação mas os descontos persistem."
        }
    ];
    
    const randomExample = examples[Math.floor(Math.random() * examples.length)];
    document.getElementById('jsonInput').value = JSON.stringify(randomExample, null, 2);
    addLog("📄 Exemplo carregado");
}

// Processar arquivo
function processFile() {
    const filename = document.getElementById('filename').value || '100.txt';
    const button = document.getElementById('processBtn');
    
    if (ws.readyState === WebSocket.OPEN) {
        // Desabilitar botão durante processamento
        button.disabled = true;
        button.innerHTML = '🔄 Processando...';
        
        ws.send(JSON.stringify({
            action: "process_file",
            filename: filename
        }));
        
        addLog(`📁 Iniciando processamento de: ${filename}`);
        
        // Re-habilitar botão após 5 segundos
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = '🚀 Processar Arquivo';
        }, 5000);
    } else {
        addLog("❌ WebSocket não conectado");
    }
}

// Atualizar estatísticas
async function updateStats() {
    try {
        const response = await fetch('/stats');
        const stats = await response.json();
        
        document.getElementById('totalRequests').textContent = stats.total_requests;
        document.getElementById('totalErrors').textContent = stats.total_errors;
        document.getElementById('errorRate').textContent = stats.error_rate.toFixed(1) + '%';
        document.getElementById('uptime').textContent = stats.uptime_seconds.toFixed(0) + 's';
        
    } catch (error) {
        console.error('Erro ao atualizar estatísticas:', error);
    }
}

// Carregar logs do sistema
async function loadSystemLogs() {
    const button = document.getElementById('loadLogsBtn');
    const logsDiv = document.getElementById('systemLogs');
    
    try {
        // Mostrar loading
        button.disabled = true;
        button.innerHTML = '🔄 Carregando...';
        
        const response = await fetch('/logs');
        const data = await response.json();
        
        if (response.ok && data.logs) {
            logsDiv.style.display = 'block';
            logsDiv.innerHTML = `=== LOGS RECENTES (${data.recent_lines} de ${data.total_lines} linhas) ===\n\n` + 
                               data.logs.join('');
            logsDiv.scrollTop = logsDiv.scrollHeight;
            
            addLog(`📋 Logs carregados: ${data.recent_lines} linhas recentes`);
        } else {
            logsDiv.style.display = 'block';
            logsDiv.innerHTML = `❌ Erro ao carregar logs: ${data.message || 'Erro desconhecido'}`;
            addLog(`❌ Erro ao carregar logs do sistema`);
        }
        
    } catch (error) {
        logsDiv.style.display = 'block';
        logsDiv.innerHTML = `❌ Erro de conexão: ${error.message}`;
        addLog(`❌ Erro ao conectar com endpoint de logs: ${error.message}`);
    } finally {
        button.disabled = false;
        button.innerHTML = '📥 Carregar Logs Recentes';
    }
}

// Inicializar quando página carregar
document.addEventListener('DOMContentLoaded', function() {
    connectWebSocket();
    updateStats();
    
    // Atualizar estatísticas a cada 10 segundos
    statsInterval = setInterval(updateStats, 10000);
    
    addLog("🚀 Interface carregada e pronta!");
    addLog("💡 Use o formulário acima para testar a API");
    addLog("📁 Use a seção de arquivo para processamento em lote");
});