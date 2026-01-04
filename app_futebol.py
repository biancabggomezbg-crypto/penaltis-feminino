import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Penáltis", layout="wide", page_icon="⚽")

# Nomes dos ficheiros
ARQUIVO_ATLETAS = "atletas_db.csv"
ARQUIVO_TREINOS = "historico_treinos.csv"

# Zonas da baliza
ZONAS = [
    "Alto Esquerdo", "Alto Direito",
    "MA Esquerdo", "MA Direito",
    "Canto Esquerdo", "Canto Direito", 
    "Centro"
]

# --- FUNÇÕES ---
def carregar_atletas():
    if os.path.exists(ARQUIVO_ATLETAS):
        return pd.read_csv(ARQUIVO_ATLETAS)
    return pd.DataFrame(columns=["Nome", "Pe Dominante"])

def carregar_historico():
    if os.path.exists(ARQUIVO_TREINOS):
        return pd.read_csv(ARQUIVO_TREINOS)
    return pd.DataFrame(columns=["Data", "Nome", "Zona", "Resultado"])

def salvar_csv(df, nome_arquivo):
    df.to_csv(nome_arquivo, index=False)

def calcular_estatisticas(df_atletas, df_hist):
    dados_consolidados = []
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
st.title("⚽ Controle de Penáltis - Feminino")

df_atletas = carregar_atletas()
df_historico = carregar_historico()

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
        with col_g:
            if st.button("⚽ GOL", type="primary", use_container_width=True):
                novo_reg = pd.DataFrame([{"Data": data_treino, "Nome": atleta_selecionada, "Zona": zona_selecionada, "Resultado": "Golo"}])
                df_historico = pd.concat([df_historico, novo_reg], ignore_index=True)
                salvar_csv(df_historico, ARQUIVO_TREINOS)
                st.success("GOL registrado!")
        with col_p:
            if st.button("❌ ERRO", type="secondary", use_container_width=True):
                novo_reg = pd.DataFrame([{"Data": data_treino, "Nome": atleta_selecionada, "Zona": zona_selecionada, "Resultado": "Erro"}])
                df_historico = pd.concat([df_historico, novo_reg], ignore_index=True)
                salvar_csv(df_historico, ARQUIVO_TREINOS)
                st.error("ERRO registrado!")

# ABA 2: RANKING
with aba_ranking:
    st.subheader("Compilado Geral")
    if df_atletas.empty:
        st.info("Sem dados ainda.")
    else:
        df_final = calcular_estatisticas(df_atletas, df_historico)
        c1, c2 = st.columns([1, 3])
        with c1:
            ordenar_por = st.selectbox("Ordenar por:", ["Aproveitamento (%)", "Nome", "Erros", "Gols"])
        
        ascending = True if ordenar_por == "Nome" or ordenar_por == "Erros" else False
        df_exibicao = df_final.sort_values(by=ordenar_por, ascending=ascending)

        st.dataframe(df_exibicao.style.background_gradient(subset=["Aproveitamento (%)"], cmap="Greens"), use_container_width=True, hide_index=True)
        
        st.divider()
        # Botão de Download (Segurança)
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
                df_atletas = pd.concat([df_atletas, pd.DataFrame([{"Nome": novo_nome, "Pe Dominante": novo_pe}])], ignore_index=True)
                salvar_csv(df_atletas, ARQUIVO_ATLETAS)
                st.success("Cadastrada!")
                st.rerun()
    with c2:
        st.write("### Excluir Atleta")
        if not df_atletas.empty:
            nome_apagar = st.selectbox("Selecione para excluir:", df_atletas["Nome"].unique())
            if st.button("🗑️ Excluir"):
                df_atletas = df_atletas[df_atletas["Nome"] != nome_apagar]
                salvar_csv(df_atletas, ARQUIVO_ATLETAS)
                st.warning("Removida.")
                st.rerun()