import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import time  # Necessário para o delay antes de dar refresh na página

# ==========================================
# CONFIGURAÇÃO E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Gestão de Transporte Escolar", layout="wide")

# Conectar ao banco V3
conn = sqlite3.connect('transporte_v3.db', check_same_thread=False)
c = conn.cursor()

# Criar tabela com todos os campos necessários
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
    empresa TEXT, -- Coluna que estava faltando no seu código original
    data_atualizacao TEXT
)
''')
conn.commit()

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def buscar_dados_cep(cep):
    cep = cep.replace("-", "").replace(".", "").strip()
    if len(cep) == 8:
        try:
            response = requests.get(f"https://viacep.com.br/ws/{cep}/json/")
            dados = response.json()
            if "erro" not in dados:
                return dados
        except:
            return None
    return None

# ==========================================
# INTERFACE
# ==========================================
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["Escola (Solicitação)", "Relatórios e Docs"])

# ---------------------------------------------------------------------
# ABA 1: ESCOLA (SOLICITAÇÃO)
# ---------------------------------------------------------------------
if menu == "Escola (Solicitação)":
    st.title("🚌 Solicitação de Transporte Escolar")
    st.markdown("---")

    with st.form("form_escola"):
        st.subheader("1. Dados do Aluno")
        col1, col2, col3 = st.columns(3)
        nome = col1.text_input("Nome Completo do Aluno (Obrigatório)")
        cpf = col2.text_input("CPF do Aluno (Obrigatório)")
        ra = col3.text_input("R.A. do Aluno (Obrigatório)")

        col4, col5 = st.columns(2)
        cadeirante = col4.radio("Aluno Cadeirante?", ["NÃO", "SIM"], horizontal=True)
        cid = col5.text_input("CID")

        st.markdown("##### Endereço Residencial")
        cep_input_aluno = st.text_input("CEP Residencial (Opcional)")
        
        logradouro_suggest = ""
        municipio_suggest = ""
        
        if cep_input_aluno and len(cep_input_aluno) >= 8:
            dados_cep = buscar_dados_cep(cep_input_aluno)
            if dados_cep:
                logradouro_suggest = f"{dados_cep['logradouro']}, {dados_cep['bairro']}"
                municipio_suggest = f"{dados_cep['localidade']} - {dados_cep['uf']}"
                st.caption(f"✅ Endereço encontrado: {logradouro_suggest}")
        
        col_end1, col_num1, col_mun1 = st.columns([3, 1, 2])
        end_aluno = col_end1.text_input("Logradouro Completo", value=logradouro_suggest)
        num_aluno = col_num1.text_input("Número (Obrigatório)")
        mun_aluno = col_mun1.text_input("Município (Obrigatório)", value=municipio_suggest)

        st.subheader("2. Dados da Unidade Escolar")
        nome_escola = st.text_input("Nome da Unidade Escolar")
        cep_input_escola = st.text_input("CEP Escola (Opcional)")
        
        logradouro_esc_suggest = ""
        municipio_esc_suggest = ""
        
        if cep_input_escola and len(cep_input_escola) >= 8:
            dados_cep_esc = buscar_dados_cep(cep_input_escola)
            if dados_cep_esc:
                logradouro_esc_suggest = f"{dados_cep_esc['logradouro']}, {dados_cep_esc['bairro']}"
                municipio_esc_suggest = f"{dados_cep_esc['localidade']} - {dados_cep_esc['uf']}"

        col_end2, col_num2, col_mun2 = st.columns([3, 1, 2])
        end_escola = col_end2.text_input("Logradouro Escola", value=logradouro_esc_suggest)
        num_escola = col_num2.text_input("Número Escola (Obrigatório)")
        mun_escola = col_mun2.text_input("Município Escola (Obrigatório)", value=municipio_esc_suggest)

        st.subheader("3. Frequência e Horários")
        sala_recurso = st.radio("Frequenta Sala de Recurso?", ["NÃO", "SIM"], horizontal=True)
        dias_freq = st.multiselect("Dias de Frequência", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"])
        
        col_h1, col_h2 = st.columns(2)
        hr_entrada = col_h1.time_input("Horário de Entrada", value=None)
        hr_saida = col_h2.time_input("Horário de Saída", value=None)

        st.subheader("4. Documentação")
        doc_medico = st.file_uploader("Ficha Médica", type=['pdf', 'jpg', 'png'])
        doc_viagem = st.file_uploader("Ficha de Programação de Viagem", type=['pdf', 'jpg', 'png'])

        submitted = st.form_submit_button("Enviar Solicitação")

        if submitted:
            if not nome or not cpf or not ra or not num_aluno or not mun_aluno or not hr_entrada or not hr_saida or not doc_medico or not doc_viagem:
                st.error("Por favor, preencha todos os campos obrigatórios e anexe os documentos.")
            else:
                dias_str = ", ".join(dias_freq)
                hr_ent_str = hr_entrada.strftime("%H:%M")
                hr_sai_str = hr_saida.strftime("%H:%M")

                c.execute('''
                    INSERT INTO solicitacoes (
                        nome_aluno, cpf_aluno, ra_aluno, cadeirante, cid, 
                        cep_aluno, logradouro_aluno, numero_aluno, municipio_aluno,
                        nome_escola, cep_escola, logradouro_escola, numero_escola, municipio_escola,
                        sala_recurso, dias_frequencia, horario_entrada, horario_saida,
                        arquivo_medico, nome_arq_medico, arquivo_viagem, nome_arq_viagem
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    nome, cpf, ra, cadeirante, cid, 
                    cep_input_aluno, end_aluno, num_aluno, mun_aluno,
                    nome_escola, cep_input_escola, end_escola, num_escola, mun_escola,
                    sala_recurso, dias_str, hr_ent_str, hr_sai_str,
                    doc_medico.getvalue(), doc_medico.name, doc_viagem.getvalue(), doc_viagem.name
                ))
                conn.commit()
                st.success(f"Solicitação enviada com sucesso para o aluno: {nome}")

# ---------------------------------------------------------------------
# ABA 2: RELATÓRIOS E DOCS (CORRIGIDA)
# ---------------------------------------------------------------------
elif menu == "Relatórios e Docs":
    st.title("🗂️ Relatório Geral e Edição")
    
    filtro = st.selectbox("Filtrar Status", ["Todos", "Pendente", "Aprovado", "Reprovado"])
    
    query = "SELECT * FROM solicitacoes"
    if filtro != "Todos":
        query += f" WHERE status = '{filtro}'"
    
    df = pd.read_sql(query, conn)
    
    # Exibir tabela resumida
    # Nota: Certifique-se que a coluna 'empresa' exista para não dar erro aqui
    cols_view = ['id', 'nome_aluno', 'nome_escola', 'status', 'empresa']
    st.dataframe(df[cols_view])
    
    st.markdown("---")
    st.subheader("Gerenciar Registros (Editar / Excluir / Docs)")
    
    # Para manipulação individual, usamos o cursor para garantir acesso aos nomes das colunas
    conn.row_factory = sqlite3.Row
    cursor_row = conn.cursor()
    registros = cursor_row.execute(query).fetchall()
    
    for reg in registros:
        empresa_val = reg['empresa'] if reg['empresa'] else ""
        label = f"🆔 {reg['id']} - {reg['nome_aluno']} ({reg['status']}) | 🏢 {empresa_val}"
        
        with st.expander(label):
            st.markdown("#### 📂 Documentos")
            cd1, cd2 = st.columns(2)
            if reg['arquivo_medico']: 
                cd1.download_button("Ficha Médica", reg['arquivo_medico'], file_name=reg['nome_arq_medico'], key=f"dm{reg['id']}")
            if reg['arquivo_viagem']: 
                cd2.download_button("Ficha Viagem", reg['arquivo_viagem'], file_name=reg['nome_arq_viagem'], key=f"dv{reg['id']}")
            
            st.markdown("---")
            st.markdown("#### ✏️ Editar Informações")
            with st.form(f"edit_{reg['id']}"):
                ce1, ce2 = st.columns(2)
                new_nome = ce1.text_input("Nome Aluno", reg['nome_aluno'])
                new_status = ce2.selectbox("Status", ["Pendente", "Aprovado", "Reprovado"], index=["Pendente", "Aprovado", "Reprovado"].index(reg['status']))
                
                ce3, ce4 = st.columns(2)
                new_escola = ce3.text_input("Escola", reg['nome_escola'])
                new_empresa = ce4.text_input("🏢 Empresa Transportadora", value=empresa_val)
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    c.execute("UPDATE solicitacoes SET nome_aluno=?, status=?, nome_escola=?, empresa=? WHERE id=?",
                              (new_nome, new_status, new_escola, new_empresa, reg['id']))
                    conn.commit()
                    st.success("Atualizado!")
                    time.sleep(1)
                    st.rerun()

            if st.button(f"🗑️ Excluir Registro {reg['id']}", key=f"del_{reg['id']}"):
                c.execute("DELETE FROM solicitacoes WHERE id=?", (reg['id'],))
                conn.commit()
                st.warning("Registro excluído.")
                time.sleep(1)
                st.rerun()
