import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import time

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Gestão de Transporte Escolar", layout="wide")

# ==========================================
# CONEXÃO E MIGRATION DO BANCO DE DADOS
# ==========================================
# Usando V4 para garantir a criação limpa das novas tabelas de usuário e coluna empresa
DB_NAME = 'transporte_v4.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Tabela de Solicitações (Dados do Aluno)
    c.execute('''
    CREATE TABLE IF NOT EXISTS solicitacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_aluno TEXT, cpf_aluno TEXT, ra_aluno TEXT, cadeirante TEXT, cid TEXT,
        cep_aluno TEXT, logradouro_aluno TEXT, numero_aluno TEXT, municipio_aluno TEXT,
        nome_escola TEXT, cep_escola TEXT, logradouro_escola TEXT, numero_escola TEXT, municipio_escola TEXT,
        sala_recurso TEXT, dias_frequencia TEXT, horario_entrada TEXT, horario_saida TEXT,
        arquivo_medico BLOB, nome_arq_medico TEXT, arquivo_viagem BLOB, nome_arq_viagem TEXT,
        status TEXT DEFAULT 'Pendente', supervisor_nome TEXT, supervisor_cpf TEXT,
        motivo_reprovacao TEXT, arquivo_assinado BLOB, nome_arq_assinado TEXT, data_atualizacao TEXT
    )
    ''')
    
    # 2. Tabela de Usuários (Gestão de Acesso)
    c.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_completo TEXT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        perfis TEXT NOT NULL -- Perfis separados por vírgula ex: "ADM,Escola"
    )
    ''')
    
    # 3. Migration: Adicionar coluna 'empresa' se não existir na tabela solicitacoes
    try:
        c.execute("ALTER TABLE solicitacoes ADD COLUMN empresa TEXT")
    except sqlite3.OperationalError:
        pass # Coluna já existe
        
    # 4. Criar usuário ADM padrão se não existir
    c.execute("SELECT * FROM usuarios WHERE username = 'adm'")
    if not c.fetchone():
        # Perfis salvos como string separada por vírgula
        c.execute("INSERT INTO usuarios (nome_completo, username, password, perfis) VALUES (?, ?, ?, ?)",
                  ("Administrador do Sistema", "adm", "Adm12345", "ADM"))
        
    conn.commit()
    conn.close()

# Inicializa o banco ao abrir o app
init_db()

# ==========================================
# FUNÇÕES DE AUTENTICAÇÃO E SESSÃO
# ==========================================

def verificar_credenciais(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 Transporte Escolar</h1>", unsafe_allow_html=True)
    
    # Se já validou senha mas tem múltiplos perfis, mostra seleção
    if st.session_state.get("auth_success") and st.session_state.get("pending_roles"):
        st.info(f"Olá, {st.session_state.temp_user_name}!")
        roles = st.session_state.pending_roles
        
        st.markdown("### Selecione o Perfil de Acesso:")
        role_selected = st.selectbox("Perfil:", roles)
        
        if st.button("Acessar Painel"):
            st.session_state.logged_in = True
            st.session_state.user_role = role_selected
            st.session_state.user_name = st.session_state.temp_user_name
            st.session_state.username_login = st.session_state.temp_username_login
            
            # Limpa variaveis temporarias
            del st.session_state.auth_success
            del st.session_state.pending_roles
            del st.session_state.temp_user_name
            del st.session_state.temp_username_login
            st.rerun()
            
    else:
        # Tela de Login Padrão
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("login_form"):
                user_input = st.text_input("Usuário")
                pass_input = st.text_input("Senha", type="password")
                submit = st.form_submit_button("Entrar")
                
                if submit:
                    user_db = verificar_credenciais(user_input, pass_input)
                    if user_db:
                        perfis_str = user_db["perfis"]
                        lista_perfis = [p.strip() for p in perfis_str.split(",")]
                        
                        # Se tiver só um perfil, loga direto
                        if len(lista_perfis) == 1:
                            st.session_state.logged_in = True
                            st.session_state.user_role = lista_perfis[0]
                            st.session_state.user_name = user_db["nome_completo"]
                            st.session_state.username_login = user_db["username"]
                            st.rerun()
                        else:
                            # Se tiver mais de um, marca flag para mostrar o selectbox
                            st.session_state.auth_success = True
                            st.session_state.pending_roles = lista_perfis
                            st.session_state.temp_user_name = user_db["nome_completo"]
                            st.session_state.temp_username_login = user_db["username"]
                            st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

# Inicializa variáveis de sessão
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ==========================================
# FUNÇÕES AUXILIARES GERAIS
# ==========================================
def buscar_dados_cep(cep):
    if not cep: return None
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
# LÓGICA PRINCIPAL (APP)
# ==========================================

if not st.session_state.logged_in:
    login_screen()
else:
    # --- BARRA LATERAL (SIDEBAR) ---
    st.sidebar.title(f"👤 {st.session_state.user_name}")
    st.sidebar.caption(f"Perfil: {st.session_state.user_role}")
    
    # Definição de Menus por Perfil
    opcoes_menu = []
    
    role = st.session_state.user_role
    
    if role == "ADM":
        opcoes_menu = ["Escola (Solicitação)", "Supervisor (Avaliação)", "Relatórios e Docs", "Gestão de Acesso"]
    elif role == "Escola":
        opcoes_menu = ["Escola (Solicitação)"]
    elif role == "Supervisor":
        opcoes_menu = ["Escola (Solicitação)", "Supervisor (Avaliação)"]
    
    menu = st.sidebar.radio("Navegação:", opcoes_menu)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair / Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    conn = get_db_connection()
    c = conn.cursor()

    # ==========================================
    # 1. ESCOLA (SOLICITAÇÃO)
    # ==========================================
    if menu == "Escola (Solicitação)":
        st.title("🚌 Transporte Escolar - Solicitação")
        st.markdown("---")

        # Se for Supervisor ou ADM visualizando a tela da escola, bloqueia campos
        # Mas ADM pode querer testar, então vamos bloquear apenas Supervisor
        disable_widgets = True if role == "Supervisor" else False
        
        if disable_widgets:
            st.warning("🔒 MODO VISUALIZAÇÃO: Seu perfil permite apenas visualizar este formulário.")

        with st.form("form_escola"):
            st.subheader("1. Dados do Aluno")
            c1, c2, c3 = st.columns(3)
            nome = c1.text_input("Nome Completo", disabled=disable_widgets)
            cpf = c2.text_input("CPF", disabled=disable_widgets)
            ra = c3.text_input("R.A.", disabled=disable_widgets)

            c4, c5 = st.columns(2)
            cadeirante = c4.radio("Cadeirante?", ["NÃO", "SIM"], horizontal=True, disabled=disable_widgets)
            cid = c5.text_input("CID", disabled=disable_widgets)

            st.markdown("##### Endereço Residencial")
            c_cep, c_dummy = st.columns([1, 2])
            cep_aluno = c_cep.text_input("CEP Residencial", disabled=disable_widgets)
            
            # Busca de CEP simplificada
            log_sugg = ""
            mun_sugg = ""
            if not disable_widgets and cep_aluno and len(cep_aluno) >= 8:
                d = buscar_dados_cep(cep_aluno)
                if d:
                    log_sugg = f"{d['logradouro']}, {d['bairro']}"
                    mun_sugg = f"{d['localidade']} - {d['uf']}"
                    st.success(f"Endereço encontrado: {log_sugg}")

            c_end, c_num, c_mun = st.columns([3, 1, 2])
            end_aluno = c_end.text_input("Logradouro", value=log_sugg, disabled=disable_widgets)
            num_aluno = c_num.text_input("Número", disabled=disable_widgets)
            mun_aluno = c_mun.text_input("Município", value=mun_sugg, disabled=disable_widgets)

            st.subheader("2. Dados da Escola")
            nome_escola = st.text_input("Nome da Unidade", disabled=disable_widgets)
            
            c_cep2, dummy = st.columns([1, 2])
            cep_escola = c_cep2.text_input("CEP Escola", disabled=disable_widgets)
            
            log_esc_sugg = ""
            mun_esc_sugg = ""
            if not disable_widgets and cep_escola and len(cep_escola) >= 8:
                d2 = buscar_dados_cep(cep_escola)
                if d2:
                    log_esc_sugg = f"{d2['logradouro']}, {d2['bairro']}"
                    mun_esc_sugg = f"{d2['localidade']} - {d2['uf']}"
                    st.success(f"Escola encontrada: {log_esc_sugg}")

            ce2, cn2, cm2 = st.columns([3, 1, 2])
            end_escola = ce2.text_input("Logradouro Escola", value=log_esc_sugg, disabled=disable_widgets)
            num_escola = cn2.text_input("Número Escola", disabled=disable_widgets)
            mun_escola = cm2.text_input("Município Escola", value=mun_esc_sugg, disabled=disable_widgets)

            st.subheader("3. Frequência")
            sala_rec = st.radio("Sala de Recurso?", ["NÃO", "SIM"], horizontal=True, disabled=disable_widgets)
            dias = st.multiselect("Dias", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"], disabled=disable_widgets)
            
            ch1, ch2 = st.columns(2)
            hr_ent = ch1.time_input("Entrada", value=None, disabled=disable_widgets)
            hr_sai = ch2.time_input("Saída", value=None, disabled=disable_widgets)

            st.subheader("4. Documentação")
            f_med = st.file_uploader("Ficha Médica", disabled=disable_widgets)
            f_via = st.file_uploader("Ficha Viagem", disabled=disable_widgets)

            if not disable_widgets:
                if st.form_submit_button("Enviar Solicitação"):
                    if nome and cpf and ra and num_aluno and num_escola and f_med and f_via:
                        c.execute('''INSERT INTO solicitacoes (
                            nome_aluno, cpf_aluno, ra_aluno, cadeirante, cid,
                            cep_aluno, logradouro_aluno, numero_aluno, municipio_aluno,
                            nome_escola, cep_escola, logradouro_escola, numero_escola, municipio_escola,
                            sala_recurso, dias_frequencia, horario_entrada, horario_saida,
                            arquivo_medico, nome_arq_medico, arquivo_viagem, nome_arq_viagem
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (nome, cpf, ra, cadeirante, cid, cep_aluno, end_aluno, num_aluno, mun_aluno,
                         nome_escola, cep_escola, end_escola, num_escola, mun_escola,
                         sala_rec, ", ".join(dias), str(hr_ent), str(hr_sai),
                         f_med.getvalue(), f_med.name, f_via.getvalue(), f_via.name))
                        conn.commit()
                        st.success("Cadastrado com sucesso!")
                    else:
                        st.error("Preencha campos obrigatórios e anexe documentos.")

    # ==========================================
    # 2. SUPERVISOR (AVALIAÇÃO)
    # ==========================================
    elif menu == "Supervisor (Avaliação)":
        st.title("📋 Painel do Supervisor")
        
        # Filtra pendentes
        pendentes = pd.read_sql("SELECT id, nome_aluno FROM solicitacoes WHERE status='Pendente'", conn)
        
        if not pendentes.empty:
            sel = st.selectbox("Selecione:", pendentes.apply(lambda x: f"{x['id']} - {x['nome_aluno']}", axis=1))
            id_sel = int(sel.split(' - ')[0])
            
            c.execute("SELECT * FROM solicitacoes WHERE id=?", (id_sel,))
            aluno = c.fetchone()
            
            if aluno:
                st.info(f"Aluno: {aluno['nome_aluno']} (RA: {aluno['ra_aluno']})")
                
                t1, t2 = st.tabs(["Dados", "Documentos"])
                with t1:
                    st.write(f"**Endereço:** {aluno['logradouro_aluno']}, {aluno['numero_aluno']}")
                    st.write(f"**Escola:** {aluno['nome_escola']}")
                    st.write(f"**Horário:** {aluno['horario_entrada']} - {aluno['horario_saida']}")
                with t2:
                    c1, c2 = st.columns(2)
                    if aluno['arquivo_medico']:
                        c1.download_button("Médico", aluno['arquivo_medico'], aluno['nome_arq_medico'] or "med.pdf")
                    if aluno['arquivo_viagem']:
                        c2.download_button("Viagem", aluno['arquivo_viagem'], aluno['nome_arq_viagem'] or "via.pdf")
                
                st.markdown("---")
                with st.form("valida_sup"):
                    st.markdown("#### Identificação e Parecer")
                    # Se for supervisor, tenta pegar nome da sessão, senão deixa digitar
                    nome_padrao = st.session_state.user_name if role == "Supervisor" else ""
                    
                    nome_sup = st.text_input("Nome Supervisor", value=nome_padrao)
                    cpf_sup = st.text_input("CPF Supervisor")
                    parecer = st.radio("Decisão", ["Aprovar Solicitação", "Reprovar Solicitação"])
                    
                    motivo = None
                    if parecer == "Reprovar Solicitação":
                        motivo = st.selectbox("Motivo", ["Falta de Doc", "Não elegível", "Reavaliação"])
                    
                    f_ass = st.file_uploader("Ficha Assinada (Obrigatório)")
                    
                    if st.form_submit_button("Finalizar"):
                        if nome_sup and cpf_sup and f_ass:
                            st_final = "Aprovado" if parecer == "Aprovar Solicitação" else "Reprovado"
                            c.execute('''UPDATE solicitacoes SET 
                                status=?, supervisor_nome=?, supervisor_cpf=?, motivo_reprovacao=?,
                                arquivo_assinado=?, nome_arq_assinado=?, data_atualizacao=?
                                WHERE id=?''',
                                (st_final, nome_sup, cpf_sup, motivo or "Aprovado", 
                                 f_ass.getvalue(), f_ass.name, str(datetime.now()), id_sel))
                            conn.commit()
                            st.success("Avaliação salva!")
                            st.rerun()
                        else:
                            st.error("Preencha todos os campos e anexe o arquivo.")
        else:
            st.info("Sem pendências.")

    # ==========================================
    # 3. RELATÓRIOS E DOCS (COM EDIÇÃO)
    # ==========================================
    elif menu == "Relatórios e Docs":
        st.title("🗂️ Relatório Geral e Edição")
        
        filtro = st.selectbox("Filtrar Status", ["Todos", "Pendente", "Aprovado", "Reprovado"])
        
        query = "SELECT * FROM solicitacoes"
        if filtro != "Todos":
            query += f" WHERE status = '{filtro}'"
            
        df = pd.read_sql(query, conn)
        
        # Tabela Simples
        st.dataframe(df[['id', 'nome_aluno', 'nome_escola', 'status', 'empresa', 'supervisor_nome']])
        
        st.markdown("---")
        st.subheader("Gerenciar Registros (Editar / Excluir / Docs)")
        
        registros = c.execute(query).fetchall()
        
        for reg in registros:
            # Layout do Expander: Ícone + Nome + Empresa
            empresa_lbl = f" | 🏢 {reg['empresa']}" if reg['empresa'] else ""
            label = f"🆔 {reg['id']} - {reg['nome_aluno']} ({reg['status']}){empresa_lbl}"
            
            with st.expander(label):
                
                # --- ÁREA DE DOCUMENTOS ---
                st.markdown("#### 📂 Documentos")
                cd1, cd2, cd3 = st.columns(3)
                if reg['arquivo_medico']: cd1.download_button("Ficha Médica", reg['arquivo_medico'], "med.pdf", key=f"dm{reg['id']}")
                if reg['arquivo_viagem']: cd2.download_button("Ficha Viagem", reg['arquivo_viagem'], "via.pdf", key=f"dv{reg['id']}")
                if reg['arquivo_assinado']: cd3.download_button("Parecer Assinado", reg['arquivo_assinado'], "par.pdf", key=f"da{reg['id']}")
                
                st.markdown("---")
                
                # --- ÁREA DE EDIÇÃO ---
                st.markdown("#### ✏️ Editar Informações")
                with st.form(f"edit_{reg['id']}"):
                    ce1, ce2 = st.columns(2)
                    new_nome = ce1.text_input("Nome Aluno", reg['nome_aluno'])
                    new_status = ce2.selectbox("Status", ["Pendente", "Aprovado", "Reprovado"], index=["Pendente", "Aprovado", "Reprovado"].index(reg['status']))
                    
                    ce3, ce4 = st.columns(2)
                    new_escola = ce3.text_input("Escola", reg['nome_escola'])
                    # NOVO CAMPO EMPRESA
                    new_empresa = ce4.text_input("🏢 Empresa Transportadora", value=reg['empresa'] if reg['empresa'] else "")
                    
                    c_save, c_del = st.columns([1, 4])
                    save_btn = c_save.form_submit_button("💾 Salvar Alterações")
                    
                    if save_btn:
                        c.execute("UPDATE solicitacoes SET nome_aluno=?, status=?, nome_escola=?, empresa=? WHERE id=?",
                                  (new_nome, new_status, new_escola, new_empresa, reg['id']))
                        conn.commit()
                        st.success("Atualizado!")
                        time.sleep(1)
                        st.rerun()

                # Botão de Excluir fora do form para evitar conflito de submit
                if st.button(f"🗑️ Excluir Registro {reg['id']}", key=f"del_{reg['id']}"):
                    c.execute("DELETE FROM solicitacoes WHERE id=?", (reg['id'],))
                    conn.commit()
                    st.warning("Registro excluído.")
                    time.sleep(1)
                    st.rerun()

    # ==========================================
    # 4. GESTÃO DE ACESSO (SÓ ADM)
    # ==========================================
    elif menu == "Gestão de Acesso":
        if role != "ADM":
            st.error("Acesso Negado.")
        else:
            st.title("🔐 Gestão de Usuários")
            
            # --- Formulário de Cadastro ---
            with st.expander("➕ Cadastrar Novo Usuário", expanded=True):
                with st.form("new_user"):
                    u_nome = st.text_input("Nome Completo")
                    u_user = st.text_input("Usuário (Login)")
                    u_pass = st.text_input("Senha")
                    u_perfis = st.multiselect("Perfis de Acesso", ["ADM", "Escola", "Supervisor"])
                    
                    if st.form_submit_button("Cadastrar"):
                        if u_nome and u_user and u_pass and u_perfis:
                            try:
                                perfis_str = ",".join(u_perfis)
                                c.execute("INSERT INTO usuarios (nome_completo, username, password, perfis) VALUES (?,?,?,?)",
                                          (u_nome, u_user, u_pass, perfis_str))
                                conn.commit()
                                st.success(f"Usuário {u_user} criado!")
                                time.sleep(1)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Erro: Este nome de usuário já existe.")
                        else:
                            st.warning("Preencha todos os campos.")
            
            # --- Lista de Usuários ---
            st.subheader("Usuários Cadastrados")
            users = pd.read_sql("SELECT id, nome_completo, username, perfis FROM usuarios", conn)
            st.dataframe(users)
            
            # --- Exclusão Rápida ---
            st.markdown("#### Gerenciar")
            user_to_edit = st.selectbox("Selecione usuário para excluir:", users['username'])
            if st.button("Excluir Usuário Selecionado"):
                if user_to_edit == "adm":
                    st.error("Não é possível excluir o administrador principal.")
                else:
                    c.execute("DELETE FROM usuarios WHERE username=?", (user_to_edit,))
                    conn.commit()
                    st.success("Excluído.")
                    time.sleep(1)
                    st.rerun()

    conn.close()
