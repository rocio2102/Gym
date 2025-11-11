import streamlit as st
import csv
from datetime import datetime
import pandas as pd
import os
import time

ARCHIVO_CSV = "asistencias.csv"

# --- Funciones de Lógica de Negocio ---

def marcar_asistencia(nombre, apellido):
    """Registra la asistencia en el archivo CSV."""
    
    ahora = datetime.now()
    fecha = ahora.strftime("%Y-%m-%d")
    hora = ahora.strftime("%H:%M:%S")

    # Si el archivo no existe o está vacío, creamos el encabezado
    file_exists = os.path.exists(ARCHIVO_CSV) and os.stat(ARCHIVO_CSV).st_size != 0

    with open(ARCHIVO_CSV, "a", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        if not file_exists:
            writer.writerow(["Fecha", "Hora", "Nombre", "Apellido"])
        writer.writerow([fecha, hora, nombre, apellido])

# ¡IMPORTANTE! Se eliminó @st.cache_data para asegurar la actualización inmediata
def leer_asistencias():
    """Lee el archivo CSV y retorna un DataFrame de Pandas."""
    try:
        # Leer el CSV directamente en un DataFrame, parseando la fecha
        df = pd.read_csv(ARCHIVO_CSV, encoding="utf-8", parse_dates=['Fecha']) 
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Fecha", "Hora", "Nombre", "Apellido"])
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["Fecha", "Hora", "Nombre", "Apellido"])

def limpiar_registros():
    """Elimina el archivo CSV, borrando todos los registros."""
    if os.path.exists(ARCHIVO_CSV):
        os.remove(ARCHIVO_CSV)
    # No es necesario llamar a st.rerun() aquí, ya se hace en la función que la llama.

# --- Funciones de Estado de Limpieza ---

# Inicializar el estado de la sesión si no existe
if 'confirmar_limpieza' not in st.session_state:
    st.session_state.confirmar_limpieza = False

# Función para solicitar confirmación
def solicitar_confirmacion():
    st.session_state.confirmar_limpieza = True

# Función para cancelar
def cancelar_limpieza():
    st.session_state.confirmar_limpieza = False
    st.rerun()

# Función para proceder con la limpieza
def ejecutar_limpieza():
    limpiar_registros()
    st.session_state.confirmar_limpieza = False
    st.success("Historial borrado exitosamente.")
    time.sleep(1) 
    st.rerun()

# --- Configuración y Diseño de la Interfaz (Streamlit) ---

st.set_page_config(page_title="Control de Asistencia Gym", layout="wide")
st.title("Sistema de Control de Asistencia 🏋️‍♀️")
st.markdown("---")

# ===================================================================
# 1. SECCIÓN DE REGISTRO
# ===================================================================

col_form, col_spacer = st.columns([1, 0.5])

with col_form:
    st.header("1. Marcar Asistencia")
    
    with st.form("form_asistencia"):
        nombre = st.text_input("Nombre:")
        apellido = st.text_input("Apellido:")
        
        submit_button = st.form_submit_button("REGISTRAR ASISTENCIA")

    if submit_button:
        if nombre and apellido:
            marcar_asistencia(nombre.strip(), apellido.strip())
            st.success(f"✅ ¡Asistencia registrada para **{nombre} {apellido}**!")
            # CORRECCIÓN 1: Usamos st.rerun() para actualizar la lista y limpiar los campos
            st.rerun()
        else:
            st.error("Por favor, completá tu nombre y apellido.")

st.markdown("---")

# ===================================================================
# 2. SECCIÓN DE VISUALIZACIÓN, FILTROS Y REPORTES
# ===================================================================

st.header("2. Lista Histórica de Asistencias")

df_asistencias = leer_asistencias()

if df_asistencias.empty:
    st.info("Aún no hay asistencias registradas.")
else:
    # --- FILTROS ---
    st.subheader("Filtros y Búsqueda")
    
    col_search, col_date, col_total = st.columns(3)

    # Filtro por Nombre/Apellido (Búsqueda)
    filtro_texto = col_search.text_input("Buscar por Nombre o Apellido:", key="filtro_nombre")
    
    # Filtro por Fecha (Reporte por Fecha)
    fecha_max = df_asistencias['Fecha'].max().date() if not df_asistencias.empty else datetime.today().date()
    filtro_fecha = col_date.date_input("Filtrar por Fecha Específica:", 
                                       value=None, 
                                       min_value=df_asistencias['Fecha'].min().date() if not df_asistencias.empty else None, 
                                       max_value=fecha_max,
                                       key="filtro_fecha")

    # Aplicar filtros
    df_filtrado = df_asistencias.copy()
    
    if filtro_fecha:
        # dt.date convierte la columna de datetime a date para la comparación
        df_filtrado = df_filtrado[df_filtrado['Fecha'].dt.date == filtro_fecha]

    if filtro_texto:
        df_filtrado = df_filtrado[
            df_filtrado['Nombre'].str.contains(filtro_texto, case=False) |
            df_filtrado['Apellido'].str.contains(filtro_texto, case=False)
        ]
    
    # Mostrar totales
    col_total.metric(label="Total de Asistencias (Filtradas)", value=len(df_filtrado))
    
    # Mostrar la tabla filtrada
    st.markdown("---")
    st.subheader(f"Resultados ({len(df_filtrado)})")
    st.dataframe(df_filtrado, use_container_width=True)

    # --- DESCARGA Y LIMPIEZA ---
    col_download, col_clean = st.columns([1, 1])

    with col_download:
        st.download_button(
            label="Descargar a Excel (Archivo CSV)",
            data=df_filtrado.to_csv(index=False).encode('utf-8'),
            file_name=f'asistencias_gym_reporte_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
    
    with col_clean:
        # CORRECCIÓN 2: Lógica de doble confirmación con st.session_state
        st.markdown("### Administración")
        
        if not st.session_state.confirmar_limpieza:
            if st.button("🔴 LIMPIAR TODO EL HISTORIAL (PELIGRO)", type="secondary", on_click=solicitar_confirmacion):
                pass
        else:
            # Diálogo de confirmación
            st.warning("⚠️ ¿Estás *totalmente* seguro? Esta acción eliminará **TODO** el historial de asistencias y es irreversible.")
            
            col_confirm_si, col_confirm_no = st.columns(2)
            
            with col_confirm_si:
                st.button("SÍ, BORRAR DEFINITIVAMENTE", type="primary", on_click=ejecutar_limpieza)
            with col_confirm_no:
                st.button("NO, CANCELAR", on_click=cancelar_limpieza)