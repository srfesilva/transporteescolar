import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import time  # Adicionado para evitar erro no time.sleep

# ... (Configuração inicial permanece igual)

# CORREÇÃO: Adicionada a coluna 'empresa' na criação da tabela
c.execute('''
CREATE TABLE IF NOT EXISTS solicitacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_aluno TEXT,
    cpf_aluno TEXT,
    ra_aluno TEXT,
    cadeirante TEXT,
    cid TEXT,
    cep_aluno TEXT,
    logradouro_aluno TEXT,
    numero_aluno TEXT,
    municipio_aluno TEXT,
    nome_escola TEXT,
    cep_escola TEXT,
    logradouro_escola TEXT,
    numero_escola TEXT,
    municipio_escola TEXT,
    sala_recurso TEXT,
    dias_frequencia TEXT,
    horario_entrada TEXT,
    horario_saida TEXT,
    arquivo_medico BLOB,
    nome_arq_medico TEXT,
    arquivo_viagem BLOB,
    nome_arq_viagem TEXT,
    status TEXT DEFAULT 'Pendente',
    supervisor_nome TEXT,
    supervisor_cpf TEXT,
    motivo_reprovacao TEXT,
    arquivo_assinado BLOB,
    nome_arq_assinado TEXT,
    empresa TEXT, -- Coluna adicionada aqui
    data_atualizacao TEXT
)
''')
conn.commit()

# ... (Funções auxiliares e Menu permanecem iguais)

if menu == "Escola (Solicitação)":
    # (Mantenha o código da Aba 1 aqui)
    st.title("🚌 Solicitação de Transporte Escolar")
    # ... código omitido por brevidade ...

# CORREÇÃO DE INDENTAÇÃO: Alinhado com o 'if' acima
elif menu == "Relatórios e Docs":
    st.title("🗂️ Relatório Geral e Edição")
    # ... restando do código da aba de relatórios ...
