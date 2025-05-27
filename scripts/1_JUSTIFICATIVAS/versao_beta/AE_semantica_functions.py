import os
import pandas as pd
import re
import matplotlib.pyplot as plt


def carregar_csv(caminho):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"O arquivo '{caminho}' não foi encontrado no diretório atual.")
    try:
        return pd.read_csv(caminho, encoding="utf-8", sep=",")
    except (UnicodeDecodeError, pd.errors.ParserError):
        try:
            return pd.read_csv(caminho, encoding="latin1", sep=";")
        except Exception as e:
            raise RuntimeError(f"Erro ao tentar carregar o CSV: {e}")

def validar_colunas(df,COLUNAS_ESPERADAS):
    for coluna in COLUNAS_ESPERADAS:
        if coluna not in df.columns:
            raise ValueError(f"A coluna obrigatória '{coluna}' não foi encontrada no arquivo CSV.")


def expandir_praticas_vedadas(df):
    # Cria cópia explícita para evitar SettingWithCopyWarning
    df = df.copy()
    
    # Garante que a coluna esteja em string
    df["PRATICAS VEDADAS"] = df["PRATICAS VEDADAS"].astype(str)
    
    # Divide múltiplas práticas e explode as linhas
    df["PRATICAS_VEDADAS_TEMP"] = df["PRATICAS VEDADAS"].str.split(",")
    df_explodido = df.explode("PRATICAS_VEDADAS_TEMP").copy()

    # Remove espaços em branco e redefine a coluna original com os valores separados
    df_explodido["PRATICAS VEDADAS"] = df_explodido["PRATICAS_VEDADAS_TEMP"].str.strip()
    df_explodido.drop(columns=["PRATICAS_VEDADAS_TEMP"], inplace=True)

    return df_explodido
def analisar_justificativas(df, LIMITE_LONGA, LIMITE_CURTA):
    print("\nDistribuição percentual da coluna 'PRATICAS VEDADAS':")
    frequencias = df["PRATICAS VEDADAS"].value_counts(normalize=True) * 100
    frequencias_formatadas = frequencias.round(2).astype(str)
    print(frequencias_formatadas)

    contagem_palavras = df["JUSTIFICATIVA"].apply(lambda x: len(str(x).split()))

    print("\nNúmero de justificativas nulas:")
    nulos = df["JUSTIFICATIVA"].isnull().sum()
    print(f"{nulos} justificativas estão vazias ou nulas.")

    print("\nEstatísticas descritivas da contagem de palavras por justificativa:")
    descricao = contagem_palavras.describe().to_frame()
    descricao.columns = ["JUSTIFICATIVA"]
    print(descricao.round(2))

    media = contagem_palavras.mean()
    desvio = contagem_palavras.std()
    print(f"\nMédia de palavras por justificativa: {media:.2f}")
    print(f"Desvio padrão da contagem de palavras: {desvio:.2f}")

    justificativas_curtas = df[(contagem_palavras <= LIMITE_CURTA) &
                               (df["JUSTIFICATIVA"].astype(str).str.contains(r"[a-zA-ZÀ-ÿ]", na=False))]

    justificativas_longas = df[contagem_palavras >= LIMITE_LONGA]

    print(f"\nJustificativas muito curtas (≤ {LIMITE_CURTA} palavras): {len(justificativas_curtas)} encontradas")
    print(f"Justificativas muito longas (≥ {LIMITE_LONGA} palavras): {len(justificativas_longas)} encontradas")

    # Salvar os arquivos ao invés de exibir exemplos
    justificativas_curtas.to_csv("justificativas_muito_curtas.csv", index=False)
    print("\n↳ Registros curtos salvos em: 'justificativas_muito_curtas.csv'")

    justificativas_longas.to_csv("justificativas_muito_longas.csv", index=False)
    print("↳ Registros longos salvos em: 'justificativas_muito_longas.csv'")

    # Salvar com contagem também (para análise geral)
    df.assign(N_PALAVRAS=contagem_palavras).to_csv("justificativas_com_contagem.csv", index=False)

    print("\nContagem de palavras por justificativa:")
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140,
            150, 170, 200, 250, 300, 350, 400, 500, 600, 700]
    labels = [f"{bins[i]}–{bins[i+1]-1}" for i in range(len(bins)-1)]
    faixas = pd.cut(contagem_palavras, bins=bins, labels=labels, right=False)
    frequencia_faixas = faixas.value_counts().sort_index()

    for faixa, freq in frequencia_faixas.items():
        barra = "█" * (freq // 50)  # 1 bloco para cada 50 ocorrências
        print(f"{faixa:10}: {freq:5} {barra}")
'''
    plt.figure(figsize=(10, 5))
    plt.hist(contagem_palavras, bins=50, color="skyblue", edgecolor="black")
    plt.axvline(media, color='red', linestyle='dashed', linewidth=1, label='Média')
    plt.axvline(media + desvio, color='orange', linestyle='dotted', linewidth=1, label='+1 Desvio Padrão')
    plt.axvline(media - desvio, color='orange', linestyle='dotted', linewidth=1, label='-1 Desvio Padrão')
    plt.title("Distribuição do número de palavras por justificativa")
    plt.xlabel("Número de palavras")
    plt.ylabel("Frequência")
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()
'''

def filtro_ruido(texto):
    texto = str(texto).strip()
    if re.fullmatch(r"[a-zA-Z]{10,}", texto):  # apenas letras longas sem espaços
        return True
    if re.fullmatch(r"[^a-zA-Z0-9\s]{3,}", texto):  # apenas símbolos
        return True
    return False

def eh_repetitiva(texto):
    palavras = str(texto).strip().upper().split()
    if len(palavras) < 4:
        return False
    unicas = set(palavras)
    proporcao = len(unicas) / len(palavras)
    return proporcao < 0.4



def mostrar_distribuicao(df, expandir=False):
    if expandir:
        df = expandir_praticas_vedadas(df)
        print("\nDistribuição percentual da coluna 'PRATICAS VEDADAS' (após expansão):")
    else:
        print("\nDistribuição agrupada da coluna 'PRATICAS VEDADAS' (antes da expansão):")
    
    dist = df["PRATICAS VEDADAS"].value_counts(normalize=True) * 100
    print(dist.round(2).astype(str))
    return df if expandir else None

def filtrar_por_ruido(df, colunas):
    mask = df["JUSTIFICATIVA"].apply(filtro_ruido)
    df_ruido = df[mask]
    df_sem_ruido = df[~mask]
    return df_sem_ruido, df_ruido

def filtrar_por_regex(df, colunas):
    padrao = r"^\s*$|^[@\.\-]+$"
    mask = df["JUSTIFICATIVA"].astype(str).str.strip().str.match(padrao)
    df_regex = df[mask]
    df_limpo = df[~mask]
    return df_limpo, df_regex

def filtrar_por_repeticao(df, colunas):
    mask = df["JUSTIFICATIVA"].apply(eh_repetitiva)
    df_repet = df[mask]
    df_final = df[~mask]
    return df_final, df_repet


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

def detectar_similares_consecutivos_tfidf(df, janela=10, limiar=0.70, nome_arquivo="filtro_tfidf_grupos_similares.csv"):
    if "JUSTIFICATIVA" not in df.columns or "ID TERMO" not in df.columns:
        raise ValueError("Colunas obrigatórias 'JUSTIFICATIVA' e 'ID TERMO' não estão presentes.")

    df = df[df["JUSTIFICATIVA"].notna()].reset_index(drop=True)
    justificativas = df["JUSTIFICATIVA"].astype(str).tolist()

    vetorizar = TfidfVectorizer()
    matriz_tfidf = vetorizar.fit_transform(justificativas)

    similares = []
    for i in range(len(df)):
        vetor_i = matriz_tfidf[i]
        for j in range(max(0, i - janela), min(len(df), i + janela + 1)):
            if i == j:
                continue
            sim = cosine_similarity(vetor_i, matriz_tfidf[j])[0][0]
            if sim >= limiar:
                similares.append({
                    "ID_BASE":      df.at[i, "ID TERMO"],
                    "JUSTIFICATIVA_BASE": justificativas[i],
                    "ID_COMPARADA": df.at[j, "ID TERMO"],
                    "JUSTIFICATIVA_COMPARADA": justificativas[j],
                    "SIMILARIDADE": round(sim, 3)
                })

    df_similares = pd.DataFrame(similares)
    df_similares.to_csv(nome_arquivo, index=False)

    n_total_pares    = len(df_similares)
    ids_base         = set(df_similares["ID_BASE"])
    media_repeticoes = n_total_pares / len(ids_base) if ids_base else 0

    print(f"\n🔎 {n_total_pares} pares de justificativas similares detectados (TF-IDF, janela ±{janela}, limiar ≥ {limiar})")
    print(f"🧬 {len(ids_base)} justificativas distintas originaram pares similares.")
    print(f"📊 Cada uma foi repetida em média {media_repeticoes:.2f} vezes.")
    print(f"↳ Registros salvos em: '{nome_arquivo}'")

    colunas_salvar = ["ID TERMO", "PRATICAS VEDADAS", "JUSTIFICATIVA"]
    ids_presentes  = set(df["ID TERMO"])

    if ids_base:
        df_bases = df[df["ID TERMO"].isin(ids_base & ids_presentes)]
        nome_bases = "filtro_tfidf_justificativas_originais.csv"
        df_bases[colunas_salvar].drop_duplicates().to_csv(nome_bases, index=False)
        print(f"📌 {len(df_bases)} justificativas salvas como originais em '{nome_bases}'")

    # identifica IDs que estão em mais de um par, seja como base ou comparada
    todas_ids     = list(df_similares["ID_BASE"]) + list(df_similares["ID_COMPARADA"])
    freq         = Counter(todas_ids)
    ids_repetidos = {uid for uid, cnt in freq.items() if cnt > 1}

    if ids_repetidos:
        df_copias = df[df["ID TERMO"].isin(ids_repetidos & ids_presentes)]
        nome_copias = "filtro_tfidf_justificativas_duplicadas.csv"
        df_copias[colunas_salvar].drop_duplicates().to_csv(nome_copias, index=False)
        print(f"🔁 {len(df_copias)} justificativas salvas como duplicadas em '{nome_copias}'")

    # salva sempre o CSV de pares redundantes (IDs com mais de um par)
    df_redundantes = df_similares[
        df_similares["ID_BASE"].isin(ids_repetidos) |
        df_similares["ID_COMPARADA"].isin(ids_repetidos)
    ]
    nome_pares_repetidos = "filtro_tfidf_pares_redundantes.csv"
    df_redundantes.to_csv(nome_pares_repetidos, index=False)
    print(f"📎 {len(df_redundantes)} pares redundantes salvos em '{nome_pares_repetidos}'")

    total_pares_repetido = len(df_redundantes)
    return df_similares, ids_repetidos, total_pares_repetido




def registrar_reprovados(nome_filtro, df_reprovado, ids_ja_salvos, colunas_salvar):
    df_unicos = df_reprovado[~df_reprovado["ID TERMO"].isin(ids_ja_salvos)].copy()
    ids_unicos = set(df_unicos["ID TERMO"])
    if not df_unicos.empty:
        nome_arquivo = f"justificativas_filtradas_por_{nome_filtro}.csv"
        df_unicos.loc[:, df_unicos.columns.intersection(colunas_salvar)].to_csv(nome_arquivo, index=False)
        print(f"\n🧪 {len(df_unicos)} justificativas removidas por {nome_filtro}")
        print(f"↳ Registros salvos em: '{nome_arquivo}'")
    return ids_unicos

from collections import Counter

from collections import Counter

from collections import Counter

def filtrar_por_similaridade(df, df_similares, colunas_salvar):
    ids_base = set(df_similares["ID_BASE"])
    ids_comparada = set(df_similares["ID_COMPARADA"])

    # IDs duplicados reais = comparadas que não são base
    ids_repetidos_puros = ids_comparada - ids_base

    # Segurança: não pode haver sobreposição
    assert ids_repetidos_puros.isdisjoint(ids_base), (
        "⚠️ Inconsistência: um mesmo ID TERMO está como original e duplicado."
    )

    # Só mantemos os que ainda estão no DataFrame
    ids_presentes = set(df["ID TERMO"])
    ids_filtrados = ids_repetidos_puros.intersection(ids_presentes)

    # Separa os duplicados e os aprovados
    df_duplicados = df[df["ID TERMO"].isin(ids_filtrados)]
    df_filtrado = df[~df["ID TERMO"].isin(ids_filtrados)]

    # Salva os duplicados filtrados
    if not df_duplicados.empty:
        nome_duplicados = "justificativas_similares_duplicadas.csv"
        df_duplicados[colunas_salvar].to_csv(nome_duplicados, index=False)
        print(f"\n🔂 {len(df_duplicados)} justificativas removidas por similaridade (TF-IDF sequencial).")
        print(f"↳ Registros duplicados salvos em: '{nome_duplicados}'")

    # Salva também os originais identificados como base
    df_originais = df[df["ID TERMO"].isin(ids_base)]
    if not df_originais.empty:
        nome_originais = "justificativas_similares_originais.csv"
        df_originais[colunas_salvar].drop_duplicates().to_csv(nome_originais, index=False)
        print(f"📌 {len(df_originais)} justificativas identificadas como originais em grupos similares.")
        print(f"↳ Registros originais salvos em: '{nome_originais}'")

    return df_filtrado, df_duplicados, ids_filtrados

import os
import pandas as pd

import os
import pandas as pd

import os
import pandas as pd

def exibir_resumo_final(df_original, total_original):
    caminho_reprovados = "1_filtrados_consignacao.csv"
    caminho_aprovados  = "2_consignacao_aprovado.csv"
    colunas_salvar     = ["ID TERMO", "PRATICAS VEDADAS", "JUSTIFICATIVA"]

    # 1. Filtra por regex
    df_regex = pd.read_csv("justificativas_filtradas_por_regex.csv", usecols=colunas_salvar)
    df_regex.drop_duplicates(subset="ID TERMO").to_csv(caminho_reprovados, index=False)
    total_regex = df_regex["ID TERMO"].nunique()

    # 2. Filtra por ruído
    df_reprovados   = pd.read_csv(caminho_reprovados)
    ids_reprovados  = set(df_reprovados["ID TERMO"])
    df_ruido        = pd.read_csv("justificativas_filtradas_por_ruido.csv", usecols=colunas_salvar)
    novos_ruido     = df_ruido.loc[~df_ruido["ID TERMO"].isin(ids_reprovados)]
    total_ruido     = len(novos_ruido)
    if total_ruido:
        df_reprovados = pd.concat([df_reprovados, novos_ruido], ignore_index=True)
        ids_reprovados.update(novos_ruido["ID TERMO"])

    # 3. Filtra por similaridade TF-IDF
    pares_file = "filtro_tfidf_pares_redundantes.csv"
    total_pares_repetido = 0
    if os.path.exists(pares_file):
        df_pairs      = pd.read_csv(pares_file)
        ids_pairs     = set(df_pairs["ID_BASE"]) | set(df_pairs["ID_COMPARADA"])
        novos_pairs   = ids_pairs - ids_reprovados
        total_pares_repetido = len(novos_pairs)
        if novos_pairs:
            df_novos = df_original.loc[df_original["ID TERMO"].isin(novos_pairs), colunas_salvar]
            df_reprovados = pd.concat([df_reprovados, df_novos], ignore_index=True)
            ids_reprovados.update(novos_pairs)

    # 4. Filtra por repetição excessiva
    df_repet    = pd.read_csv("justificativas_filtradas_por_repeticao.csv", usecols=colunas_salvar)
    novos_repet = df_repet.loc[~df_repet["ID TERMO"].isin(ids_reprovados)]
    total_repet = len(novos_repet)
    if total_repet:
        df_reprovados = pd.concat([df_reprovados, novos_repet], ignore_index=True)
        ids_reprovados.update(novos_repet["ID TERMO"])

    # Salva reprovados
    df_reprovados.drop_duplicates(subset="ID TERMO").to_csv(caminho_reprovados, index=False)

    # Calcula totais
    total_reprovados = len(ids_reprovados)
    total_aprovados  = total_original - total_reprovados

    # Salva aprovados
    df_aprovados = df_original.loc[~df_original["ID TERMO"].isin(ids_reprovados), colunas_salvar]
    df_aprovados.drop_duplicates(subset="ID TERMO").to_csv(caminho_aprovados, index=False)

    # Resumo
    print("\n📋 Resumo final de filtragem:")
    print(f"🔹 Total originais:              {total_original}")
    print(f"🧼 Reprovados por regex:         {total_regex}")
    print(f"🧹 Reprovados por ruído:         {total_ruido}")
    print(f"🔂 Reprovados por TF-IDF:        {total_pares_repetido}")
    print(f"🔁 Reprovados por repetição:     {total_repet}")
    print(f"❌ Total reprovados:             {total_reprovados}")
    print(f"✅ Total aprovados:              {total_aprovados}")
    print(f"↳ Arquivo de aprovados:         '{caminho_aprovados}'")


def limpar_ids_reprovados(df, ids_reprovados):
    return df.loc[~df["ID TERMO"].isin(ids_reprovados)].copy()
