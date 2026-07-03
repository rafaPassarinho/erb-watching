"""
Bot de Telegram para registro fotográfico de ERBs.

Fluxo:
1. Usuário envia foto (.jpeg)
2. Bot solicita o número da estação (num_estacao)
3. Bot valida o número no Excel
4. Salva a foto em erb_photos/<num_estacao>.jpeg
5. Atualiza a coluna 'caminho_foto' no Excel
6. Executa build_site.py
"""

import os
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env

TOKEN = os.getenv("TELEGRAM_TOKEN")
EXCEL_PATH = Path("ERBs_Mar26_goiania_preprocessed.xlsx")
PHOTOS_DIR = Path("erb_photos")
SHEET_NAME = "Sheet1"
COL_NUM_ESTACAO = "num_estacao"
COL_CAMINHO_FOTO = "caminho_foto"

# estados da conversa (máquina de estados do ConversationHandler)
AGUARDANDO_NUMERO = 1

# logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def garantir_pasta_fotos():
    """Cria a pasta erb_photos se ela não existir."""
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

def carregar_estacoes_validas():
    """Lê o Excel e retorna um conjunto com todos os valores
    da coluna 'num_estacao' como inteiros.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    return set(df[COL_NUM_ESTACAO].dropna().astype(int).tolist())

def atualizar_excel(num_estacao: int):
    """Abre o Excel, localiza a linha com num_estacao
    e insere o caminho da foto na coluna 'caminho_foto'.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    
    # monta o caminho padrão da foto
    caminho = f"erb-watching\\erb_photos\\{num_estacao}.jpeg"

    # localiza a linha correta e atualiza e atualiza
    mascara = df[COL_NUM_ESTACAO].astype(int) == num_estacao
    df.loc[mascara, COL_CAMINHO_FOTO] = caminho

    # salva de volta o mesmo arquivo
    df.to_excel(EXCEL_PATH, sheet_name=SHEET_NAME, index=False)
    logger.info("Excel atualizado: estação %d -> %s", num_estacao, caminho)

def executar_build_site() -> tuple[bool, str]:
    """
    Executa build_site.py e retorna uma tupla (sucesso, mensagem).
    """
    resultado = subprocess.run(
        ["python", "build_site.py"],
        capture_output=True,
        text=True
    )
    if resultado.returncode == 0:
        return True, resultado.stdout
    else:
        return False, resultado.stderr

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem de boas-vindas com /start."""
    await update.message.reply_text(
        "Olá! Envie uma foto (.jpeg) da ERB para registrar."
    )

async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    PASSO 1: Usuário envia a foto.
    O bot baixo o arquivo temporariamente e pergunta o número da estação.
    """
    # Telegram comprime fotos enviadas como imagem; para preservar qualidade,
    # o usuário deve enviar como DOCUMENTO. Tratamos ambos os casos:
    if update.message.document:
        arquivo = update.message.document
        # verifica se é JPEG pelo mime_type
        if arquivo.mime_type not in ("image/jpeg", "image/jpg"):
            await update.message.reply_text("Por favor, envie apenas arquivos .jpeg")
            return ConversationHandler.END
        file_id = arquivo.file_id
    elif update.message.photo:
        # pega a versão de maior resolução
        file_id = update.message.photo[-1].file_id
    else:
        await update.message.reply_text("Não reconheci o arquivo. Por favor, envie uma imagem .jpeg.")
        return ConversationHandler.END
    
    # armazena o file_id no contexto da conversa para usar depois
    context.user_data["file_id"] = file_id

    await update.message.reply_text(
        "Foto recebida!\n\n"
        "Agora me informe o **número da estação** (num\\_estacao) "
        "correspondente a esta foto:",
        parse_mode="Markdown"
    )

    # avança para o próximo estado da conversa
    return AGUARDANDO_NUMERO

async def receber_numero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    PASSO 2: Usuário informa o número da estação.
    O bot valida, salva a foto, atualiza o Excel e executa build_site.py.
    """
    texto = update.message.text.strip()

    # valida se é um número inteiro
    if not texto.isdigit():
        await update.message.reply_text("O número da estação deve conter apenas dígitos. Tente novamente:")
        return AGUARDANDO_NUMERO # mantém no mesmo estado
    
    num_estacao = int(texto)

    # valida se o número da estação existe no Excel
    try:
        estacoes_validas = carregar_estacoes_validas()
    except Exception as e:
        logger.error("Erro ao carregar estações válidas: %s", e)
        await update.message.reply_text("Erro ao acessar o arquivo Excel. Verifique se está tudo ok.")
        return ConversationHandler.END
    
    if num_estacao not in estacoes_validas:
        await update.message.reply_text(
            f"Estação {num_estacao} não encontrada na planilha.\n"
            "Verifique o número e tente novamente:",
            parse_mode="Markdown",
        )
        return AGUARDANDO_NUMERO # permite nova tentativa
    
    await update.message.reply_text(f"Estação {num_estacao} encontrada. Salvando foto...")

    try:
        garantir_pasta_fotos()
        destino = PHOTOS_DIR / f"{num_estacao}.jpeg"

        # baixa o arquivo do Telegram
        arquivo_telegram = await context.bot.get_file(context.user_data["file_id"])
        await arquivo_telegram.download_to_drive(destino)
    except Exception as e:
        logger.error("Erro ao salvar a foto: %s", e)
        await update.message.reply_text("Erro ao salvar a foto.")
        return ConversationHandler.END
    
    try:
        atualizar_excel(num_estacao)
    except Exception as e:
        logger.error("Erro ao atualizar o Excel: %s", e)
        await update.message.reply_text("Erro ao atualizar a planilha.")
        return ConversationHandler.END
    
    await update.message.reply_text("Planilha atualizada. Atualizando o site...")

    sucesso, saida = executar_build_site()
    if sucesso:
        await update.message.reply_text(
            "Site atualizado com sucesso!\n\n"
            f"Foto salva em: `erb_photos/{num_estacao}.jpeg`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"Foto salva, mas houve erro ao gerar o site:\n```\n{saida}\n```",
            parse_mode="Markdown"
        )

    # limpa os dados temporários da conversa
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação em andamento com /cancelar."""
    context.user_data.clear()
    await update.message.reply_text("Operação cancelada. Envie uma foto para recomeçar.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    # conversationHandler gerencia o fluxo de múltiplas mensagens
    conversa = ConversationHandler(
        # Ponto de entrada: qualquer foto enviada (como documento ou imagem)
        entry_points=[
            MessageHandler(filters.Document.IMAGE, receber_foto),
            MessageHandler(filters.PHOTO, receber_foto),
        ],
        states={
            AGUARDANDO_NUMERO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_numero)
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conversa)

    logger.info("Bot iniciado. Aguardando mensagens...")
    app.run_polling()

if __name__ == "__main__":
    main()    