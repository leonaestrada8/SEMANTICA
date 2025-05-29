import tiktoken

# seleciona o codificador do modelo desejado
encoding = tiktoken.encoding_for_model("gpt-4")

# texto de exemplo (pode ser substituído pelo conteúdo lido de arquivo)
json_text = """
{ 
Você é um especialista em empréstimos consignados.
Sua tarefa é avaliar a justificativa enviada por um usuário com base em um ou mais dos seguintes critérios:
• Consignação em folha sem autorização prévia e formal do consignado;
• Consignação em folha sem o correspondente crédito do valor ao consignado;
• Manutenção de desconto em folha referente a contrato já liquidado;

Não faz parte do escopo e deve ser negado:

• rediscussão de contrato assinado (contrato indevido, taxas abusivas, etc.);
• requisições de boletos;

Instruções:
Verifique se a justificativa apresentada se enquadra em um ou mais dos critérios acima.
Ao final, produza única saída no formato JSON abaixo, preenchendo todos os campos:

{
  "requestId": "<UUID>",
  "timestamp": "<ISO 8601 com fuso -03:00>",
  "diagnosticoLLM": "SIM" | "NÃO",
  "justificativaLLM": "<texto livre até 144 caracteres>",
  "confidence": <valor numérico entre 0.0 e 1.0>,
  "status": "success" | "error"
}

• requestId: id da requisicao gerado aleatoriamente
• timestamp: hora da execução
• diagnosticoLLM: resposta sim ou não se o texto do usuário se encaixa nas categorias determinadas
• justificativaLLM: racional para a resposta acima
• confidence: confiança na resposta do LLM
• status: OK ou NOK

Abaixo, a justificativa enviada pelo usuário:

"Olá. Eu estou tentando abrir a solicitação da carta para quitação do contrato e não estou conseguindo abrir o link da selfie, por favor me ajudem, preciso liquidar o contrato."
}
"""

# contagem de tokens conforme o esquema BPE do modelo
token_count = len(encoding.encode(json_text))

# contagem de palavras simples, considerando separação por espaços em branco
word_list = json_text.split()
word_count = len(word_list)

# contagem de caracteres, incluindo espaços e pontuação
char_count = len(json_text)

print(f"Total de tokens: {token_count}")
print(f"Total de palavras: {word_count}")
print(f"Total de caracteres: {char_count}")
