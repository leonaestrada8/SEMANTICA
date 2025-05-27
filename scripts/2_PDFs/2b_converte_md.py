#!/usr/bin/env python3
"""
Script para converter arquivos PDF em Markdown, com hardcoded directory,
contagem de sucesso/falha, prints de progresso e estatísticas.
"""
import time
from pathlib import Path
from docling.document_converter import DocumentConverter

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


# Diretório raiz hardcoded para varredura
ROOT_DIR = Path(
    r"C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\convertidos_pdf\UNIQUE"
)

def converte_pdfs_em_markdown(raiz: Path) -> None:
    """
    Para cada arquivo PDF em raiz (e subpastas), converte para Markdown
    e salva o .md na mesma pasta onde o PDF original está.

    Prints incluem progresso, erros e estatísticas finais.
    """
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
    start_time = time.time()

    for idx, pdf_path in enumerate(pdf_paths, start=1):
        print(f"[{idx}/{total}] Processando: {pdf_path}")
        try:
            resultado = converter.convert(str(pdf_path))
            markdown = resultado.document.export_to_markdown()
            md_path = pdf_path.with_suffix('.md')
            md_path.write_text(markdown, encoding='utf-8')
            print(f"[{idx}/{total}] Convertido: {pdf_path.name} -> {md_path.name}\n")
            success_count += 1
        except Exception as e:
            print(f"[{idx}/{total}] Erro: não foi possível converter '{pdf_path.name}': {e}\n")
            failures.append(pdf_path.name)

    end_time = time.time()
    duration = end_time - start_time

    print("==== Estatísticas de Conversão ====")
    print(f"Total de arquivos processados : {total}")
    print(f"Convertidos com sucesso       : {success_count}")
    print(f"Conversões com falha          : {len(failures)}")
    if failures:
        print("Arquivos com erro:")
        for nome in failures:
            print(f"  - {nome}")
    print(f"Tempo total de processamento  : {duration:.2f} segundos")

if __name__ == "__main__":
    converte_pdfs_em_markdown(ROOT_DIR)
