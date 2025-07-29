import pandas as pd
import streamlit as st

COLUMNS_REQUERIDAS = ["Cliente", "Días Retorno"]


def cargar_excel():
    st.subheader("📁 Carga de archivo Excel")

    archivo = st.file_uploader("Selecciona el archivo .xlsx con pedidos", type=["xlsx"])

    if archivo:
        try:
            df = pd.read_excel(archivo)

            # Validación de columnas
            if not all(col in df.columns for col in COLUMNS_REQUERIDAS):
                st.error(f"❌ El archivo debe contener las columnas: {', '.join(COLUMNS_REQUERIDAS)}")
                return None

            # Limpieza de valores nulos y tipos
            df = df[COLUMNS_REQUERIDAS].dropna()
            df["Días Retorno"] = df["Días Retorno"].astype(int)
            df["Cliente"] = df["Cliente"].astype(str)

            st.success("✅ Archivo cargado correctamente")
            return df

        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            return None
    else:
        st.info("Sube un archivo para continuar.")
        return None