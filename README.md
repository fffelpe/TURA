# Agente TURA (TV Cultura Ingestão)

Este repositório contém a Agente de IA "TURA", responsável por automatizar o fluxo de ingestão e criação de IDs na Intranet da TV Cultura.

## Como funciona
1. A TURA varre a rede local a cada 40 minutos.
2. Identifica os arquivos de mídia (ignorando arquivos com sufixo `_ing`).
3. Faz uma cópia padronizada na pasta `INGEST`.
4. Em lotes de 10 arquivos, submete os dados invisivelmente via requisições HTTP para a Intranet (bypassing ASP.NET VIEWSTATE), gerando os IDs.
5. Gera uma planilha Excel final e envia a Ordem de Serviço por e-mail para a equipe de ingestão.

## Como rodar

1. Clone o repositório.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
