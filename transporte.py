import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Gestão de Transporte Escolar", layout="wide")

# Conectar ao banco (usamos v2 para garantir que as novas colunas sejam criadas)
conn = sqlite3.connect('transporte_v2.db', check_same_thread=False)
c = conn.cursor()

# Criar tabela com TODOS os novos campos
c.execute('''
CREATE TABLE IF NOT EXISTS solicitacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Dados do Aluno
    nome_aluno TEXT,
    cpf_aluno TEXT,
    ra_aluno TEXT,
    cadeirante TEXT,
    cid TEXT,
    cep_aluno TEXT,
    endereco_aluno TEXT,
    
    -- Dados da Escola
    nome_escola TEXT,
    endereco_escola TEXT,
    sala_recurso TEXT,
    dias_frequencia TEXT,
    horarios_frequencia TEXT,
    
    -- Arquivos (Salvos como binário BLOB para simplificar)
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
def buscar_endereco_cep(cep):
    """Busca endereço pelo CEP usando a API ViaCEP"""
    cep = cep.replace("-", "").replace(".", "").strip()
    if len(cep) == 8:
        try:
            response = requests.get(f"https://viacep.com.br/ws/{cep}/json/")
            dados = response.json()
            if "erro" not in dados:
                return f"{dados['logradouro']}, {dados['bairro']}, {dados['localidade']} - {dados['uf']}"
        except:
            return None
    return None

# ==========================================
# INTERFACE
# ==========================================
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["Escola (Solicitação)", "Supervisor (Avaliação)", "Relatórios"])

# ---------------------------------------------------------------------
# ABA 1: ESCOLA (SOLICITAÇÃO)
# ---------------------------------------------------------------------
if menu == "Escola (Solicitação)":
    st.title("🚌 Solicitação de Transporte Escolar")
    st.markdown("---")

    with st.form("form_escola"):
        st.subheader("1. Dados do Aluno")
        col1, col2, col3 = st.columns(3)
        nome = col1.text_input("Nome Completo do Aluno")
        cpf = col2.text_input("CPF do Aluno")
        ra = col3.text_input("R.A. do Aluno")

        col4, col5 = st.columns(2)
        cadeirante = col4.radio("Aluno Cadeirante?", ["NÃO", "SIM"], horizontal=True)
        cid = col5.text_input("CID (Código Internacional de Doenças)")

        # Busca de CEP
        st.markdown("##### Endereço Residencial")
        col_cep, col_end = st.columns([1, 3])
        cep_input = col_cep.text_input("CEP (somente números)")
        
        # Lógica simples para sugerir endereço no label (limitação do form streamit)
        endereco_sugerido = ""
        if cep_input:
            end_encontrado = buscar_endereco_cep(cep_input)
            if end_encontrado:
                st.info(f"CEP Encontrado: {end_encontrado}")
                endereco_sugerido = end_encontrado
            else:
                st.warning("CEP não encontrado ou inválido.")
        
        endereco_aluno = col_end.text_input("Endereço Completo e Número", value=endereco_sugerido)

        st.subheader("2. Dados da Unidade Escolar e Frequência")
        nome_escola = st.text_input("Nome da Unidade Escolar ou Instituição Credenciada")
        end_escola = st.text_input("Endereço da Unidade Escolar")
        
        col6, col7 = st.columns(2)
        sala_recurso = col6.radio("Frequenta Sala de Recurso?", ["NÃO", "SIM"], horizontal=True)
        
        st.markdown("##### Frequência")
        col_dias, col_hrs = st.columns(2)
        dias_freq = col_dias.multiselect("Dias de Frequência", 
                                         ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"])
        hrs_freq = col_hrs.text_input("Horários (Ex: Entrada 07:00 / Saída 12:00)")

        st.subheader("3. Documentação Obrigatória")
        doc_medico = st.file_uploader("Ficha Médica", type=['pdf', 'jpg', 'png'])
        doc_viagem = st.file_uploader("Ficha de Programação de Viagem", type=['pdf', 'jpg', 'png'])

        submitted = st.form_submit_button("Enviar Solicitação")

        if submitted:
            if nome and cpf and ra and doc_medico and doc_viagem:
                # Converter arquivos para binário
                bin_medico = doc_medico.getvalue()
                bin_viagem = doc_viagem.getvalue()
                dias_str = ", ".join(dias_freq)

                c.execute('''
                    INSERT INTO solicitacoes (
                        nome_aluno, cpf_aluno, ra_aluno, cadeirante, cid, 
                        cep_aluno, endereco_aluno, nome_escola, endereco_escola, 
                        sala_recurso, dias_frequencia, horarios_frequencia,
                        arquivo_medico, nome_arq_medico, arquivo_viagem, nome_arq_viagem
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    nome, cpf, ra, cadeirante, cid, cep_input, endereco_aluno,
                    nome_escola, end_escola, sala_recurso, dias_str, hrs_freq,
                    bin_medico, doc_medico.name, bin_viagem, doc_viagem.name
                ))
                conn.commit()
                st.success(f"Solicitação para o aluno {nome} enviada com sucesso!")
            else:
                st.error("Por favor, preencha os campos obrigatórios e anexe os documentos.")

# ---------------------------------------------------------------------
# ABA 2: SUPERVISOR (AVALIAÇÃO)
# ---------------------------------------------------------------------
elif menu == "Supervisor (Avaliação)":
    st.title("📋 Avaliação do Supervisor / PEC")
    
    # Identificação do Supervisor
    st.sidebar.markdown("### Identificação")
    nome_sup = st.sidebar.text_input("Nome do Supervisor ou PEC")
    cpf_sup = st.sidebar.text_input("CPF do Supervisor")

    # Lista de Pendentes
    df_pendentes = pd.read_sql("SELECT id, nome_aluno, status FROM solicitacoes WHERE status='Pendente'", conn)
    
    if not df_pendentes.empty:
        aluno_selecionado = st.selectbox("Selecione um Aluno para Avaliar:", df_pendentes['nome_aluno'])
        
        # Pegar ID do aluno selecionado
        id_aluno = df_pendentes[df_pendentes['nome_aluno'] == aluno_selecionado].iloc[0]['id']
        
        # Buscar dados completos do aluno
        c.execute("SELECT * FROM solicitacoes WHERE id=?", (id_aluno,))
        dados = c.fetchone()
        # Mapeando colunas pelo índice (baseado na ordem de criação da tabela ou row_factory)
        # 1=nome, 2=cpf, 3=ra, 4=cadeirante, 5=cid, 7=endereço, ...
        
        st.markdown("---")
        col_detalhes1, col_detalhes2 = st.columns(2)
        
        with col_detalhes1:
            st.markdown(f"**Aluno:** {dados[1]}")
            st.markdown(f"**CPF:** {dados[2]}")
            st.markdown(f"**R.A.:** {dados[3]}")
            st.markdown(f"**Cadeirante:** {dados[4]}")
            st.markdown(f"**CID:** {dados[5]}")
            st.markdown(f"**Endereço:** {dados[7]}")
            
        with col_detalhes2:
            st.markdown(f"**Escola:** {dados[8]}")
            st.markdown(f"**Sala Recurso:** {dados[10]}")
            st.markdown(f"**Dias:** {dados[11]}")
            st.markdown(f"**Horários:** {dados[12]}")

        st.markdown("### 📂 Documentos do Aluno")
        col_docs1, col_docs2 = st.columns(2)
        
        # Botões de Download
        if dados[13]: # Arquivo Medico
            col_docs1.download_button(label=f"⬇️ Baixar Ficha Médica", 
                                      data=dados[13], 
                                      file_name=dados[14] or "ficha_medica.pdf")
        
        if dados[15]: # Arquivo Viagem
            col_docs2.download_button(label=f"⬇️ Baixar Ficha Viagem", 
                                      data=dados[15], 
                                      file_name=dados[16] or "ficha_viagem.pdf")

        st.markdown("---")
        st.subheader("Decisão do Supervisor")
        
        with st.form("form_validacao"):
            decisao = st.radio("Parecer Final:", ["Aprovar Solicitação", "Reprovar Solicitação"])
            
            motivo = None
            if decisao == "Reprovar Solicitação":
                motivo = st.selectbox("Motivo da Reprovação:", [
                    "Falta de documentação",
                    "Aluno não elegível ao transporte",
                    "Reavaliação da Necessidade do Transporte"
                ])
            
            arquivo_assinado = st.file_uploader("Incluir Arquivos Assinados (Obrigatório para finalizar)", 
                                                type=['pdf', 'jpg', 'png'])
            
            btn_avaliar = st.form_submit_button("Finalizar Avaliação")
            
            if btn_avaliar:
                if not nome_sup or not cpf_sup:
                    st.error("Preencha seu Nome e CPF na barra lateral antes de finalizar.")
                elif not arquivo_assinado:
                    st.error("É necessário incluir o arquivo assinado para registrar a avaliação.")
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
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_aluno))
                    conn.commit()
                    st.success("Avaliação registrada com sucesso!")
                    st.rerun()

    else:
        st.info("Nenhuma solicitação pendente no momento.")

# ---------------------------------------------------------------------
# ABA 3: RELATÓRIOS
# ---------------------------------------------------------------------
elif menu == "Relatórios":
    st.title("📊 Relatório Geral")
    
    df = pd.read_sql("SELECT id, nome_aluno, cpf_aluno, ra_aluno, nome_escola, status, motivo_reprovacao FROM solicitacoes", conn)
    st.dataframe(df)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Planilha Completa (CSV)", data=csv, file_name="relatorio_geral.csv", mime="text/csv")

