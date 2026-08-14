# -*- coding: utf-8 -*-
import re
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://intranet.tvcultura.com.br/mam/Jornalismo/geraridBruto.aspx"
LOGIN_URL = "http://intranet.tvcultura.com.br/mam/login.aspx"
PREFIXO = "ctl00$ctl00$ContentPlaceHolder1$ContentPlaceHolder1$"
CAMPOS_HIDDEN = ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]

class IntranetSession:
    def __init__(self, usuario=None, senha=None):
        self.session = requests.Session()
        self.usuario = usuario or os.getenv("INTRANET_USER")
        self.senha = senha or os.getenv("INTRANET_PASS")
        self.hidden_state = {}

    def _extrair_hidden_fields(self, html):
        campos = {}
        for nome in CAMPOS_HIDDEN:
            m = re.search(rf'id="{nome}"[^>]*value="([^"]*)"', html)
            if not m:
                m = re.search(rf'name="{nome}"[^>]*value="([^"]*)"', html)
            if m:
                campos[nome] = m.group(1)
        return campos

    def _extrair_hidden_fields_do_delta(self, texto):
        campos = {}
        partes = texto.split("|")
        i = 0
        while i < len(partes) - 3:
            tipo = partes[i + 1]
            nome = partes[i + 2]
            valor = partes[i + 3]
            if tipo == "hiddenField" and nome in CAMPOS_HIDDEN:
                campos[nome] = valor
            i += 4
        return campos

    def _extrair_media_id(self, texto):
        m = re.search(r'lblMediaId"[^>]*>([^<]+)</span>', texto)
        if m:
            return m.group(1).strip()
        return None

    def _extrair_erro_validacao(self, texto):
        if "obrigat" in texto.lower() or "erro" in texto.lower() or "inválid" in texto.lower():
            return True
        return False

    def login(self):
        print("[Intranet] Iniciando autenticação...")
        resp_get = self.session.get(LOGIN_URL, timeout=30)
        resp_get.raise_for_status()
        self.hidden_state = self._extrair_hidden_fields(resp_get.text)
        
        if not self.hidden_state.get("__VIEWSTATE"):
            raise RuntimeError("Não foi possível carregar o __VIEWSTATE da página de login.")

        payload_login = {
            "ctl00$ctl00$ToolkitScriptManager1": "ctl00$ctl00$ContentPlaceHolder1$UpdatePanel1|ctl00$ctl00$ContentPlaceHolder1$ContentPlaceHolder1$Login1$LoginImageButton",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.hidden_state.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": self.hidden_state.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": self.hidden_state.get("__EVENTVALIDATION", ""),
            "ctl00$ctl00$txt_email": "",
            "ctl00$ctl00$txt_email_TextBoxWatermarkExtender_ClientState": "",
            "ctl00$ctl00$ContentPlaceHolder1$ContentPlaceHolder1$Login1$UserName": self.usuario,
            "ctl00$ctl00$ContentPlaceHolder1$ContentPlaceHolder1$Login1$Password": self.senha,
            "hiddenInputToUpdateATBuffer_CommonToolkitScripts": "1",
            "__ASYNCPOST": "true",
            "ctl00$ctl00$ContentPlaceHolder1$ContentPlaceHolder1$Login1$LoginImageButton.x": "0",
            "ctl00$ctl00$ContentPlaceHolder1$ContentPlaceHolder1$Login1$LoginImageButton.y": "0"
        }

        headers = {
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LOGIN_URL,
        }

        resp_post = self.session.post(LOGIN_URL, data=payload_login, headers=headers, timeout=30)
        resp_post.raise_for_status()

        novos_campos = self._extrair_hidden_fields_do_delta(resp_post.text)
        if novos_campos:
            self.hidden_state.update(novos_campos)

        if self._extrair_erro_validacao(resp_post.text):
            raise RuntimeError("Falha no login. Verifique o usuário e a senha no arquivo .env.")
        print("[Intranet] Autenticação concluída com sucesso.")

    def carregar_pagina(self):
        resp = self.session.get(BASE_URL, timeout=30)
        resp.raise_for_status()
        self.hidden_state = self._extrair_hidden_fields(resp.text)
        if not self.hidden_state.get("__VIEWSTATE"):
            raise RuntimeError("Não foi possível extrair __VIEWSTATE da página de geração.")

    def gerar_id(self, materia, data, programa="1452 - AGROCULTURA", audio="1", cromia="1", fonte="1", editoria="6", cinegrafista="", reporter="", observacao=""):
        if not self.hidden_state.get("__VIEWSTATE"):
            raise RuntimeError("Sessão não inicializada. Chame carregar_pagina() antes.")

        payload = {
            "ctl00$ctl00$ToolkitScriptManager1": f"{PREFIXO}UpdatePanel1|{PREFIXO}btnGerarId",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.hidden_state.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": self.hidden_state.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": self.hidden_state.get("__EVENTVALIDATION", ""),
            "ctl00$ctl00$txt_email": "",
            f"{PREFIXO}txtPrograma": programa,
            f"{PREFIXO}txtMateria": materia,
            f"{PREFIXO}ddlAudio": audio,
            f"{PREFIXO}ddlCromia": cromia,
            f"{PREFIXO}txtData": data,
            f"{PREFIXO}ddlFonte": fonte,
            f"{PREFIXO}ddlEditoria": editoria,
            f"{PREFIXO}txtCinegrafista": cinegrafista,
            f"{PREFIXO}txtReporter": reporter,
            f"{PREFIXO}txtObservacao": observacao,
            "hiddenInputToUpdateATBuffer_CommonToolkitScripts": "1",
            "__ASYNCPOST": "true",
            f"{PREFIXO}btnGerarId.x": "10",
            f"{PREFIXO}btnGerarId.y": "10",
        }

        headers = {
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE_URL,
        }

        resp = self.session.post(BASE_URL, data=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        texto = resp.text

        novos_campos = self._extrair_hidden_fields_do_delta(texto)
        if novos_campos:
            self.hidden_state.update(novos_campos)

        if self._extrair_erro_validacao(texto):
            raise RuntimeError(f"Falha de validação ao gerar ID para '{materia}'.")

        media_id = self._extrair_media_id(texto)
        if not media_id:
            raise RuntimeError(f"Não foi possível extrair o Media ID para '{materia}'.")

        return media_id

# Instância global para aproveitar a sessão durante o lote
_sessao_global = None

def gerar_id_intranet(nome_arquivo, data=None):
    global _sessao_global
    from datetime import datetime

    if data is None:
        data = datetime.now().strftime("%d/%m/%Y")

    if _sessao_global is None:
        _sessao_global = IntranetSession()
        _sessao_global.login()
        _sessao_global.carregar_pagina()

    try:
        return _sessao_global.gerar_id(materia=nome_arquivo, data=data)
    except RuntimeError:
        # Tenta recarregar a página caso o ViewState expire
        _sessao_global.carregar_pagina()
        return _sessao_global.gerar_id(materia=nome_arquivo, data=data)
