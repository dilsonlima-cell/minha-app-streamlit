import streamlit as st
import pandas as pd

# =============================
# Funções principais
# =============================

def sort_hierarchical(series):
    """
    Converte strings como '1.10.2' em lista [1,10,2] para permitir ordenação hierárquica correta.
    """
    return series.map(lambda v: [int(p) for p in str(v).split('.') if p.isdigit()])


def process_codes(df):
    """
    Processa DataFrame adicionando CÓDIGO FINAL e CÓDIGO PAI
    garantindo hierarquia correta e múltiplos níveis pai-filho.
    """
    # Ordenar hierarquicamente
    df = df.sort_values(by="Nº DO ITEM", key=sort_hierarchical).reset_index(drop=True)

    # Criar dicionário para mapear Nº DO ITEM -> CÓDIGO FINAL
    code_map = {}

    # Helper para encontrar o código do pai subindo a hierarquia
    def find_parent_code(item_id):
        parts = str(item_id).split('.')
        while len(parts) > 1:  # Enquanto tiver subníveis
            parts = parts[:-1]
            parent_id = '.'.join(parts)
            if parent_id in code_map:
                return code_map[parent_id]
        return None

    codigos_pai = []
    for _, row in df.iterrows():
        item_id = str(row['Nº DO ITEM'])
        codigo_final = row.get('CÓDIGO FINAL', None)

        # Atualiza dicionário
        if codigo_final and codigo_final != "NULO":
            code_map[item_id] = codigo_final

        # Encontra pai
        parent_code = find_parent_code(item_id)
        if parent_code:
            codigos_pai.append(parent_code)
        else:
            codigos_pai.append("")
            st.warning(f"⚠️ Item {item_id} não encontrou pai válido.")

    df['CÓDIGO PAI'] = codigos_pai
    return df


def load_file(uploaded_file):
    """
    Carrega Excel ou TXT automaticamente.
    """
    if uploaded_file.name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)

    elif uploaded_file.name.endswith(".txt"):
        # Tenta detectar o separador automaticamente
        try:
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        except Exception:
            # fallback para tabulação
            return pd.read_csv(uploaded_file, sep="\t")

    else:
        st.error("❌ Formato de arquivo não suportado. Envie .xlsx ou .txt")
        return None


# =============================
# Aplicação Streamlit
# =============================

st.title("📊 Classificação Hierárquica de Itens")

uploaded_file = st.file_uploader("Envie seu arquivo (.xlsx ou .txt)", type=["xlsx", "txt"])

if uploaded_file:
    df = load_file(uploaded_file)

    if df is not None:
        st.subheader("📋 Dados Originais")
        st.dataframe(df.head(20))

        # Processar hierarquia
        df_processado = process_codes(df)

        st.subheader("✅ Dados Processados")
        st.dataframe(df_processado.head(20))

        # Download do resultado
        output_file = "dados_processados.xlsx"
        df_processado.to_excel(output_file, index=False)
        with open(output_file, "rb") as f:
            st.download_button(
                label="📥 Baixar arquivo processado",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
