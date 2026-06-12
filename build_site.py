"""
Script principal para construir o site de registros de antenas 5G.
Executa todo o pipeline: processamento de dados -> geração do mapa.
"""

import subprocess
import sys
from pathlib import Path
import argparse

def run_command(command, description):
    """Executa um comando de terminal e mostra o progresso."""
    print(f"\n{'='*50}")
    print(f"Executando: {description}")
    print(f"{'='*50}")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Sucesso: {description}")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"Erro ao executar: {description}")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Construir site de registros de antenas 5G")
    parser.add_argument('--skip-photos', action='store_true', help="Pular processamento de fotos (usar cache existente)")
    args = parser.parse_args()

    print("Iniciando contrução do site de Registros de Antenas 5G...")

    # verificar dependências
    print("\nVerificando dependências...")
    try:
        import pandas
        import folium
        import PIL
        import tqdm
        print("Todas as dependências estão instaladas.")
    except ImportError as e:
        print(f"Dependência faltando: {e.name}.")
        print("Execute: pip install -r requirements.txt")
        sys.exit(1)

    # verificar arquivos necessários
    excel_file = Path('ERBs_Mar26_goiania_preprocessed.xlsx')
    photos_dir = Path('erb_photos')

    if not excel_file.exists():
        print(f"Arquivo Excel não encontrado: {excel_file}")
        sys.exit(1)

    if not photos_dir.exists():
        print(f"Pasta de fotos não encontrada: {photos_dir}")
        sys.exit(1)

    # Passo 1: Processar dados e fotos
    if not args.skip_photos:
        print("\nProcessando dados e fotos...")
        success = run_command("python process_data.py", "Processamento de dados excel e redimenisonamento de fotos")
        if not success:
            print("Falha no processamento de dados. Abortando.")
            sys.exit(1)
    else:
        print("\nPulando processamento de fotos. Usando cache existente (se disponível).")
    
    # Passo 2: Gerar mapa interativo
    print("\nGerando mapa interativo...")
    success = run_command("python generate_map.py", "Geração do mapa interativo com Folium")
    if not success:
        print("Falha na geração do mapa. Abortando.")
        sys.exit(1)

    # verificar arquivos gerados
    generated_files = [Path('data.json'), Path('index.html'), Path('processed_photos')]

    print("\nArquivos gerados:")
    for file_path in generated_files:
        if file_path.exists():
            if file_path.is_dir():
                photo_count = len(list(file_path.glob("*.jpg")))
                print(f"  ✓ {file_path}/ ({photo_count} fotos)")
            else:
                size_kb = file_path.stat().st_size / 1024
                print(f"  ✓ {file_path} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()