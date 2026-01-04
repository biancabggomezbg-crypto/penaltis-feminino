import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Penáltis", layout="wide", page_icon="⚽")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Criamos a conexão. O nome "gsheets" refere-se ao que configuramos no secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

# Nomes das Abas na Planilha (Têm de ser iguais aos que criaste no Google Sheets)
ABA_ATLETAS = "Atletas"
ABA_TREINOS = "Treinos"

# Zonas da baliza
ZONAS = [
    "Alto Esquerdo", "Alto Direito",
    "MA Esquerdo", "MA Direito",
    "Canto Esquerdo", "Canto Direito", 
    "Centro"
]

# --- FUNÇÕES ---

def carregar_dados(aba, colunas_padrao):
    """
    Carrega dados do Google Sheets.
    ttl=0 significa que ele não guarda cache, lê sempre o dado mais novo.
    """
    try:
        df = conn.read(worksheet=aba, ttl=0)
        # Se a aba estiver vazia ou com colunas erradas, devolve vazio mas com a estrutura certa
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=colunas_padrao)
        # Garante que não há linhas vazias que o Google Sheets às vezes traz
        df = df.dropna(how="all")
        return df
    except Exception as e:
        # Se der erro (ex: aba não existe), retorna vazio para não quebrar o site
        return pd.DataFrame(columns=colunas_padrao)

def salvar_dados(df, aba):
    """
    Salva os dados no Google Sheets e limpa o cache para atualizar na hora.
    """
    conn.update(worksheet=aba, data=df)
    st.cache_data.clear() # Força o Streamlit a recarregar os dados

def calcular_estatisticas(df_atletas, df_hist):
    dados_consolidados = []
    # Se não houver histórico, retornamos apenas os atletas zerados
    if df_hist.empty:
        for _, row in df_atletas.iterrows():
            dados_consolidados.append({
                "Nome": row["Nome"],
                "Pé Dominante": row["Pe Dominante"],
                "Cobranças Totais": 0, "Gols": 0, "Erros": 0,
                "Aproveitamento (%)": 0.0, "Canto Preferido": "-"
            })
        return pd.DataFrame(dados_consolidados)

    for _, row in df_atletas.iterrows():
        nome = row["Nome"]
        pe = row["Pe Dominante"]
        chutes_atleta = df_hist[df_hist["Nome"] == nome]
        
        total = len(chutes_atleta)
        golos = len(chutes_atleta[chutes_atleta["Resultado"] == "Golo"])
        erros = len(chutes_atleta[chutes_atleta["Resultado"] == "Erro"])
        aproveitamento = (golos / total * 100) if total > 0 else 0.0
        
        if total > 0:
            canto_pref = chutes_atleta["Zona"].mode()
            canto_str = canto_pref[0] if not canto_pref.empty else "N/A"
        else:
            canto_str = "-"

        dados_consolidados.append({
            "Nome": nome, "Pé Dominante": pe, "Cobranças Totais": total,
            "Gols": golos, "Erros": erros,
            "Aproveitamento (%)": round(aproveitamento, 1),
            "Canto Preferido": canto_str
        })
    return pd.DataFrame(dados_consolidados)

# --- PROGRAMA PRINCIPAL ---
st.title("⚽ Controle de Penáltis - Feminino (Online)")

# Carrega os dados da Nuvem
df_atletas = carregar_dados(ABA_ATLETAS, ["Nome", "Pe Dominante"])
df_historico = carregar_dados(ABA_TREINOS, ["Data", "Nome", "Zona", "Resultado"])

aba_registro, aba_ranking, aba_gestao = st.tabs(["📝 Registrar Treino", "🏆 Ranking & Dados", "⚙️ Gestão de Atletas"])

# ABA 1: REGISTRAR
with aba_registro:
    if df_atletas.empty:
        st.warning("Vá para a aba 'Gestão' e cadastre as atletas primeiro!")
    else:
        st.subheader("Novo Registro")
        col1, col2 = st.columns(2)
        with col1:
            data_treino = st.date_input("Data do Treino", datetime.now())
        with col2:
            nomes_lista = sorted(df_atletas["Nome"].unique())
            atleta_selecionada = st.selectbox("Selecione a Atleta", nomes_lista)

        st.divider()
        st.write("📍 **Onde foi o chute?**")
        zona_selecionada = st.radio("Selecione a zona:", ZONAS, horizontal=True)
        st.divider()

        col_g, col_p = st.columns(2)
        
        # Função auxiliar para registrar
        def registrar_chute(resultado):
            novo_reg = pd.DataFrame([{
                "Data": data_treino.strftime("%Y-%m-%d"), # Formata a data para string
                "Nome": atleta_selecionada, 
                "Zona": zona_selecionada, 
                "Resultado": resultado
            }])
            # Concatena e salva
            df_novo_historico = pd.concat([df_historico, novo_reg], ignore_index=True)
            salvar_dados(df_novo_historico, ABA_TREINOS)
            return True

        with col_g:
            if st.button("⚽ GOL", type="primary", use_container_width=True):
                with st.spinner("Salvando na nuvem..."):
                    registrar_chute("Golo")
                st.success("GOL registrado com sucesso!")
                st.rerun() # Atualiza a página
                
        with col_p:
            if st.button("❌ ERRO", type="secondary", use_container_width=True):
                with st.spinner("Salvando na nuvem..."):
                    registrar_chute("Erro")
                st.error("ERRO registrado!")
                st.rerun() # Atualiza a página

# ABA 2: RANKING
with aba_ranking:
    st.subheader("Compilado Geral")
    if df_atletas.empty:
        st.info("Cadastre atletas para ver o ranking.")
    else:
        df_final = calcular_estatisticas(df_atletas, df_historico)
        
        c1, c2 = st.columns([1, 3])
        with c1:
            ordenar_por = st.selectbox("Ordenar por:", ["Aproveitamento (%)", "Nome", "Erros", "Gols"])
        
        ascending = True if ordenar_por == "Nome" or ordenar_por == "Erros" else False
        df_exibicao = df_final.sort_values(by=ordenar_por, ascending=ascending)

        st.dataframe(df_exibicao.style.background_gradient(subset=["Aproveitamento (%)"], cmap="Greens"), use_container_width=True, hide_index=True)
        
        st.divider()
        # Botão de Download
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Relatório (CSV)", data=csv, file_name='relatorio_penaltis.csv', mime='text/csv')

# ABA 3: GESTÃO
with aba_gestao:
    c1, c2 = st.columns(2)
    with c1:
        st.write("### Adicionar Atleta")
        novo_nome = st.text_input("Nome:")
        novo_pe = st.selectbox("Pé Dominante:", ["Destra", "Canhota", "Ambidestra"])
        
        if st.button("Salvar Atleta"):
            if novo_nome and novo_nome not in df_atletas["Nome"].values:
                with st.spinner("Salvando na nuvem..."):
                    novo_df = pd.DataFrame([{"Nome": novo_nome, "Pe Dominante": novo_pe}])
                    df_atletas_atualizado = pd.concat([df_atletas, novo_df], ignore_index=True)
                    salvar_dados(df_atletas_atualizado, ABA_ATLETAS)
                st.success("Cadastrada!")
                st.rerun()
            elif novo_nome in df_atletas["Nome"].values:
                st.warning("Atleta já existe!")
                
    with c2:
        st.write("### Excluir Atleta")
        if not df_atletas.empty:
            nome_apagar = st.selectbox("Selecione para excluir:", df_atletas["Nome"].unique())
            if st.button("🗑️ Excluir"):
                with st.spinner("Apagando..."):
                    df_atletas_atualizado = df_atletas[df_atletas["Nome"] != nome_apagar]
                    salvar_dados(df_atletas_atualizado, ABA_ATLETAS)
                st.warning("Removida.")
                st.rerun()
