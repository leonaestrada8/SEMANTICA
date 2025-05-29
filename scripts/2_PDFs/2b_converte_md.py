#!/usr/bin/env python3
"""
Script para converter arquivos PDF em Markdown, com hardcoded directory,
contagem de sucesso/falha, prints de progresso, estatísticas de tamanho de arquivo,
per-file conversion time, tempo total e tempo médio.
"""
import time
from pathlib import Path
from docling.document_converter import DocumentConverter
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

# Diretório raiz hardcoded para varredura
ROOT_DIR = Path(
    r"C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\FILES\organizado"
)

def converte_pdfs_em_markdown(raiz: Path) -> None:
    print(f"Iniciando varredura no diretório: {raiz}")

    try:
        converter = DocumentConverter(pin_memory=True)
    except TypeError:
        converter = DocumentConverter()
    except Exception as e:
        print(f"Falha ao inicializar DocumentConverter: {e}")
        return

    pdf_paths = list(raiz.rglob('*.pdf'))
    total = len(pdf_paths)

    if total == 0:
        print(f"Nenhum PDF encontrado em {raiz}")
        return

    print(f"Encontrados {total} arquivos PDF. Iniciando conversão…\n")

    success_count = 0
    failures = []
    durations = []
    overall_start = time.time()

    for idx, pdf_path in enumerate(pdf_paths, start=1):
        size_bytes = pdf_path.stat().st_size
        size_kb = size_bytes / 1024
        print(f"[{idx}/{total}] Processando: {pdf_path.name} ({size_kb:.2f} KB)")

        file_start = time.time()
        try:
            resultado = converter.convert(str(pdf_path))
            markdown = resultado.document.export_to_markdown()
            md_path = pdf_path.with_suffix('.md')
            md_path.write_text(markdown, encoding='utf-8')
            file_end = time.time()
            file_duration = file_end - file_start
            durations.append(file_duration)

            print(f"[{idx}/{total}] Convertido: {pdf_path.name} -> {md_path.name} em {file_duration:.2f} segundos\n")
            success_count += 1
        except Exception as e:
            file_end = time.time()
            file_duration = file_end - file_start
            durations.append(file_duration)

            print(f"[{idx}/{total}] Erro na conversão de '{pdf_path.name}' após {file_duration:.2f} segundos: {e}\n")
            failures.append(pdf_path.name)

    overall_end = time.time()
    total_duration = overall_end - overall_start
    average_duration = total_duration / total if total else 0

    print("==== Estatísticas de Conversão ====")
    print(f"Total de arquivos processados : {total}")
    print(f"Convertidos com sucesso       : {success_count}")
    print(f"Conversões com falha          : {len(failures)}")
    if failures:
        print("Arquivos com erro:")
        for nome in failures:
            print(f"  - {nome}")
    print(f"Tempo total de processamento  : {total_duration:.2f} segundos")
    print(f"Tempo médio por arquivo       : {average_duration:.2f} segundos")

if __name__ == "__main__":
    converte_pdfs_em_markdown(ROOT_DIR)
