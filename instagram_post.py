"""
Script para automatizar postagens de todos de ERBs no Instagram.
Utiliza instagrapi para interagir com o Instagram.
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
import logging
from PIL import Image

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_post.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ERBInstagramPoster:
    """Classe para gerenciar postagens de ERBs no Instagram."""

    def __init__(self, excel_path: str, photos_dir: str, posted_file: str="posted_erbs.json"):
        """
        Inicializa o poster do Instagram.
        
        Args:
            excel_path (str): Caminho para o arquivo Excel contendo os dados dos ERBs.
            photos_dir (str): Diretório com as fotos originais.
            posted_file (str): Caminho para o arquivo JSON para controle de ERBs já postadas
        """
        load_dotenv() 

        self.excel_path = Path(excel_path)
        self.photos_dir = Path(photos_dir)
        self.posted_file = Path(posted_file)

        # carregar dados
        self.erb_data = self._load_erb_data()
        self.posted_erbs = self._load_posted_erbs()

        # configurar cliente Instagram
        self.client = Client()
        self._setup_instagram_client()
    
    def _load_erb_data(self) -> pd.DataFrame:
        """Carrega e processa os dados do Excel."""
        try:
            df = pd.read_excel(self.excel_path)

            # Preencher valores vazios
            df['class_infra_fisica'] = df['class_infra_fisica'].fillna('').replace('(vazio)', 'Não especificada')
            df['tecnologias'] = df['tecnologias'].fillna('Não especificada')
            df['faixa'] = df['faixa'].fillna('0')
            df['num_estacao'] = df['num_estacao'].astype(str)
            
            # Preencher campos de endereço
            df['logradouro'] = df['logradouro'].fillna('')
            df['bairro'] = df['bairro'].fillna('')
            
            logger.info(f"Dados carregados: {len(df)} ERBs encontradas")
            return df
        
        except Exception as e:
            logger.error(f"Erro ao carregar dados do Excel: {e}")
            raise

    def _load_posted_erbs(self) -> Dict:
        """Carrega o controle de ERBs já postadas."""
        if self.posted_file.exists():
            with open(self.posted_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'posted': [], 'last_posted': None}
    
    def _save_posted_erbs(self):
        """Salva o controle de ERBs já postadas."""
        self.posted_erbs['last_posted'] = datetime.now().isoformat()
        with open(self.posted_file, 'w', encoding='utf-8') as f:
            json.dump(self.posted_erbs, f, ensure_ascii=False, indent=2)
    
    def _setup_instagram_client(self):
        """Configura e faz login no Instagram."""
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")

        if not username or not password:
            raise ValueError("Credenciais do Instagram não encontradas no arquivo .env")

        try:
            # tentar carregar sessão salva
            session_file = Path("instagram_session.json")
            if session_file.exists():
                try:
                    self.client.load_settings(session_file)
                    self.client.login(username, password)
                    logger.info("Sessão do Instagram carregada com sucesso.")
                    return
                except Exception:
                    logger.warning("Sessão expirada, fazendo login novamente...")
            
            # login normal
            self.client.login(username, password)
            self.client.dump_settings(session_file)
            logger.info("Login no Instagram realizado com sucesso.")

        except ChallengeRequired:
            logger.error("Desafio de segurança do Instagram detectado. Verifique seu email/telefone.")
            raise
        except Exception as e:
            logger.error(f"Erro ao fazer login no Instagram: {e}")
            raise
    
    def _validate_and_prepare_photo(self, photo_path: Path) -> Optional[Path]:
        """
        Valida e prepara a foto para postagem.
        Instagram recomenda: 1080px x 1.080px (quadrado), 1.080px x 1.350px (retrato)
        Args:
            photo_path (Path): Caminho para a foto original.
        Returns:
            Optional[Path]: Caminho para a foto preparada ou None se não for possível preparar.
        """
        if not photo_path.exists():
            logger.error(f"Foto não encontrada: {photo_path}")
            return None
        
        try:
            with Image.open(photo_path) as img:
                # Verificar tamanho mínimo
                if img.width < 320 or img.height < 320:
                    logger.warning(f"Foto muito pequena: {photo_path}")
                    return None
                
                # target_size = (1080, 1080)
                # img.thumbnail(target_size, Image.Resampling.LANCZOS)
                # img.save(photo_path, 'JPEG', quality=95)
                
                return photo_path
                
        except Exception as e:
            logger.error(f"Erro ao validar foto {photo_path}: {e}")
            return None
    
    def _create_caption(self, erb: pd.Series) -> str:
        """Cria a legenda formatada para a ERB."""

        # formatar tecnologias
        tecnologias = str(erb['tecnologias'])

        # formatar faixas
        faixas = str(erb['faixa'])
        if faixas and faixas != '0':
            faixa_texto = f"{faixas} MHz"
        else:
            faixa_texto = "Não especificada"
        
        # formatar infraestrutura física
        infra_fisica = str(erb['class_infra_fisica']) if erb['class_infra_fisica'] else "Não especificada"

        # formatar endereço
        endereco_parts = []
        if erb['logradouro'] and str(erb['logradouro']).strip():
            endereco_parts.append(str(erb['logradouro']).strip())
        if erb['bairro'] and str(erb['bairro']).strip():
            endereco_parts.append(str(erb['bairro']).strip())
        endereco_parts.append(f"{erb['municipio']} - {erb['sigla_uf']}")
        endereco = ', '.join(endereco_parts)

        #construir legenda
        caption = f"""{erb['num_estacao']}
        
Tecnologias: {tecnologias}
Faixas: {faixa_texto}
Infraestrutura: {infra_fisica}
Localização:
{endereco}
"""
        return caption
    
    def post_single_erb(self, num_estacao: str, test_mode: bool = False) -> bool:
        """
        Publica uma única ERB no Instagram.

        Args:
            num_estacao (str): Número da estação a ser postada.
            test_mode (bool): Se True, não fará a postagem real, apenas simula.

        Returns:
            bool: True se a postagem foi bem-sucedida, False caso contrário.
        """
        # verificar se já foi postada
        if num_estacao in self.posted_erbs['posted']:
            logger.info(f"ERB {num_estacao} já foi postada anteriormente")
            return False
        
        # encontrar dados da ERB
        erb_row = self.erb_data[self.erb_data['num_estacao'] == num_estacao]
        if erb_row.empty:
            logger.error(f"ERB {num_estacao} não encontrada nos dados")
            return False
        
        erb = erb_row.iloc[0]

        # encontrar foto
        photo_path = self.photos_dir / f"{num_estacao}.jpeg"
        if not photo_path.exists():
            # tentar outras extensões
            for ext in ['.jpg', '.jpeg', '.png']:
                alt_path = self.photos_dir / f"{num_estacao}{ext}"
                if alt_path.exists():
                    photo_path = alt_path
                    break
            else:
                logger.error(f"Foto para ERB {num_estacao} não encontrada")
                return False
            
        # validar foto
        validated_photo = self._validate_and_prepare_photo(photo_path)
        if not validated_photo:
            return False
        
        # criar legenda
        caption = self._create_caption(erb)

        if test_mode:
            logger.info(f"[TESTE] Simulando postagem da ERB #{num_estacao}")
            logger.info(f"Foto: {validated_photo}")
            logger.info(f"Legenda:\n{caption}")
            return True
        
        # publicar no instagram
        try:
            logger.info(f"Postando ERB #{num_estacao} no Instagram...")

            # upload da foto
            media = self.client.photo_upload(str(validated_photo), caption)

            # registrar como postada
            self.posted_erbs['posted'].append(num_estacao)
            self._save_posted_erbs()

            logger.info(f"ERB #{num_estacao} postada com sucesso! ID: {media.pk}")
            return True
        
        except LoginRequired:
            logger.error("Sessão expirada. Tentando fazer login novamente...")
            self._setup_instagram_client()
            return self.post_single_erb(num_estacao, test_mode)
        
        except Exception as e:
            logger.error(f"Erro ao postar ERB #{num_estacao}: {e}")
            return False
        
def main():
    """Função principal com interface de linha de comando"""
    parser = argparse.ArgumentParser(
        description="Automatizador de postagens de ERBs no Instagram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Postar uma ERB específica em modo teste
  python instagram_poster.py --erb 1012979137 --test
  """
    )

    parser.add_argument('--erb', type=str, help='Número da ERB específica para postar')
    parser.add_argument('--test', action='store_true', help='Modo teste (não publica realmente)')

    args = parser.parse_args()

    #Configurações
    EXCEL_PATH = "ERBs_Mar26_goiania_preprocessed.xlsx"
    PHOTOS_DIR = "erb_photos"

    try:
        # criar poster
        poster = ERBInstagramPoster(EXCEL_PATH, PHOTOS_DIR)

        if args.erb:
            # postar ERB específica
            poster.post_single_erb(args.erb, test_mode=args.test)
        else:
            parser.print_help()
        
    except Exception as e:
        logger.error(f"Erro na execução do script: {e}")
        raise

if __name__ == "__main__":
    main()