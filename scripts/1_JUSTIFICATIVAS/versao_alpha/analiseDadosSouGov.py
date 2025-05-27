#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import os


# In[3]:


print(os.getcwd())  # Mostra o diretório atual


# In[4]:


# Carrega a planilha em um DataFrame
#df = pd.read_csv('justificativas.csv')
df = pd.read_csv(r'C:\Users\S827594051\FormacaoDSA4\Lab5\justificativas.csv', encoding='latin1')


# In[14]:


df.head(50)


# In[12]:


# Filtra as linhas com ID vedação igual a 10, 11 ou 12
df_filtrado = df[df['PRATICAS VEDADAS'].astype(str).isin(['10', '11', '12'])]


# In[13]:


# Imprime o número de linhas no DataFrame filtrado
print('Número de linhas:', df_filtrado.shape[0])


# In[15]:


# Filtra as linhas com ID vedação igual a 10
df_filtrado_10 = df[df['PRATICAS VEDADAS'].astype(str).isin(['10'])]


# In[16]:


# Imprime o número de linhas no DataFrame filtrado
print('Número de linhas com prática = 10:', df_filtrado_10.shape[0])


# In[23]:


# Converter todos os valores para string (por segurança)
df['PRATICAS VEDADAS'] = df['PRATICAS VEDADAS'].astype(str)

# Função para contar quantos dos IDs 10, 11, 12 aparecem na linha
def conta_ids_vedacao(val):
    ids = [x.strip().replace('.', '') for x in val.replace(';', ',').split(',')]
    return sum(id_ in ['10', '11', '12'] for id_ in ids)

# Aplicar a função e filtrar onde há mais de um ID
df_multiplos_ids = df[df['PRATICAS VEDADAS'].apply(conta_ids_vedados) > 1]

# Exibir o resultado
print(df_multiplos_ids.head())
print(f'Total de linhas com mais de um ID vedacao: {len(df_multiplos_ids)}')


# In[24]:


quantidade = (df['PRATICAS VEDADAS'].apply(conta_ids_vedacao) > 1).sum()


# In[25]:


print(f'Quantidade de linhas com mais de um ID vedacao (10, 11 ou 12): {quantidade}')


# In[5]:


# Tipos de dados, valores nulos.
df.info()


# In[6]:


# Estatísticas básicas
df.describe()


# In[7]:


# Total de valores ausentes por coluna.
df.isnull().sum()


# In[12]:


# Descobrir quais práticas ocorrem com maior frequência.
from collections import Counter

def extrair_ids(val):
    ids = [x.strip().replace('.', '') for x in str(val).replace(';', ',').split(',')]
    return [id_ for id_ in ids if id_.isdigit()]

todos_ids = df['PRATICAS VEDADAS'].dropna().apply(extrair_ids).sum()
contagem_ids = Counter(todos_ids)

import pandas as pd
df_contagem = pd.DataFrame.from_dict(contagem_ids, orient='index', columns=['Frequência']).sort_values('Frequência', ascending=False)
print(df_contagem)


# In[10]:


df = df.drop('Unnamed: 4', axis=1)


# In[13]:


# Verificar quais combinações de IDs são mais comuns (duplas ou trios).
df['PRATICAS VEDADAS LIMPOS'] = df['PRATICAS VEDADAS'].apply(extrair_ids)
df['TOTAL_IDS'] = df['PRATICAS VEDADAS LIMPOS'].apply(len)
df['COMBINACAO'] = df['PRATICAS VEDADAS LIMPOS'].apply(lambda x: ','.join(sorted(x)))

df['COMBINACAO'].value_counts().head(10)  # Top 10 combinações


# In[15]:


import matplotlib.pyplot as plt

# Cria o gráfico de barras
ax = df['TOTAL_IDS'].value_counts().sort_index().plot(kind='bar', title='Quantidade de práticas por reclamação')

# Adiciona os valores no topo de cada barra
for p in ax.patches:
    ax.annotate(
        str(int(p.get_height())),              # valor da barra
        (p.get_x() + p.get_width() / 2, p.get_height()),  # posição x e y
        ha='center', va='bottom'               # alinhamento horizontal e vertical
    )

# Mostra o gráfico
plt.xlabel('Quantidade de práticas na reclamação')
plt.ylabel('Número de reclamações')
plt.tight_layout()
plt.show()


# In[16]:


# Linhas onde o campo está vazio (nulo ou string vazia após remover espaços)
vazios = df[df['PRATICAS VEDADAS'].isnull() | (df['PRATICAS VEDADAS'].str.strip() == '')]

print(f'⚠️ Total de linhas com campo PRATICAS VEDADAS vazio: {len(vazios)}')


# In[19]:


# Lista de palavras ou frases a buscar
palavras_chave = ['não autorizei', 'nao autorizei', 'não recebi', 'desconto indevido', 'desconto não autorizado']

# Coluna que contém o texto da reclamação
coluna_texto = 'JUSTIFICATIVA'  # ou 'DESCRICAO'

# Converte texto para minúsculo e verifica a presença das palavras-chave
df['PALAVRAS_CHAVE_ENCONTRADAS'] = df[coluna_texto].str.lower().apply(
    lambda texto: any(p in str(texto) for p in palavras_chave)
)

# Filtra reclamações com palavras-chave relevantes
reclamacoes_relevantes = df[df['PALAVRAS_CHAVE_ENCONTRADAS'] == True]

print(f'🔍 Reclamações com palavras-chave suspeitas: {len(reclamacoes_relevantes)}')


# In[25]:


# Instale TextBlob, se ainda não tiver
get_ipython().system('pip install textblob')
get_ipython().system('python -m textblob.download_corpora')


# In[47]:


# Análise de sentimento
from textblob import TextBlob

# Aplica a análise de sentimento
df['SENTIMENTO'] = df[coluna_texto].astype(str).apply(lambda x: TextBlob(x).sentiment.polarity)

# Interpreta o sentimento
df['CATEGORIA_SENTIMENTO'] = df['SENTIMENTO'].apply(
    lambda x: 'negativo' if x < -0.1 else ('positivo' if x > 0.1 else 'neutro')
)

# Exemplo: visualizar textos com sentimento negativo
print(df[df['CATEGORIA_SENTIMENTO'] == 'negativo'][[coluna_texto, 'SENTIMENTO']].head())


# In[48]:


df.sort_values('CATEGORIA_SENTIMENTO')[[coluna_texto, 'CATEGORIA_SENTIMENTO', 'SENTIMENTO']].tail(100)


# In[46]:


print(df['CATEGORIA_SENTIMENTO'].value_counts())


# In[51]:


print(reclamacoes_relevantes)


# In[53]:


# identificar linhas em que a justificativa menciona envio de boletos
import pandas as pd

# Suponha que a coluna com justificativas se chame 'JUSTIFICATIVA'
coluna_texto = 'JUSTIFICATIVA'

# Convertemos o texto para string e minúsculas, e procuramos menções a 'boleto'
mascara_boletos = df[coluna_texto].astype(str).str.lower().str.contains('boleto')

# Filtramos as linhas que contêm essas menções
df_boletos = df[mascara_boletos]

# Mostramos a quantidade de linhas com menção a boletos
print(f"Quantidade de linhas com envio de boletos mencionados: {df_boletos.shape[0]}")

# Opcional: visualizar as justificativas encontradas
df_boletos[[coluna_texto]].head(40)


# In[56]:


# Conta quantas justificativas estão repetidas (duplicadas)
justificativas_duplicadas = df[df['JUSTIFICATIVA'].duplicated(keep=False)]

# Mostra a quantidade total de linhas repetidas
print(f"Quantidade de linhas com justificativas repetidas: {justificativas_duplicadas.shape[0]}")

# (Opcional) Visualiza as justificativas duplicadas e quantas vezes aparecem
duplicadas_agrupadas = justificativas_duplicadas['JUSTIFICATIVA'].value_counts()
print("\nJustificativas repetidas mais comuns:")
print(duplicadas_agrupadas.head(40))


# In[ ]:


# duplicated(keep=False) identifica todas as ocorrências duplicadas (não apenas as segundas).
# shape[0] retorna a quantidade de linhas duplicadas.
# value_counts() mostra as justificativas mais repetidas.

