# 1. Imports (Igual que antes + json para dumps)
import streamlit as st
import json # Necesario para convertir el diccionario a string JSON para descarga
import os
import math
from datetime import datetime, timedelta
import pandas as pd
import traceback # Para el bloque de error general al final

# --- Constantes y Configuración ---
ARCHIVO_DATOS = "stock_data_hist.json"
LEAD_TIME_FIJO = 3
DIAS_SEGURIDAD_FIJOS = 3
DIAS_PROMEDIO = 30
DIAS_HISTORIAL_MAX = 90

# --- Funciones Auxiliares (cargar_datos, guardar_datos, calcular_promedio_ventas - SIN CAMBIOS) ---
def cargar_datos(archivo):
    if os.path.exists(archivo):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                if not contenido: return {}
                return json.loads(contenido)
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error al cargar '{archivo}': {e}. Se empezará vacío.")
            return {}
        except Exception as e:
             st.error(f"Error inesperado al cargar datos: {e}")
             return {}
    else: return {}

def guardar_datos(archivo, datos):
    try:
        hoy = datetime.now().date()
        fecha_limite = hoy - timedelta(days=DIAS_HISTORIAL_MAX)
        for nombre_prod, data_prod in datos.items():
            if not isinstance(data_prod, dict):
                 datos[nombre_prod] = {"ventas_historico": []}; continue
            if "ventas_historico" in data_prod and isinstance(data_prod["ventas_historico"], list):
                historial_nuevo = []
                for venta in data_prod["ventas_historico"]:
                     if isinstance(venta, dict) and isinstance(venta.get("fecha"), str) and len(venta["fecha"]) == 10 and "cantidad" in venta:
                         try:
                             fecha_venta_obj = datetime.strptime(venta["fecha"], "%Y-%m-%d").date()
                             if fecha_venta_obj >= fecha_limite:
                                 if isinstance(venta["cantidad"], (int, float)) and venta["cantidad"] >= 0:
                                     historial_nuevo.append(venta)
                         except (ValueError, TypeError): pass
                historial_nuevo.sort(key=lambda x: x.get("fecha", "0000-00-00"), reverse=True)
                datos[nombre_prod]["ventas_historico"] = historial_nuevo
            elif "ventas_historico" not in data_prod:
                 datos[nombre_prod]["ventas_historico"] = []
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error al guardar datos en '{archivo}': {e}")
        return False

def calcular_promedio_ventas(historial, dias_ventana):
    if not historial or not isinstance(historial, list): return 0.0
    hoy = datetime.now().date()
    fecha_inicio_ventana = hoy - timedelta(days=dias_ventana)
    total_ventas_ventana = 0
    fechas_validas = []
    for venta in historial:
        if isinstance(venta, dict) and isinstance(venta.get("fecha"), str) and len(venta["fecha"]) == 10:
            try:
                fecha_venta = datetime.strptime(venta["fecha"], "%Y-%m-%d").date()
                fechas_validas.append(fecha_venta)
                if fecha_inicio_ventana <= fecha_venta <= hoy:
                    cantidad = venta.get("cantidad", 0)
                    if isinstance(cantidad, (int, float)) and cantidad >= 0:
                        total_ventas_ventana += cantidad
            except (ValueError, TypeError): continue
    if not fechas_validas: return 0.0
    primera_fecha_venta = min(fechas_validas)
    dias_desde_primera_venta = (hoy - primera_fecha_venta).days + 1
    denominador = min(dias_desde_primera_venta, dias_ventana)
    denominador = max(1, denominador)
    promedio_diario = total_ventas_ventana / denominador
    return promedio_diario

# --- Lógica de la Aplicación Streamlit ---

st.set_page_config(layout="wide", page_title="Stock Óptimo")
st.title("📊 Calculadora de Stock Óptimo")

# Inicializar Estado de Sesión
if 'productos_data' not in st.session_state:
    st.session_state.productos_data = cargar_datos(ARCHIVO_DATOS)
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None
if 'show_create_form' not in st.session_state:
     st.session_state.show_create_form = False

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("📦 Productos")

    # Crear Nuevo Producto (Formulario Condicional)
    if st.button("➕ Crear Nuevo Producto", key="toggle_create"):
         st.session_state.show_create_form = not st.session_state.show_create_form
    if st.session_state.show_create_form:
        with st.form("create_form", clear_on_submit=True):
             new_prod_name_input = st.text_input("Nombre del Nuevo Producto:")
             submitted_create = st.form_submit_button("Crear y Seleccionar")
             if submitted_create:
                 new_prod_name = new_prod_name_input.strip()
                 if not new_prod_name: st.warning("El nombre no puede estar vacío.")
                 elif new_prod_name in st.session_state.productos_data:
                     st.warning(f"'{new_prod_name}' ya existe. Seleccionado.")
                     st.session_state.selected_product = new_prod_name
                     st.session_state.show_create_form = False
                     st.rerun()
                 else:
                     st.session_state.productos_data[new_prod_name] = {"ventas_historico": []}
                     if guardar_datos(ARCHIVO_DATOS, st.session_state.productos_data):
                         st.success(f"Producto '{new_prod_name}' creado.")
                         st.session_state.selected_product = new_prod_name
                         st.session_state.show_create_form = False
                         st.rerun()
                     else:
                          if new_prod_name in st.session_state.productos_data: # Revertir si falla guardado
                               del st.session_state.productos_data[new_prod_name]

    st.divider()

    # Selección de Producto Existente
    lista_productos_sorted = sorted(st.session_state.productos_data.keys())
    options = ["-- Selecciona un Producto --"] + lista_productos_sorted
    current_selection_index = 0
    if st.session_state.selected_product and st.session_state.selected_product in options:
        try: current_selection_index = options.index(st.session_state.selected_product)
        except ValueError: st.session_state.selected_product = None
    selected = st.selectbox( "Selecciona Existente:", options=options, index=current_selection_index, key="product_selector")
    if selected == "-- Selecciona un Producto --":
        if st.session_state.selected_product is not None: st.session_state.selected_product = None; st.rerun()
    elif selected != st.session_state.selected_product:
        st.session_state.selected_product = selected; st.rerun()

    # --- Sección de Gestión de Datos (con Descarga) --- <<< NUEVO
    st.divider()
    st.subheader("💾 Gestión de Datos")

    # Preparar datos para descarga (convertir dict a string JSON)
    if st.session_state.productos_data: # Solo mostrar si hay datos
        try:
            json_string = json.dumps(
                st.session_state.productos_data,
                indent=4,
                ensure_ascii=False
            )
            st.download_button(
                label="📥 Descargar Datos (JSON)",
                data=json_string,
                file_name=ARCHIVO_DATOS, # Nombre del archivo a descargar
                mime="application/json" # Tipo de archivo
            )
        except Exception as e:
            st.error(f"Error al preparar datos para descarga: {e}")
    else:
        st.info("No hay datos para descargar todavía.")


# --- Panel Principal ---
if st.session_state.selected_product:
    st.header(f"📈 Detalles: {st.session_state.selected_product}")

    # Asegurar que los datos del producto existen en el estado de sesión
    if st.session_state.selected_product not in st.session_state.productos_data:
         st.error("Error: El producto seleccionado ya no existe en los datos. Por favor, recarga o selecciona otro.")
         st.stop() # Detener ejecución si el producto no está

    producto_actual = st.session_state.productos_data[st.session_state.selected_product]
    historial_actual = producto_actual.get("ventas_historico", [])
    if not isinstance(historial_actual, list): historial_actual = []

    # Formulario para Agregar Venta
    with st.form("venta_form"):
        st.subheader("➕ Agregar Venta")
        col1, col2 = st.columns([1, 2])
        with col1: input_fecha = st.date_input("Fecha Venta", value=datetime.now().date(), key="fecha_venta")
        with col2: input_cantidad = st.number_input("Cantidad Vendida", min_value=0, step=1, key="cantidad_venta")
        submitted_venta = st.form_submit_button("💾 Guardar Venta y Recalcular Stock")

        if submitted_venta:
            fecha_str = input_fecha.strftime('%Y-%m-%d')
            cantidad = input_cantidad
            entrada_modificada = False; indice_existente = -1
            for i, venta in enumerate(historial_actual):
                 if isinstance(venta, dict) and venta.get("fecha") == fecha_str: indice_existente = i; break
            if indice_existente != -1:
                 if historial_actual[indice_existente].get("cantidad") != cantidad:
                     historial_actual[indice_existente]["cantidad"] = cantidad
                     st.info(f"Venta del {fecha_str} actualizada a {cantidad} unidades.")
                     entrada_modificada = True
                 else: st.info(f"Venta para {fecha_str} ya registrada (sin cambios)."); entrada_modificada = True # O False si no se quiere recalcular
            else:
                 historial_actual.append({"fecha": fecha_str, "cantidad": cantidad})
                 historial_actual.sort(key=lambda x: x.get("fecha", "0000-00-00"), reverse=True)
                 st.success(f"Venta del {fecha_str} ({cantidad} uds) agregada.")
                 entrada_modificada = True
            if entrada_modificada:
                 st.session_state.productos_data[st.session_state.selected_product]["ventas_historico"] = historial_actual
                 if guardar_datos(ARCHIVO_DATOS, st.session_state.productos_data): st.rerun()
                 # else: Error ya mostrado por guardar_datos

    st.divider()

    # Mostrar Resultados
    st.subheader("📊 Recomendaciones de Stock")
    promedio = calcular_promedio_ventas(historial_actual, DIAS_PROMEDIO)
    demanda_lt = promedio * LEAD_TIME_FIJO; stock_seg = promedio * DIAS_SEGURIDAD_FIJOS
    optimo = math.ceil(demanda_lt + stock_seg); pedido = math.ceil(demanda_lt + stock_seg)
    col_res1, col_res2, col_res3 = st.columns(3)
    with col_res1: st.metric(label=f"Prom. Diario ({DIAS_PROMEDIO}d)", value=f"{promedio:.2f}")
    with col_res2: st.metric(label="Stock Óptimo Sugerido", value=f"{optimo}")
    with col_res3: st.metric(label="Punto de Pedido", value=f"{pedido}")
    st.caption(f"Cálculos basados en Lead Time={LEAD_TIME_FIJO}d y Seguridad={DIAS_SEGURIDAD_FIJOS}d.")

    st.divider()

    # Mostrar Historial
    st.subheader("📜 Historial Reciente")
    if not historial_actual: st.info("No hay ventas registradas.")
    else:
        try:
            df_historial = pd.DataFrame(historial_actual)
            df_historial['cantidad'] = pd.to_numeric(df_historial['cantidad'], errors='coerce').fillna(0).astype(int)
            df_historial['fecha'] = pd.to_datetime(df_historial['fecha'])
            df_historial = df_historial.sort_values(by='fecha', ascending=False)
            df_historial['fecha'] = df_historial['fecha'].dt.strftime('%Y-%m-%d')
            st.dataframe(df_historial[['fecha', 'cantidad']].head(30), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error al mostrar el historial con Pandas: {e}")
            hist_texto = "\n".join([f"{v.get('fecha', '??')}: {v.get('cantidad', '??')} uds" for v in historial_actual[:30]])
            st.text_area("Ventas", hist_texto, height=200, disabled=True)

else:
    st.info("⬅️ Selecciona un producto de la barra lateral o crea uno nuevo para empezar.")


# --- Bloque Final de Captura de Errores (Opcional pero útil) ---
# (Este bloque no es estrictamente necesario para la funcionalidad principal,
# pero puede ayudar si la app falla completamente al inicio)
# try:
#     # El código principal de Streamlit ya se ejecutó hasta aquí
#     pass
# except Exception as e:
#     st.error(f"¡ERROR FATAL DE LA APLICACIÓN!\n{e}")
#     st.code(traceback.format_exc())
