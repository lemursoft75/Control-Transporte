import streamlit as st
import pandas as pd
from datetime import date
from utils.file_handler import cargar_excel
from utils.storage import load_units, save_units, load_calendar, save_calendar, load_pedidos_excel, save_pedidos_excel, \
    PEDIDOS_EXCEL_PATH
from utils.calendar_logic import agregar_pedido, eliminar_pedido, editar_dias_retorno
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

# 📦 Unidades disponibles - ¡Nuevas métricas aquí!
with tabs[0]:
    st.subheader("🔧 Configurar unidades base")
    for unidad in units:
        nuevo_valor = st.number_input(f"{unidad}", value=units[unidad], min_value=0, step=1,
                                      key=f"config_unit_{unidad}")
        units[unidad] = nuevo_valor
    save_units(units)

    st.markdown("---")
    st.subheader("📊 Resumen y Pronóstico de Unidades")

    hoy = datetime.today().date()
    mañana = hoy + timedelta(days=1)

    hoy_str = hoy.strftime("%Y-%m-%d")
    mañana_str = mañana.strftime("%Y-%m-%d")

    # Contadores para cargas y retornos por día (hoy y mañana)
    cargas_hoy = {unidad: 0 for unidad in units.keys()}
    retornos_hoy = {unidad: 0 for unidad in units.keys()}
    cargas_mañana = {unidad: 0 for unidad in units.keys()}
    retornos_mañana = {unidad: 0 for unidad in units.keys()}
    unidades_en_transito = {unidad: 0 for unidad in units.keys()}

    # Iterar por TODO el calendario para calcular las unidades en tránsito y los eventos del día
    for fecha_cal_str, eventos_dia in calendar.items():
        fecha_cal_dt = datetime.strptime(fecha_cal_str, "%Y-%m-%d").date()

        for evento in eventos_dia:
            if evento.get("tipo_evento") == "entrega":
                unidad_entrega = evento["unidad"]
                fecha_pedido_entrega_dt = datetime.strptime(evento["fecha_pedido"], "%Y-%m-%d").date()

                dias_retorno_para_calculo = evento.get('dias_retorno_calculados', evento['dias_retorno'])

                fecha_retorno_estimada = fecha_pedido_entrega_dt + timedelta(days=dias_retorno_para_calculo)

                if fecha_pedido_entrega_dt <= hoy and fecha_retorno_estimada > hoy:
                    unidades_en_transito[unidad_entrega] += 1

                if fecha_pedido_entrega_dt == hoy:
                    cargas_hoy[unidad_entrega] += 1
                elif fecha_pedido_entrega_dt == mañana:
                    cargas_mañana[unidad_entrega] += 1

            elif evento.get("tipo_evento") == "retorno":
                unidad_retorno = evento["unidad"]
                if fecha_cal_dt == hoy:
                    retornos_hoy[unidad_retorno] += 1
                elif fecha_cal_dt == mañana:
                    retornos_mañana[unidad_retorno] += 1

    # Preparar datos para la tabla
    data = []
    for unidad_tipo in units.keys():
        disponibles_config = units[unidad_tipo]

        # --- INICIO: CÁLCULO AJUSTADO DE "DISPONIBLES HOY (NETO)" ---
        # Primero, lo que estaría en patio si no hubiera retornos o cargas hoy
        en_patio_sin_movimientos_hoy = disponibles_config - unidades_en_transito[unidad_tipo]

        # Luego, sumar los retornos de hoy y restar las cargas de hoy
        disponibles_neto_hoy = en_patio_sin_movimientos_hoy + retornos_hoy[unidad_tipo] - cargas_hoy[unidad_tipo]
        # --- FIN: CÁLCULO AJUSTADO ---

        # Pronóstico para mañana: Disponibles Hoy (Neto) + Retornos de Mañana - Cargas de Mañana
        pronostico_mañana = disponibles_neto_hoy + retornos_mañana[unidad_tipo] - cargas_mañana[unidad_tipo]

        data.append({
            "Unidad": unidad_tipo,
            "Config. Base (Físicas)": disponibles_config,
            f"Cargas Hoy ({hoy.strftime('%d/%m')})": cargas_hoy[unidad_tipo],
            f"Retornos Hoy ({hoy.strftime('%d/%m')})": retornos_hoy[unidad_tipo],
            "En Tránsito (Ahora)": unidades_en_transito[unidad_tipo],
            f"Disponibles Hoy (Neto)": disponibles_neto_hoy,  # <--- CALCULO AJUSTADO
            f"Cargas Mañana ({mañana.strftime('%d/%m')})": cargas_mañana[unidad_tipo],
            f"Retornos Mañana ({mañana.strftime('%d/%m')})": retornos_mañana[unidad_tipo],
            f"Pronóstico Mañana ({mañana.strftime('%d/%m')})": pronostico_mañana  # <--- CALCULO AJUSTADO
        })

    df_resumen = pd.DataFrame(data)
    st.dataframe(df_resumen.set_index("Unidad"))

# 📥 Cargar pedidos - (Sin cambios en esta sección)
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

        search_cliente_registrar = st.text_input("🔍 Buscar cliente para registrar:", "",
                                                 key="search_cliente_registrar").lower()

        if search_cliente_registrar:
            df_display = df_actual_pedidos[
                df_actual_pedidos["Cliente"].astype(str).str.lower().str.contains(search_cliente_registrar)
            ]
            if df_display.empty:
                st.warning(f"No se encontraron clientes que coincidan con '{search_cliente_registrar}'.")
        else:
            df_display = df_actual_pedidos

        st.dataframe(df_display)

        if st.button("🗑️ Eliminar Excel cargado (permanentemente)", type="secondary"):
            if os.path.exists(PEDIDOS_EXCEL_PATH):
                os.remove(PEDIDOS_EXCEL_PATH)
                st.success("Archivo Excel de pedidos guardado eliminado.")
                st.rerun()

        st.info("Asigna unidad y fecha para cada pedido cargado:")
        for index, row in df_display.iterrows():
            st.markdown("---")
            cliente = row["Cliente"]
            dias_retorno = row["Días Retorno"]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"🧾 **Cliente:** {cliente}")
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

# 🗓️ Calendario - (Sin cambios en esta sección)
with tabs[2]:
    st.subheader("📆 Calendario de Pedidos")

    if isinstance(calendar, dict):
        all_dates = sorted(calendar.keys())

        found_results_calendar = False

        for fecha_str in all_dates:
            eventos = calendar.get(fecha_str, [])

            filtered_entregas = [e for e in eventos if e.get("tipo_evento") == "entrega"]
            filtered_retornos = [e for e in eventos if e.get("tipo_evento") == "retorno"]

            if not filtered_entregas and not filtered_retornos:
                continue

            found_results_calendar = True

            st.markdown(f"### 📅 {fecha_str}")
            resumen = f"• {len(filtered_entregas)} carga(s), {len(filtered_retornos)} retorno(s)"
            st.caption(resumen)

            for i, evento in enumerate(filtered_entregas):
                col_display, col_edit_delete = st.columns([0.7, 0.3])
                with col_display:
                    emoji = "💎" if evento["cliente"].lower() in ["plastisaro", "plastinorte"] else "🚛"
                    fecha_carga_dt = datetime.strptime(evento['fecha_pedido'], "%Y-%m-%d").date()

                    dias_para_calculo = evento.get('dias_retorno_calculados', evento['dias_retorno'])

                    fecha_retorno_calculada = fecha_carga_dt + timedelta(days=dias_para_calculo)

                    st.success(
                        f"{emoji} **{evento['cliente']}** — {evento['unidad']} | "
                        f"🚚 Carga: {fecha_carga_dt.strftime('%d/%m/%Y')} → Retorno: {fecha_retorno_calculada.strftime('%d/%m/%Y')}"
                    )
                with col_edit_delete:
                    if st.button(f"🗑️ Eliminar {evento['cliente'][:10]}...", key=f"del_btn_{evento['id']}_{i}"):
                        ok, msg = eliminar_pedido(calendar, units, evento['id'])
                        if ok:
                            st.success(msg)
                            save_units(units)
                            save_calendar(calendar)
                            st.rerun()
                        else:
                            st.error(msg)
                    with st.expander(f"Editar días ({evento['cliente'][:10]})"):
                        nuevos_dias = st.number_input(
                            f"Nuevos días retorno para {evento['cliente']}",
                            value=evento['dias_retorno'],
                            min_value=1,
                            key=f"dias_input_{evento['id']}_{i}"
                        )
                        if st.button(f"Guardar edición", key=f"save_edit_btn_{evento['id']}_{i}"):
                            ok, msg = editar_dias_retorno(calendar, units, evento['id'], nuevos_dias)
                            if ok:
                                st.success(msg)
                                save_calendar(calendar)
                                st.rerun()
                            else:
                                st.error(msg)

            for evento in filtered_retornos:
                cliente_retorno = evento.get("cliente_asociado", "Desconocido")
                fecha_pedido_retorno_str = evento.get("fecha_pedido_asociado", "Fecha desconocida")

                try:
                    fecha_pedido_dt = datetime.strptime(fecha_pedido_retorno_str, "%Y-%m-%d").date()
                    fecha_pedido_formateada = fecha_pedido_dt.strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    fecha_pedido_formateada = "Fecha no válida"

                st.info(
                    f"🔁 Retorno de unidad: **{evento['unidad']}** | "
                    f"Pedido: {cliente_retorno} (Carga: {fecha_pedido_formateada})"
                )

        if not found_results_calendar and not calendar:
            st.info("El calendario está vacío. Registra pedidos para verlos aquí.")

    else:
        st.error("❌ El calendario no tiene el formato correcto.")
        st.write(calendar)

# 🧹 Limpieza - (Sin cambios en esta sección)
with tabs[3]:
    with st.expander("🧼 Limpieza de datos (Expandir para ver opciones)"):
        st.warning("Esta acción eliminará todos los pedidos y unidades. No se puede deshacer.")

        if 'confirm_clean' not in st.session_state:
            st.session_state.confirm_clean = False

        st.session_state.confirm_clean = st.checkbox("Estoy seguro de querer limpiar todos los datos",
                                                     key="clean_confirm_checkbox")

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