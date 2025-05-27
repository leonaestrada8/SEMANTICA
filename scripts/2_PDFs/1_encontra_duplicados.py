#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapeamento e movimentação de arquivos em dois passos,
com relatório de quais arquivos foram detectados.
"""

import hashlib
import shutil
from pathlib import Path

# 1 Definição do diretório raiz (hard-coded)
RAIZ            = Path(r"C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\convertidos_pdf")
UNIQUE_DIR      = RAIZ / "UNIQUE"
REPETITION_DIR  = RAIZ / "REPETITION"

# 2 Controle de inclusão das pastas UNIQUE/REPETITION na varredura
INCLUIR_DESTINOS = False

def calcular_sha256(arquivo: Path, buffer_size: int = 8192) -> str:
    hasher = hashlib.sha256()
    with arquivo.open("rb") as f:
        for bloco in iter(lambda: f.read(buffer_size), b""):
            hasher.update(bloco)
    return hasher.hexdigest()

def mapear_por_hash(raiz: Path) -> dict[str, list[Path]]:
    mapeamento: dict[str, list[Path]] = {}
    arquivos_encontrados = 0

    for arquivo in raiz.rglob("*"):
        if not arquivo.is_file():
            continue

        # pulamos os subdiretórios de destino, se não quisermos includí-los
        if (not INCLUIR_DESTINOS
            and (UNIQUE_DIR in arquivo.parents or REPETITION_DIR in arquivo.parents)):
            continue

        arquivos_encontrados += 1
        h = calcular_sha256(arquivo)
        mapeamento.setdefault(h, []).append(arquivo)
        print(f"[mapeado] {arquivo.relative_to(raiz)} → hash {h}")

    # resumo estatístico da varredura
    total_hashes      = len(mapeamento)
    grupos_multiplos  = sum(1 for lst in mapeamento.values() if len(lst) > 1)
    arquivos_unicos   = sum(1 for lst in mapeamento.values() if len(lst) == 1)
    arquivos_duplicados = sum(len(lst) - 1 for lst in mapeamento.values() if len(lst) > 1)

    print("\n==== Resumo do Mapeamento ====")
    print(f"Arquivos detectados       : {arquivos_encontrados}")
    print(f"Hashes distintos           : {total_hashes}")
    print(f"Grupos com duplicados      : {grupos_multiplos}")
    print(f"Arquivos únicos            : {arquivos_unicos}")
    print(f"Arquivos que serão duplicados: {arquivos_duplicados}\n")

    return mapeamento

def mover_arquivos(mapeamento: dict[str, list[Path]]) -> None:
    UNIQUE_DIR.mkdir(exist_ok=True)
    REPETITION_DIR.mkdir(exist_ok=True)

    cont_unicos    = 0
    cont_repetidos = 0

    for arquivos in mapeamento.values():
        ordenados = sorted(arquivos)
        # primeiro → UNIQUE
        original = ordenados[0]
        destino = UNIQUE_DIR / original.name
        sufixo = 1
        while destino.exists():
            destino = UNIQUE_DIR / f"{original.stem}_{sufixo}{original.suffix}"
            sufixo += 1
        shutil.move(str(original), str(destino))
        cont_unicos += 1
        print(f"[único]    {original.relative_to(RAIZ)} → UNIQUE/{destino.name}")

        # demais → REPETITION
        for dup in ordenados[1:]:
            destino = REPETITION_DIR / dup.name
            sufixo = 1
            while destino.exists():
                destino = REPETITION_DIR / f"{dup.stem}_{sufixo}{dup.suffix}"
                sufixo += 1
            shutil.move(str(dup), str(destino))
            cont_repetidos += 1
            print(f"[repetido] {dup.relative_to(RAIZ)} → REPETITION/{destino.name}")

    total = cont_unicos + cont_repetidos
    print("\n==== Estatísticas da Movimentação ====")
    print(f"Total processado: {total}")
    print(f"  • Únicos    : {cont_unicos}")
    print(f"  • Repetidos : {cont_repetidos}")

def main():
    if not RAIZ.exists() or not RAIZ.is_dir():
        raise SystemExit(f"Erro: diretório inválido: {RAIZ}")

    print("== Passo 1: Mapeamento de arquivos por hash ==")
    mapeamento = mapear_por_hash(RAIZ)

    print("== Passo 2: Movimentação de arquivos ==")
    mover_arquivos(mapeamento)

if __name__ == "__main__":
    print("Iniciando script de organização de arquivos...\n")
    main()
