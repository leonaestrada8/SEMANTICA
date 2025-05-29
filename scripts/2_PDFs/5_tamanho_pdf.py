import os
from pathlib import Path
import statistics

def human_readable_size(size_bytes: int) -> str:
    """Converte bytes em KB, MB, GB, conforme apropriado."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024 or unit == 'TB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def analyze_pdf_sizes(base_dir: Path):
    pdf_paths = list(base_dir.rglob('*.pdf'))
    if not pdf_paths:
        print(f"Nenhum arquivo .pdf encontrado em {base_dir}")
        return

    sizes = [p.stat().st_size for p in pdf_paths]
    count = len(sizes)
    total = sum(sizes)
    minimum = min(sizes)
    maximum = max(sizes)
    mean = statistics.mean(sizes)
    median = statistics.median(sizes)
    stdev = statistics.stdev(sizes) if count > 1 else 0.0
    q1 = statistics.quantiles(sizes, n=4)[0]
    q3 = statistics.quantiles(sizes, n=4)[2]

    print(f"Análise de arquivos PDF em: {base_dir}")
    print(f"Total de arquivos      : {count}")
    print(f"Tamanho total          : {human_readable_size(total)} ({total} bytes)")
    print(f"Tamanho mínimo         : {human_readable_size(minimum)} ({minimum} bytes)")
    print(f"Tamanho máximo         : {human_readable_size(maximum)} ({maximum} bytes)")
    print(f"Média aritmética       : {human_readable_size(mean)} ({mean:.2f} bytes)")
    print(f"Mediana                : {human_readable_size(median)} ({median} bytes)")
    print(f"Desvio-padrão          : {human_readable_size(stdev)} ({stdev:.2f} bytes)")
    print(f"1º quartil (25%)       : {human_readable_size(q1)} ({q1} bytes)")
    print(f"3º quartil (75%)       : {human_readable_size(q3)} ({q3} bytes)")

    # Estatísticas adicionais
    sizes_sorted = sorted(sizes)
    lower_10 = sizes_sorted[int(0.1 * count)]
    upper_90 = sizes_sorted[int(0.9 * count)]
    print(f"Percentil 10%           : {human_readable_size(lower_10)} ({lower_10} bytes)")
    print(f"Percentil 90%           : {human_readable_size(upper_90)} ({upper_90} bytes)")

if __name__ == "__main__":
    base = Path(r"C:\Users\s056558027\Documents\SERPRO_DVLP\consignacao_semantica\convertidos_pdf\UNIQUE")
    analyze_pdf_sizes(base)
