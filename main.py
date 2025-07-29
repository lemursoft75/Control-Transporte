import streamlit as st
import pandas as pd
from datetime import date
from utils.file_handler import cargar_excel
from utils.storage import load_units, save_units, load_calendar, save_calendar, load_pedidos_excel, save_pedidos_excel, PEDIDOS_EXCEL_PATH
from utils.calendar_logic import agregar_pedido, eliminar_pedido, editar_dias_retorno # <--- ¡Importa las nuevas funciones!
from datetime import datetime, timedelta
import os
import json


# 📌 Configuración de la app
st.set_page_config(page_title="Reyma del Sureste - Logística", layout="wide")
st.title("🚚 Planificador de Transportes | Reyma del Sureste")

# 🔄 Carga de datos persistentes al inicio de la app
units = load_units()
calendar = load_calendar()
pedidos_excel_df = load_pedidos_excel()

tabs = st.tabs(["📦 Unidades disponibles", "📥 Cargar pedidos", "🗓️ Calendario", "🧹 Limpieza"])

# 📦 Unidades disponibles (sin cambios)
with tabs[0]:
    st.subheader("🔧 Configurar unidades")
    for unidad in units:
        nuevo_valor = st.number_input(f"{unidad}", value=units[unidad], min_value=0, step=1, key=f"config_unit_{unidad}")
        units[unidad] = nuevo_valor
    save_units(units)

# 📥 Cargar pedidos (sin cambios)
with tabs[1]:
    st.subheader("📁 Cargar pedidos desde Excel")

    df_cargado_temporal = cargar_excel()

    if df_cargado_temporal is not None:
        st.info("Archivo Excel listo para ser guardado.")
        if st.button("💾 Guardar Pedidos del Excel", type="primary"):
            save_pedidos_excel(df_cargado_temporal)
            st.success("Archivo Excel cargado y guardado correctamente.")
            st.rerun()
    elif pedidos_excel_df is None:
        st.info("Por favor, sube un archivo Excel para empezar a registrar pedidos.")

    df_actual_pedidos = pedidos_excel_df

    if df_actual_pedidos is not None and not df_actual_pedidos.empty:
        st.write("---")
        st.subheader("Pedidos disponibles para registrar:")
        st.dataframe(df_actual_pedidos)

        if st.button("🗑️ Eliminar Excel cargado (permanentemente)", type="secondary"):
            if os.path.exists(PEDIDOS_EXCEL_PATH):
                os.remove(PEDIDOS_EXCEL_PATH)
                st.success("Archivo Excel de pedidos guardado eliminado.")
                st.rerun()

        st.info("Asigna unidad y fecha para cada pedido cargado:")
        for index, row in df_actual_pedidos.iterrows():
            st.markdown("---")
            cliente = row["Cliente"]
            dias_retorno = row["Días Retorno"]

            col1, col2, col3, col4 = st.columns(4)
            with col1: st.write(f"🧾 **Cliente:** {cliente}")
            with col2:
                fecha_pedido = st.date_input(f"Fecha pedido #{index + 1}", value=date.today(), key=f"fecha_{index}")
            with col3:
                unidad = st.selectbox(f"Unidad #{index + 1}", options=list(units.keys()), key=f"unidad_{index}")
            with col4:
                confirmar = st.button("➕ Registrar pedido", key=f"btn_{index}")
                if confirmar:
                    ok, mensaje = agregar_pedido(calendar, units, cliente, unidad, fecha_pedido, dias_retorno)
                    if ok:
                        st.success(mensaje)
                        save_units(units)
                        save_calendar(calendar)
                        st.rerun()
                    else:
                        st.error(mensaje)
    elif pedidos_excel_df is not None and pedidos_excel_df.empty:
        st.info("El archivo Excel cargado no contiene pedidos válidos.")


# 🗓️ Calendario - ¡Modificaciones aquí para eliminar y editar!
with tabs[2]:
    st.subheader("📆 Calendario de entregas")

    if isinstance(calendar, dict):
        # Obtener y ordenar todas las fechas presentes en el calendario
        all_dates = sorted(calendar.keys())

        # Mostrar los pedidos y retornos de cada día
        for fecha_str in all_dates:
            eventos = calendar.get(fecha_str, [])

            if not eventos:
                continue # No mostrar días que puedan haber quedado vacíos

            entregas = [e for e in eventos if e.get("tipo_evento") == "entrega"]
            retornos = [e for e in eventos if e.get("tipo_evento") == "retorno"]

            st.markdown(f"### 📅 {fecha_str}")
            resumen = f"• {len(entregas)} entrega(s), {len(retornos)} retorno(s)"
            st.caption(resumen)

            # Mostrar entregas con opción de eliminar/editar
            for i, evento in enumerate(entregas):
                col_display, col_edit_delete = st.columns([0.7, 0.3])
                with col_display:
                    emoji = "💎" if evento["cliente"].lower() in ["plastisaro", "plastinorte"] else "🚛"
                    st.success(
                        f"{emoji} **{evento['cliente']}** — {evento['unidad']} | "
                        f"🕒 Entrega: {evento['fecha_pedido']} → Regresa en {evento['dias_retorno']} días"
                    )
                with col_edit_delete:
                    # Botón de eliminar
                    if st.button(f"🗑️ Eliminar {evento['cliente'][:10]}...", key=f"del_btn_{evento['id']}_{i}"):
                        ok, msg = eliminar_pedido(calendar, units, evento['id'])
                        if ok:
                            st.success(msg)
                            save_units(units)
                            save_calendar(calendar)
                            st.rerun()
                        else:
                            st.error(msg)
                    # Editor de días de retorno
                    if st.checkbox(f"Editar días de retorno ({evento['cliente'][:10]})", key=f"edit_chk_{evento['id']}_{i}"):
                        nuevos_dias = st.number_input(
                            f"Nuevos días retorno para {evento['cliente']}",
                            value=evento['dias_retorno'],
                            min_value=1,
                            key=f"dias_input_{evento['id']}_{i}"
                        )
                        if st.button(f"Guardar edición {evento['cliente'][:10]}", key=f"save_edit_btn_{evento['id']}_{i}"):
                            ok, msg = editar_dias_retorno(calendar, units, evento['id'], nuevos_dias)
                            if ok:
                                st.success(msg)
                                save_calendar(calendar)
                                st.rerun()
                            else:
                                st.error(msg)

            # Mostrar retornos (sin opción de eliminar directamente, se eliminan con el pedido)
            for evento in retornos:
                st.info(f"🔁 Retorno de unidad: **{evento['unidad']}**")
    else:
        st.error("❌ El calendario no tiene el formato correcto.")
        st.write(calendar)


# 🧹 Limpieza (sin cambios)
with st.expander("🧼 Limpieza de datos (Expandir para ver opciones)"):
    st.warning("Esta acción eliminará todos los pedidos y unidades. No se puede deshacer.")

    if 'confirm_clean' not in st.session_state:
        st.session_state.confirm_clean = False

    st.session_state.confirm_clean = st.checkbox("Estoy seguro de querer limpiar todos los datos", key="clean_confirm_checkbox")

    if st.button("⚠️ Limpiar todo", type="primary", disabled=not st.session_state.confirm_clean):
        if st.session_state.confirm_clean:
            units_path = os.path.join("data", "units.json")
            calendar_path = os.path.join("data", "calendar.json")

            unidades_nuevas = {
                "Tráiler 53": 0,
                "Tráiler 48": 0,
                "Torton": 0,
                "Interplanta": 0
            }

            hoy = datetime.today().date()
            calendario_nuevo = {
                str(hoy + timedelta(days=i)): []
                for i in range(7)
            }

            try:
                with open(units_path, "w", encoding="utf-8") as f:
                    json.dump(unidades_nuevas, f, indent=2)

                with open(calendar_path, "w", encoding="utf-8") as f:
                    json.dump(calendario_nuevo, f, indent=2)

                if os.path.exists(PEDIDOS_EXCEL_PATH):
                    os.remove(PEDIDOS_EXCEL_PATH)

                st.success("🚿 Datos limpiados correctamente.")
                st.write("📁 Unidades reiniciadas:", unidades_nuevas)
                st.write("📅 Calendario reiniciado:", calendario_nuevo)

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al limpiar los datos: {e}")
                st.write("Por favor, verifica los permisos de los archivos o el formato de los datos.")
        else:
            st.warning("Por favor, marca la casilla 'Estoy seguro' para confirmar la limpieza.")