import os
import shutil
from pathlib import Path

base_directory = Path(r"C:/Users/s056558027/Documents/SERPRO_DVLP/consignacao_semantica/convertidos_pdf")
converted_directory = Path(r"C:/Users/s056558027/Documents/SERPRO_DVLP/consignacao_semantica/convertidos_pdf")

converted_directory.mkdir(parents=True, exist_ok=True)

folders_count = 0
files_count = 0

for dirpath, _, filenames in os.walk(base_directory):
    folders_count += 1
    current_dir = Path(dirpath)
    print(f"Analisando pasta: {current_dir}")
    for filename in filenames:
        src = current_dir / filename
        if src.suffix == "":
            dest = converted_directory / f"{filename}.pdf"
            try:
                shutil.move(str(src), str(dest))
                files_count += 1
                print(f"{filename} -> {filename}.pdf")
            except Exception as e:
                print(f"Erro ao mover {src}: {e}")

print(f"Total de pastas analisadas: {folders_count}")
print(f"Total de arquivos convertidos: {files_count}")
