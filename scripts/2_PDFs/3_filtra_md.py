import os
import re
import shutil
from collections import defaultdict

# mapeamento de padrões para pastas de destino
mappings = [
    (r"COMPROVANTE DE RENDIMENTOS", "COMPROVANTE DE RENDIMENTOS"),
    (r"Comprovante de Pagamento", "comprovante de pagamento"),
    (r"IDENTIFICAÇÃO DO REPRESENTANTE LEGAL DO CONSIGNATÁRIO", "declaração"),
    (r"Extrato de Consignações Vigentes", "extrato de consignacoes vigentes"),
    (r"Solicitaçªo de Liquidaçªo Antecipada", "-odd"),
    (r"\b(?:\d[ ]?){47,48}\b", "boleto"),
    (r"Cálculo de Liquidação Antecipada", "calculo de quitacao antecipada"),
    (r"COMPROVANTE DE PAGAMENTO", "comprovante de pagamento"),
    (r"Detalhe Consignação", "detalhe consignacao"),
]

cwd = os.getcwd()
print(f"Iniciando varredura em: {cwd}")

md_files = [f for f in os.listdir(cwd) if f.lower().endswith('.md')]
print(f"{len(md_files)} arquivos .md encontrados.\n")

moved_pdf_stats = defaultdict(int)
moved_md_stats = defaultdict(int)
missing_pdf_count = 0
unmatched_count = 0
error_move_count = 0
error_md_move_count = 0

for filename in md_files:
    print(f"Processando: {filename}")
    md_path = os.path.join(cwd, filename)
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  Erro ao ler {filename}: {e}")
        error_move_count += 1
        continue

    for pattern, dest_folder in mappings:
        print(f"  Verificando padrão «{pattern}»...")
        if re.search(pattern, content):
            target_dir = os.path.join(cwd, dest_folder)
            os.makedirs(target_dir, exist_ok=True)
            print(f"    Padrão encontrado! Movendo para '{dest_folder}/'")

            # mover o PDF
            pdf_name = os.path.splitext(filename)[0] + '.pdf'
            pdf_path = os.path.join(cwd, pdf_name)
            if os.path.exists(pdf_path):
                try:
                    shutil.move(pdf_path, os.path.join(target_dir, pdf_name))
                    print(f"      PDF movido: {pdf_name}")
                    moved_pdf_stats[dest_folder] += 1
                except Exception as e:
                    print(f"      Erro ao mover PDF: {e}")
                    error_move_count += 1
            else:
                print(f"      PDF não encontrado: {pdf_name}")
                missing_pdf_count += 1

            # mover o MD
            try:
                shutil.move(md_path, os.path.join(target_dir, filename))
                print(f"      MD movido: {filename}")
                moved_md_stats[dest_folder] += 1
            except Exception as e:
                print(f"      Erro ao mover MD: {e}")
                error_md_move_count += 1

            break
    else:
        print("  Nenhum padrão correspondeu.")
        unmatched_count += 1

print("\nEstatísticas de movimentação:")
for dest, count in moved_pdf_stats.items():
    print(f"  {count} PDFs movidos para '{dest}/'")
for dest, count in moved_md_stats.items():
    print(f"  {count} MDs movidos para '{dest}/'")
print(f"  {missing_pdf_count} PDFs não encontrados")
print(f"  {unmatched_count} MDs sem padrão correspondente")
print(f"  {error_move_count} erros ao mover PDFs")
print(f"  {error_md_move_count} erros ao mover MDs")
