import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Gestão de Transporte Escolar", layout="wide")

# Conectar ao banco V3 (Nova estrutura de colunas)
conn = sqlite3.connect('transporte_v3.db', check_same_thread=False)
c = conn.cursor()

# Criar tabela com NOVOS CAMPOS SEPARADOS
c.execute('''
CREATE TABLE IF NOT EXISTS solicitacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Dados do Aluno
    nome_aluno TEXT,
    cpf_aluno TEXT,
    ra_aluno TEXT,
    cadeirante TEXT,
    cid TEXT,
    
    -- Endereço Aluno Detalhado
    cep_aluno TEXT,
    logradouro_aluno TEXT,
    numero_aluno TEXT,
    municipio_aluno TEXT,
    
    -- Dados da Escola
    nome_escola TEXT,
    cep_escola TEXT,
    logradouro_escola TEXT,
    numero_escola TEXT,
    municipio_escola TEXT,
    
    -- Frequência
    sala_recurso TEXT,
    dias_frequencia TEXT,
    horario_entrada TEXT,
    horario_saida TEXT,
    
    -- Arquivos (BLOB)
    arquivo_medico BLOB,
    nome_arq_medico TEXT,
    arquivo_viagem BLOB,
    nome_arq_viagem TEXT,
    
    -- Dados do Supervisor
    status TEXT DEFAULT 'Pendente',
    supervisor_nome TEXT,
    supervisor_cpf TEXT,
    motivo_reprovacao TEXT,
    arquivo_assinado BLOB,
    nome_arq_assinado TEXT,
    data_atualizacao TEXT
)
''')
conn.commit()

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def buscar_dados_cep(cep):
    """Retorna um dicionário com logradouro, bairro, localidade(municipio), uf"""
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
menu = st.sidebar.radio("Ir para:", ["Escola (Solicitação)", "Supervisor (Avaliação)", "Relatórios e Docs"])

# ---------------------------------------------------------------------
# ABA 1: ESCOLA (SOLICITAÇÃO)
# ---------------------------------------------------------------------
if menu == "Escola (Solicitação)":
    st.title("🚌 Solicitação de Transporte Escolar")
    st.markdown("---")

    if "end_aluno_cache" not in st.session_state: st.session_state.end_aluno_cache = {}
    if "end_escola_cache" not in st.session_state: st.session_state.end_escola_cache = {}

    with st.form("form_escola"):
        # --- BLOCO 1: DADOS PESSOAIS ---
        st.subheader("1. Dados do Aluno")
        col1, col2, col3 = st.columns(3)
        nome = col1.text_input("Nome Completo do Aluno (Obrigatório)")
        cpf = col2.text_input("CPF do Aluno (Obrigatório)")
        ra = col3.text_input("R.A. do Aluno (Obrigatório)")

        col4, col5 = st.columns(2)
        cadeirante = col4.radio("Aluno Cadeirante?", ["NÃO", "SIM"], horizontal=True)
        cid = col5.text_input("CID (Código Internacional de Doenças)")

        # --- BLOCO 2: ENDEREÇO RESIDENCIAL ---
        st.markdown("##### Endereço Residencial")
        col_cep1, col_btn1 = st.columns([2, 1])
        cep_input_aluno = col_cep1.text_input("CEP Residencial (Opcional)")
        
        # Botão fictício de busca (o Streamlit reexecuta o form, simulando a busca)
        # Lógica de preenchimento automático
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

        # --- BLOCO 3: UNIDADE ESCOLAR ---
        st.subheader("2. Dados da Unidade Escolar")
        nome_escola = st.text_input("Nome da Unidade Escolar ou Instituição")
        
        col_cep2, col_dummy = st.columns([2, 3])
        cep_input_escola = col_cep2.text_input("CEP Escola (Opcional)")
        
        logradouro_esc_suggest = ""
        municipio_esc_suggest = ""
        
        if cep_input_escola and len(cep_input_escola) >= 8:
            dados_cep_esc = buscar_dados_cep(cep_input_escola)
            if dados_cep_esc:
                logradouro_esc_suggest = f"{dados_cep_esc['logradouro']}, {dados_cep_esc['bairro']}"
                municipio_esc_suggest = f"{dados_cep_esc['localidade']} - {dados_cep_esc['uf']}"
                st.caption(f"✅ Escola encontrada: {logradouro_esc_suggest}")

        col_end2, col_num2, col_mun2 = st.columns([3, 1, 2])
        end_escola = col_end2.text_input("Logradouro Escola", value=logradouro_esc_suggest)
        num_escola = col_num2.text_input("Número Escola (Obrigatório)")
        mun_escola = col_mun2.text_input("Município Escola (Obrigatório)", value=municipio_esc_suggest)

        # --- BLOCO 4: FREQUÊNCIA ---
        st.subheader("3. Frequência e Horários")
        sala_recurso = st.radio("Frequenta Sala de Recurso?", ["NÃO", "SIM"], horizontal=True)
        
        dias_freq = st.multiselect("Dias de Frequência", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"])
        
        st.markdown("**Horários (Formato Relógio - Obrigatório)**")
        col_h1, col_h2 = st.columns(2)
        hr_entrada = col_h1.time_input("Horário de Entrada", value=None)
        hr_saida = col_h2.time_input("Horário de Saída", value=None)

        # --- BLOCO 5: DOCUMENTOS ---
        st.subheader("4. Documentação Obrigatória")
        doc_medico = st.file_uploader("Ficha Médica", type=['pdf', 'jpg', 'png'])
        doc_viagem = st.file_uploader("Ficha de Programação de Viagem", type=['pdf', 'jpg', 'png'])

        submitted = st.form_submit_button("Enviar Solicitação")

        if submitted:
            # Validação de Campos Obrigatórios
            if not nome or not cpf or not ra:
                st.error("Preencha Nome, CPF e RA do aluno.")
            elif not num_aluno or not mun_aluno:
                st.error("Número e Município do Aluno são obrigatórios.")
            elif not num_escola or not mun_escola:
                st.error("Número e Município da Escola são obrigatórios.")
            elif not hr_entrada or not hr_saida:
                st.error("Os horários de Entrada e Saída são obrigatórios.")
            elif not doc_medico or not doc_viagem:
                st.error("Anexe os documentos obrigatórios.")
            else:
                # Processamento
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
                st.success(f"Solicitação enviada com sucesso! Aluno: {nome}")

# ---------------------------------------------------------------------
# ABA 2: SUPERVISOR (AVALIAÇÃO)
# ---------------------------------------------------------------------
elif menu == "Supervisor (Avaliação)":
    st.title("📋 Painel do Supervisor")
    
    # Lista de Pendentes
    df_pendentes = pd.read_sql("SELECT id, nome_aluno, status FROM solicitacoes WHERE status='Pendente'", conn)
    
    if not df_pendentes.empty:
        opcoes_alunos = df_pendentes.apply(lambda x: f"{x['id']} - {x['nome_aluno']}", axis=1)
        escolha = st.selectbox("Selecione um Aluno Pendente:", opcoes_alunos)
        
        id_aluno_selecionado = int(escolha.split(' - ')[0])
        
        c.execute("SELECT * FROM solicitacoes WHERE id=?", (id_aluno_selecionado,))
        dados = c.fetchone()
        
        if dados:
            st.info(f"Analisando solicitação # {dados[0]}")
            
            # Layout de visualização dos dados
            tab_dados, tab_docs = st.tabs(["Dados da Solicitação", "Documentos Anexados"])
            
            with tab_dados:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### Aluno")
                    st.write(f"**Nome:** {dados[1]}")
                    st.write(f"**CPF:** {dados[2]} | **RA:** {dados[3]}")
                    st.write(f"**CID:** {dados[5]} | **Cadeirante:** {dados[4]}")
                    st.write(f"**Endereço:** {dados[7]}, Nº {dados[8]} - {dados[9]}")
                
                with c2:
                    st.markdown("### Escola e Horários")
                    st.write(f"**Instituição:** {dados[10]}")
                    st.write(f"**Endereço:** {dados[12]}, Nº {dados[13]} - {dados[14]}")
                    st.write(f"**Dias:** {dados[16]}")
                    st.write(f"**Horário:** Entrada {dados[17]} / Saída {dados[18]}")

            with tab_docs:
                st.markdown("#### Documentos enviados pela Escola")
                cd1, cd2 = st.columns(2)
                if dados[19]:
                    cd1.download_button("⬇️ Baixar Ficha Médica", data=dados[19], file_name=dados[20] or "medico.pdf")
                if dados[21]:
                    cd2.download_button("⬇️ Baixar Ficha Viagem", data=dados[21], file_name=dados[22] or "viagem.pdf")

            st.markdown("---")
            st.markdown("### ✍️ Validação e Parecer")
            
            with st.form("form_supervisor"):
                # IDENTIFICAÇÃO DENTRO DO FORMULÁRIO (Solicitação atendida)
                col_sup1, col_sup2 = st.columns(2)
                nome_sup = col_sup1.text_input("Nome Completo do Supervisor / PEC")
                cpf_sup = col_sup2.text_input("CPF do Supervisor")
                
                st.markdown("#### Decisão")
                decisao = st.radio("Parecer:", ["Aprovar Solicitação", "Reprovar Solicitação"])
                
                motivo = None
                if decisao == "Reprovar Solicitação":
                    motivo = st.selectbox("Motivo da Reprovação:", [
                        "Falta de documentação",
                        "Aluno não elegível ao transporte",
                        "Reavaliação da Necessidade do Transporte"
                    ])
                
                st.markdown("#### Devolutiva Assinada")
                arquivo_assinado = st.file_uploader("Anexar Ficha Assinada (Obrigatório)", type=['pdf', 'jpg', 'png'])
                
                btn_avaliar = st.form_submit_button("Finalizar Processo")
                
                if btn_avaliar:
                    if not nome_sup or not cpf_sup:
                        st.error("Identificação do Supervisor é obrigatória.")
                    elif not arquivo_assinado:
                        st.error("É necessário anexar a ficha assinada.")
                    else:
                        status_final = "Aprovado" if decisao == "Aprovar Solicitação" else "Reprovado"
                        motivo_final = motivo if status_final == "Reprovado" else "Aprovado - Sem restrições"
                        
                        c.execute('''
                            UPDATE solicitacoes 
                            SET status=?, supervisor_nome=?, supervisor_cpf=?, 
                                motivo_reprovacao=?, arquivo_assinado=?, nome_arq_assinado=?,
                                data_atualizacao=?
                            WHERE id=?
                        ''', (status_final, nome_sup, cpf_sup, motivo_final, 
                              arquivo_assinado.getvalue(), arquivo_assinado.name, 
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_aluno_selecionado))
                        conn.commit()
                        st.success("Avaliação concluída com sucesso!")
                        st.rerun()
    else:
        st.success("Tudo em dia! Nenhuma solicitação pendente.")

# ---------------------------------------------------------------------
# ABA 3: RELATÓRIOS E DOCUMENTOS
# ---------------------------------------------------------------------
elif menu == "Relatórios e Docs":
    st.title("🗂️ Relatório Geral e Documentos")
    
    # Filtros
    status_filter = st.selectbox("Filtrar por Status:", ["Todos", "Pendente", "Aprovado", "Reprovado"])
    
    query = "SELECT id, nome_aluno, cpf_aluno, nome_escola, status, supervisor_nome, motivo_reprovacao FROM solicitacoes"
    if status_filter != "Todos":
        query += f" WHERE status = '{status_filter}'"
        
    df = pd.read_sql(query, conn)
    
    # 1. Tabela Resumo
    st.markdown("### Visão Geral")
    st.dataframe(df)
    
    # 2. Acesso aos Documentos
    st.markdown("---")
    st.markdown("### 📂 Acesso aos Arquivos por Aluno")
    st.info("Clique no nome do aluno abaixo para ver e baixar todos os documentos.")
    
    # Buscar todos os dados (incluindo blobs) para listar
    c.execute(f"SELECT id, nome_aluno, arquivo_medico, nome_arq_medico, arquivo_viagem, nome_arq_viagem, arquivo_assinado, nome_arq_assinado, status FROM solicitacoes")
    todos_dados = c.fetchall()
    
    for row in todos_dados:
        # row[0]=id, row[1]=nome, row[2]=blob_med, row[3]=nome_med, row[4]=blob_via, row[5]=nome_via, row[6]=blob_ass, row[7]=nome_ass, row[8]=status
        
        # Filtro visual (se usuario selecionou pendente, so mostra pendente na lista tambem)
        if status_filter != "Todos" and row[8] != status_filter:
            continue
            
        icon = "✅" if row[8] == "Aprovado" else "❌" if row[8] == "Reprovado" else "⏳"
        
        with st.expander(f"{icon} {row[1]} (ID: {row[0]}) - Status: {row[8]}"):
            cols = st.columns(3)
            
            # Doc Medico
            with cols[0]:
                if row[2]:
                    st.download_button("📄 Baixar Ficha Médica", data=row[2], file_name=row[3], key=f"rm_{row[0]}")
                else:
                    st.caption("Ficha Médica não encontrada")
            
            # Doc Viagem
            with cols[1]:
                if row[4]:
                    st.download_button("🚌 Baixar Ficha Viagem", data=row[4], file_name=row[5], key=f"rv_{row[0]}")
                else:
                    st.caption("Ficha Viagem não encontrada")
            
            # Doc Assinado (Supervisor)
            with cols[2]:
                if row[6]:
                    st.download_button("✍️ Baixar Parecer Supervisor", data=row[6], file_name=row[7], key=f"ra_{row[0]}")
                else:
                    st.caption("Ainda não avaliado/assinado")
