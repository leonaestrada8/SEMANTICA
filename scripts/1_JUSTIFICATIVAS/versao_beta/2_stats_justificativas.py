import csv
from datetime import datetime

def estatisticas_registros(
    caminho_arquivo: str,
    data_inicio_str: str,
    data_fim_str: str,
    formato_data: str = "%d/%m/%Y"
) -> None:
    """
    Lê o arquivo CSV delimitado por '#' (ignorando a linha de cabeçalho),
    conta o número total de registros e calcula estatísticas baseadas
    no período [data_inicio, data_fim].

    Parâmetros:
      caminho_arquivo   caminho para o arquivo CSV
      data_inicio_str   data de início do período (string)
      data_fim_str      data de fim do período (string)
      formato_data      formato para parse das datas (por padrão 'DD/MM/YYYY')
    """

    data_inicio = datetime.strptime(data_inicio_str, formato_data).date()
    data_fim    = datetime.strptime(data_fim_str,    formato_data).date()

    if data_fim < data_inicio:
        raise ValueError("A data de fim deve ser igual ou posterior à data de início.")

    total_registros = 0
    with open(caminho_arquivo, encoding="utf-8") as f:
        leitor = csv.reader(f, delimiter="#")
        next(leitor, None)
        for _ in leitor:
            total_registros += 1

    dias_periodo = (data_fim - data_inicio).days + 1
    media_por_dia = total_registros / dias_periodo
    meses_aproximados = dias_periodo / 30
    media_por_mes     = total_registros / meses_aproximados

    print(f"Período considerado: {data_inicio_str} a {data_fim_str}")
    print(f"Total de registros: {total_registros}")
    print(f"Dias no período    : {dias_periodo}")
    print(f"Média por dia      : {media_por_dia:.2f}")
    print(f"Média por mês (*)  : {media_por_mes:.2f}")
    print()
    print("(*) média mensal aproximada, considerando 30 dias por mês.")

if __name__ == "__main__":
    # Exemplo de uso com caminho absoluto no Windows:
    caminho = r"C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\docs_cliente\justificativasTermoReclamacao__jan2024_ate_150525.csv"
    inicio  = "01/01/2025"
    fim     = "15/05/2025"

    estatisticas_registros(caminho, inicio, fim)
