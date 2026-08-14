# -*- coding: utf-8 -*-
import os
import shutil
import time
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from dotenv import load_dotenv

# Importa a função geradora de ID do nosso outro arquivo
from tura_intranet import gerar_id_intranet

load_dotenv()

BASE_DIR = Path(r"\\172.20.15.111\JORNAL\AGROCULTURA\VTS E STAND UPS AFILIADAS")
INGEST_DIR = Path(r"\\172.20.15.111\JORNAL\AGROCULTURA\INGEST")

EXTENSOES_VALIDAS = ['.mp4', '.mov', '.mxf', '.avi', '.mp3', '.wav']
CATEGORIAS_VALIDAS = ['matérias', 'materias', 'standups', 'reporter chama']
LOTE_MAXIMO = 10

def processar_lote(lote_arquivos):
    print(f"\n[TURA] Processando lote de {len(lote_arquivos)} arquivos...")
    dados_excel = []
    
    for arquivo_nome in lote_arquivos:
        try:
            # Requisita a geração do ID via módulo intranet
            media_id = gerar_id_intranet(nome_arquivo=arquivo_nome)
            print(f"[TURA] Sucesso: {arquivo_nome} -> ID: {media_id}")
            dados_excel.append({"Nome do Arquivo": arquivo_nome, "ID Intranet": media_id})
        except Exception as e:
            print(f"[Erro] Falha ao gerar ID para {arquivo_nome}: {e}")
    
    # Cria a planilha se houverem dados processados
    if dados_excel:
        df = pd.DataFrame(dados_excel)
        nome_planilha = f"OS_Ingest_{int(time.time())}.xlsx"
        caminho_planilha = INGEST_DIR / nome_planilha
        
        df.to_excel(caminho_planilha, index=False, columns=["Nome do Arquivo", "ID Intranet"])
        print(f"[TURA] Planilha salva em: {caminho_planilha}")
        
        enviar_email_os(caminho_planilha, nome_planilha)

def enviar_email_os(caminho_planilha, nome_planilha):
    remetente = os.getenv("EMAIL_USER")
    senha = os.getenv("EMAIL_PASS")
    destinatario = "equipe.ingest@tvcultura.com.br"
    
    if not remetente or not senha:
        print("[Erro] Credenciais de e-mail não configuradas no .env. E-mail não enviado.")
        return

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Subject'] = f"Nova Ordem de Serviço - Ingestão - {nome_planilha}"
    
    corpo = "Olá equipe,\n\nSegue em anexo a nova planilha com a Ordem de Serviço contendo 10 novos IDs gerados para ingestão.\n\nAtenciosamente,\nAgente TURA"
    msg.attach(MIMEText(corpo, 'plain'))
    
    try:
        with open(caminho_planilha, "rb") as f:
            anexo = MIMEApplication(f.read(), _subtype="xlsx")
            anexo.add_header('Content-Disposition', 'attachment', filename=nome_planilha)
            msg.attach(anexo)
            
        servidor = smtplib.SMTP('smtp.office365.com', 587)
        servidor.starttls()
        servidor.login(remetente, senha)
        servidor.send_message(msg)
        servidor.quit()
        print(f"[TURA] E-mail enviado com sucesso para {destinatario}!")
    except Exception as e:
        print(f"[Erro] Falha ao enviar o e-mail: {e}")

def varredura():
    lote_arquivos = []
    
    print("\n[TURA] Iniciando varredura no servidor de armazenamento...")
    if not BASE_DIR.exists():
        print(f"[Erro] Diretório base inacessível: {BASE_DIR}")
        return

    # Nível 1: Meses
    for pasta_mes in BASE_DIR.iterdir():
        if not pasta_mes.is_dir(): continue
        
        # Nível 2: Dias
        for pasta_dia in pasta_mes.iterdir():
            if not pasta_dia.is_dir(): continue
            
            # Nível 3: Categorias
            for pasta_categoria in pasta_dia.iterdir():
                if not pasta_categoria.is_dir() or pasta_categoria.name.lower() not in CATEGORIAS_VALIDAS: 
                    continue
                
                # Nível 4: Pastas dos VTs
                for pasta_vt in pasta_categoria.iterdir():
                    if not pasta_vt.is_dir(): continue
                    
                    arquivos_na_pasta = [f for f in pasta_vt.iterdir() if f.is_file()]
                    
                    for arquivo in arquivos_na_pasta:
                        nome_sem_extensao = arquivo.stem.lower()
                        extensao = arquivo.suffix.lower()
                        
                        # Ignora arquivos que finalizam com "_ing"
                        if nome_sem_extensao.endswith('_ing'):
                            continue
                        
                        # Processa extensões válidas
                        if extensao in EXTENSOES_VALIDAS:
                            novo_nome = f"{pasta_vt.name}_{arquivo.name}"
                            caminho_destino = INGEST_DIR / novo_nome
                            
                            if caminho_destino.exists():
                                continue
                                
                            try:
                                shutil.copy2(arquivo, caminho_destino)
                                print(f"[TURA] Arquivo copiado: {novo_nome}")
                                
                                lote_arquivos.append(novo_nome)
                                
                                if len(lote_arquivos) == LOTE_MAXIMO:
                                    processar_lote(lote_arquivos)
                                    lote_arquivos = []
                            except Exception as e:
                                print(f"[Erro] Problema ao copiar o arquivo {arquivo.name}: {e}")

def start_agent():
    print("======================================================")
    print("AGENTE TURA INICIALIZADA - MODO INVISÍVEL")
    print("======================================================")
    
    INGEST_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        try:
            varredura()
        except Exception as err:
            print(f"[Erro Global] A varredura foi interrompida: {err}")
            
        print("[TURA] Ciclo concluído. Entrando em modo de espera por 40 minutos...")
        time.sleep(2400)

if __name__ == "__main__":
    start_agent()
