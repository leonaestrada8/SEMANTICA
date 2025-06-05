# processador.py
import asyncio
import time
import json
from pathlib import Path
from datetime import datetime
from serpro_client import SerproClient
from utils import *
from models import ProcessingResult
from config import *

async def process_file(filename="100.txt"):
    """Processa arquivo em lote"""
    print(f"📁 Processando arquivo: {filename}")
    
    # Verificar arquivo
    file_path = Path(INPUT_FOLDER) / filename
    if not file_path.exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    
    # Ler arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    # Pular cabeçalho se existir
    if lines and lines[0].startswith("IDTERMO#CPF"):
        lines = lines[1:]
        print("⏭️ Pulando cabeçalho")
    
    print(f"📋 Total de itens: {len(lines)}")
    
    # Inicializar
    client = SerproClient()
    results = []
    stats = {
        "total": len(lines),
        "approved": 0,
        "rejected": 0,
        "review_required": 0,
        "errors": 0
    }
    
    start_time = time.time()
    
    # Processar cada linha
    for i, line in enumerate(lines, 1):
        print(f"\n[{i}/{len(lines)}] Processando...")
        
        try:
            # Parse da linha
            data = parse_line(line)
            print(f"ID: {data['id_termo']} - Justificativa: {data['justificativa'][:50]}...")
            
            # Chamar LLM
            prompt = create_prompt(data['justificativa'])
            llm_result = await client.call_llm(prompt)
            
            # Classificar resultado
            diagnostico = llm_result.get('diagnosticoLLM', 'NÃO')
            confidence = llm_result.get('confidence', 0.5)
            status = classify_result(diagnostico, confidence)
            
            # Criar resultado
            result = ProcessingResult(
                id_termo=data['id_termo'],
                cpf=data['cpf'],
                pratica_vedada=data['pratica_vedada'],
                justificativa=data['justificativa'],
                status=status,
                diagnostico_llm=diagnostico,
                confidence=confidence,
                justificativa_llm=llm_result.get('justificativaLLM', '')
            )
            
            results.append(result)
            stats[status.lower()] += 1
            
            # Log do resultado
            print(f"✅ {status} - {diagnostico} ({confidence:.2f})")
            
            # Salvar resultado individual
            save_json(result.dict(), f"{data['id_termo']}.json")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            
            # Resultado de erro
            try:
                data = parse_line(line)
            except:
                data = {"id_termo": f"ERROR_{i}", "cpf": "", "pratica_vedada": "", "justificativa": line}
            
            error_result = ProcessingResult(
                **data,
                status="ERROR",
                error_message=str(e)
            )
            results.append(error_result)
            stats["errors"] += 1
        
        # Delay entre requisições
        if i < len(lines):
            await asyncio.sleep(1)
    
    # Estatísticas finais
    total_time = time.time() - start_time
    
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL")
    print("=" * 50)
    print(f"📁 Arquivo: {filename}")
    print(f"📈 Total processado: {stats['total']}")
    print(f"✅ Aprovados: {stats['approved']}")
    print(f"⚠️ Revisão necessária: {stats['review_required']}")
    print(f"❌ Rejeitados: {stats['rejected']}")
    print(f"💥 Erros: {stats['errors']}")
    print(f"⏱️ Tempo total: {total_time:.1f}s")
    print(f"📊 Tempo médio por item: {total_time/len(lines):.1f}s")
    
    # Calcular taxas
    if stats['total'] > 0:
        approval_rate = (stats['approved'] / stats['total']) * 100
        error_rate = (stats['errors'] / stats['total']) * 100
        print(f"📈 Taxa de aprovação: {approval_rate:.1f}%")
        print(f"💥 Taxa de erro: {error_rate:.1f}%")
    
    # Salvar relatório completo
    report = {
        "arquivo": filename,
        "timestamp": datetime.now().isoformat(),
        "estatisticas": stats,
        "tempo_total": total_time,
        "resultados": [r.dict() for r in results]
    }
    
    save_json(report, f"relatorio_{filename.replace('.txt', '')}.json")
    print(f"💾 Relatório salvo em: {OUTPUT_FOLDER}")
    print("=" * 50)

async def main():
    """Função principal"""
    print("📊 Processador de Arquivos - Serpro LLM")
    print("=" * 40)
    
    setup_folders()
    
    # Verificar se arquivo padrão existe
    default_file = Path(INPUT_FOLDER) / "100.txt"
    if not default_file.exists():
        print(f"❌ Arquivo padrão não encontrado: {default_file}")
        print("💡 Criando arquivo de exemplo...")
        
        sample_content = """IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA
314166#4895631478#10,11#Estou sendo descontado sem autorização prévia
314167#9876543210#12#Nunca recebi o valor do empréstimo consignado
314168#1234567890#Contrato liquidado#Continuam descontando após quitação
314169#5555555555#Boleto#SOLICITO MEU BOLETO DE QUITAÇÃO"""
        
        with open(default_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        print(f"📄 Arquivo criado: {default_file}")
    
    # Processar arquivo
    filename = input(f"Nome do arquivo [{default_file.name}]: ").strip() or default_file.name
    
    try:
        await process_file(filename)
    except KeyboardInterrupt:
        print("\n⏹️ Processamento interrompido")
    except Exception as e:
        print(f"\n💥 Erro: {e}")

if __name__ == "__main__":
    asyncio.run(main())