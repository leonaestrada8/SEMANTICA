import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import re
import AE_semantica_functions as funcoes

# ================================
# CONFIGURAÇÕES
# ================================

ARQUIVO_CSV = "dadosTermosReclamacao.csv"
COLUNAS_ESPERADAS = ["PRATICAS VEDADAS", "JUSTIFICATIVA"]
LIMITE_CURTA = 5
LIMITE_LONGA = 200

if __name__ == "__main__":
    df_inicial = funcoes.carregar_csv(ARQUIVO_CSV)
    funcoes.validar_colunas(df_inicial, COLUNAS_ESPERADAS)

    colunas_salvar = ["ID TERMO", "PRATICAS VEDADAS", "JUSTIFICATIVA"]

    funcoes.mostrar_distribuicao(df_inicial, expandir=False)
    funcoes.mostrar_distribuicao(df_inicial, expandir=True)

    df_expandido = funcoes.expandir_praticas_vedadas(df_inicial)
    funcoes.analisar_justificativas(df_expandido, LIMITE_LONGA, LIMITE_CURTA)

    df_restante = df_inicial.copy()
    ids_reprovados_total = set()

    # === 1. Ruído
    df_restante, df_ruido = funcoes.filtrar_por_ruido(df_restante, colunas_salvar)
    ids_ruido = funcoes.registrar_reprovados("ruido", df_ruido, ids_reprovados_total, colunas_salvar)
    ids_reprovados_total.update(ids_ruido)

    # === 2. Regex
    df_restante, df_regex = funcoes.filtrar_por_regex(df_restante, colunas_salvar)
    ids_regex = funcoes.registrar_reprovados("regex", df_regex, ids_reprovados_total, colunas_salvar)
    ids_reprovados_total.update(ids_regex)

     # === 4. Repetição
    df_restante, df_repet = funcoes.filtrar_por_repeticao(df_restante, colunas_salvar)
    ids_repet = funcoes.registrar_reprovados("repeticao", df_repet, ids_reprovados_total, colunas_salvar)
    ids_reprovados_total.update(ids_repet)

    # === CONTAGEM FINAL ===
    funcoes.exibir_resumo_final(df_inicial, len(df_inicial))

'''
    # === 3. Similaridade TF-IDF
    df_filtragem_similaridade = funcoes.limpar_ids_reprovados(df_restante, ids_reprovados_total)
    df_similares, ids_similares_repetidos, total_pares_repetido = funcoes.detectar_similares_consecutivos_tfidf(df_filtragem_similaridade)
    print(f"Total similares --------->>>>>>: {total_pares_repetido}")

    df_restante_filtrado = funcoes.limpar_ids_reprovados(df_restante, ids_reprovados_total)

    df_restante_filtrado, df_similares_repetidos, ids_similares_repetidos = funcoes.filtrar_por_similaridade(
        df_restante_filtrado, df_similares, colunas_salvar
    )

    # Atualiza o df_restante original com apenas os IDs restantes após filtro de similaridade
    df_restante = df_restante[df_restante["ID TERMO"].isin(df_restante_filtrado["ID TERMO"])].copy()

    ids_reprovados_total.update(ids_similares_repetidos)

'''
   


