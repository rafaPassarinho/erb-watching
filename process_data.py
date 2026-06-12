import pandas as pd
import json
import os
from pathlib import Path
from PIL import Image
import concurrent.futures
from tqdm import tqdm
import hashlib
from typing import List, Dict, Optional
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ERBProcessor:
    def __init__(self, excel_path: str, photos_input_dir: str, photos_output_dir: str, max_photo_width: int = 800, max_photo_height: int = 533):
        """
        Inicializa o processador de ERBs.
        
        Args:
            excel_path (str): Caminho para o arquivo Excel contendo os dados das ERBs.
            photos_input_dir (str): Diretório onde as fotos originais estão armazenadas.
            photos_output_dir (str): Diretório onde as fotos processadas serão salvas.
            max_photo_width (int): Largura máxima para redimensionamento das fotos processadas.
            max_photo_height (int): Altura máxima para redimensionamento das fotos processadas.
        """
        self.excel_path = Path(excel_path)
        self.photos_input_dir = Path(photos_input_dir)
        self.photos_output_dir = Path(photos_output_dir)
        self.max_photo_width = max_photo_width
        self.max_photo_height = max_photo_height

        # criar diretório de saída se não existir
        self.photos_output_dir.mkdir(parents=True, exist_ok=True)

        # cache para evitar reprocessamento
        self.processed_cache = set()

    def get_photo_hash(self, photo_path: Path) -> str:
        """Gera hash MD5 da foto para identificar alterações."""
        hash_md5 = hashlib.md5()
        with open(photo_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def resize_photo(self, input_path: Path, output_path: Path) -> bool:
        """
        Redimensiona uma única foto mantendo a proporção.
        Retorna True se a foto foi processada, False se já existia.
        """
        try:
            #verificar se a foto já foi processada
            if output_path.exists():
                return False
            
            with Image.open(input_path) as img:
                # manter orientação original
                if hasattr(img, "_getexif") and img._getexif():
                    exif = img._getexif()
                    orientation = exif.get(274) # tag de orientação exif
                    if orientation:
                        # rotacionar se necessário
                        if orientation == 3:
                            img = img.rotate(180, expand=True)
                        elif orientation == 6:
                            img = img.rotate(270, expand=True)
                        elif orientation == 8:
                            img = img.rotate(90, expand=True)
                # redimensionar mantendo proporção
                img.thumbnail((self.max_photo_width, self.max_photo_height), Image.Resampling.LANCZOS)

                # salvar compressão otimizada
                img.save(output_path, 'JPEG', optimize=True, quality=85)
            return True
        
        except Exception as e:
            logger.error(f"Erro ao processar foto {input_path}: {e}")
            return False
        
    def process_photos_batch(self, photo_paths: List[Path], max_workers: int = 4):
        """
        Processa multiplas fotos em paralelo
        """
        tasks = []
        for photo_path in photo_paths:
            if photo_path.exists():
                output_filename = f"{photo_path.stem}.jpg"
                output_path = self.photos_output_dir / output_filename
                tasks.append((photo_path, output_path))
        
        if not tasks:
            logger.info("Nenhuma foto para processar.")
            return
        
        # processar em paralelo com barras de progresso
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.resize_photo, input_path, output_path) for input_path, output_path in tasks]

            processed_count = 0
            with tqdm(total=len(futures), desc="Processando fotos") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        processed_count += 1
                    pbar.update(1)
        logger.info(f"Fotos processadas: {processed_count}/{len(tasks)}")

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e normaliza o DataFrame."""
        # preencher valores nulos
        df['class_infra_fisica'] = df["class_infra_fisica"].fillna('').replace('(vazio)', 'Não especificada')
        df['tecnologias'] = df["tecnologias"].fillna('')
        df['faixa'] = df["faixa"].fillna('0')

        # garantir que num_estação seja string para o nome do arquivo
        df['num_estacao'] = df['num_estacao'].astype(str)

        return df

    def process_excel_to_json(self, output_json_path: str = 'data.json'):
        """Processa o Excel e gera arquivo JSON otimizado."""
        logger.info(f"Lendo o arquivo Excel: {self.excel_path}")

        try:
            df = pd.read_excel(self.excel_path)
            logger.info(f"Registros encontrados: {len(df)}")
        except Exception as e:
            logger.error(f"Erro ao ler o arquivo Excel: {e}")
            return
        
        # limpar dados
        df = self.clean_dataframe(df)

        # separar registros com e sem fotos
        photos_to_process = []
        erb_data = []

        for _, row in df.iterrows():
            erb_dict = {
                'num_estacao': row['num_estacao'],
                'operadora': row['operadora'],
                'sigla_uf': row['sigla_uf'],
                'municipio': row['municipio'],
                'bairro': str(row['bairro']) if pd.notna(row['bairro']) else '',
                'logradouro': str(row['logradouro']) if pd.notna(row['logradouro']) else '',
                'latitude': row['latitude'] if pd.notna(row['latitude']) else 0,
                'longitude': row['longitude'] if pd.notna(row['longitude']) else 0,
                'class_infra_fisica': row['class_infra_fisica'],
                'tecnologias': row['tecnologias'],
                'faixa': row['faixa'],
                'tem_foto': False,
                'foto_path': None
            }

            # verificar se tem foto
            foto_path = str(row['caminho_foto']) if pd.notna(row['caminho_foto']) else ''
            if foto_path and foto_path != '':
                # extrair nome do arquivo do caminho
                if '\\' in foto_path:
                    foto_filename = foto_path.split('\\')[-1]
                elif '/' in foto_path:
                    foto_filename = foto_path.split('/')[-1]
                else:
                    foto_filename = foto_path
                
                # construir caminho para foto original
                original_photo_path = self.photos_input_dir / foto_filename

                if original_photo_path.exists():
                    erb_dict['tem_foto'] = True
                    erb_dict['foto_path'] = f"processed_photos/{original_photo_path.stem}.jpg"  # caminho relativo para JSON
                    photos_to_process.append(original_photo_path)
                else:
                    logger.warning(f"Foto não encontrada: {original_photo_path}")

            erb_data.append(erb_dict)

        # processar fotos (fora do loop)
        if photos_to_process:
            # remove duplicatas caso existam várias ERBs apontando para a mesma foto
            unique_photos = list(set(photos_to_process))
            logger.info(f"Processando {len(unique_photos)} fotos únicas...")
            self.process_photos_batch(unique_photos)

        # salvar JSON otimizado
        output_path = Path(output_json_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(erb_data, f, ensure_ascii=False, indent=2)

        # estatísticas
        total_erbs = len(erb_data)
        erbs_with_photos = sum(1 for erb in erb_data if erb['tem_foto'])

        logger.info(f"Processamento concluído!")
        logger.info(f"Total de ERBs: {total_erbs}")
        logger.info(f"ERBs com fotos: {erbs_with_photos}")
        logger.info(f"JSON salvo em: {output_path.absolute()}")

        return erb_data
    
def main():
    """Função principal para execução do processamento."""

    # configurações
    EXCEL_PATH = "ERBs_Mar26_goiania_preprocessed.xlsx"
    PHOTOS_INPUT_DIR = "erb_photos"
    PHOTOS_OUTPUT_DIR = "processed_photos"

    # criar processador
    processor = ERBProcessor(
        excel_path=EXCEL_PATH,
        photos_input_dir=PHOTOS_INPUT_DIR,
        photos_output_dir=PHOTOS_OUTPUT_DIR,
        max_photo_width=800,
        max_photo_height=533
    )

    # processar dados
    processor.process_excel_to_json(output_json_path='data.json')

if __name__ == "__main__":
    main()

                    


