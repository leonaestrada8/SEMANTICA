import os
from pathlib import Path
import statistics
import tiktoken

# configurar aqui o diretório que contém os arquivos .md
base_dir = Path(r"C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\md files")

# escolher o modelo cujo vocabulário será usado na contagem de tokens
encoding = tiktoken.encoding_for_model("gpt-4")  # ou "gpt-3.5-turbo"

def count_tokens(text: str) -> int:
    return len(encoding.encode(text or ""))

token_counts = []

for md_path in base_dir.rglob("*.md"):
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Falha ao ler {md_path.name}: {e}")
        continue
    n_tokens = count_tokens(text)
    token_counts.append(n_tokens)
    print(f"{md_path.name}: {n_tokens} tokens")

if token_counts:
    total = sum(token_counts)
    minimum = min(token_counts)
    maximum = max(token_counts)
    mean = statistics.mean(token_counts)
    median = statistics.median(token_counts)
    stdev = statistics.pstdev(token_counts)

    print("\nEstatísticas gerais de tokens:")
    print(f"  • Total de arquivos analisados: {len(token_counts)}")
    #print(f"  • Soma de tokens           : {total}")
    print(f"  • Mínimo por arquivo       : {minimum}")
    print(f"  • Máximo por arquivo       : {maximum}")
    print(f"  • Média por arquivo        : {mean:.2f}")
    print(f"  • Mediana por arquivo      : {median}")
    print(f"  • Desvio padrão populacional: {stdev:.2f}")
else:
    print("Nenhum arquivo .md encontrado em:", base_dir)
