import os
from pathlib import Path

# Defina aqui o diretório a ser varrido
base_directory = Path(r"C:/Users/s056558027/Documents/SERPRO_DVLP/consignacao_semantica/convertidos_pdf")

pastas_analisadas = 0
arquivos_renomeados = 0

for dirpath, _, filenames in os.walk(base_directory):
    pastas_analisadas += 1
    pasta_atual = Path(dirpath)
    print(f"Analisando pasta: {pasta_atual}")
    for nome in filenames:
        src = pasta_atual / nome
        # verifica se termina em .pdf (case-insensitive)
        if src.suffix.lower() == ".pdf":
            destino = src.with_suffix("")  # remove a extensão
            try:
                src.rename(destino)
                arquivos_renomeados += 1
                print(f"{nome} → {destino.name}")
            except Exception as e:
                print(f"Erro ao renomear {src}: {e}")

print(f"Total de pastas analisadas: {pastas_analisadas}")
print(f"Total de arquivos renomeados: {arquivos_renomeados}")
