import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
# Nota: Ya no necesitamos os ni el ARCHIVO_CSV

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
# Lee el nombre de la hoja de cálculo y la cuenta de servicio del archivo secrets.toml
# El nombre de la Hoja de Cálculo debe ser un "Secret" o estar aquí si lo prefieres,
# pero lo leeremos directamente de st.secrets para mayor consistencia.
try:
    NOMBRE_HOJA_CALCULO = st.secrets["nombre_hoja_calculo"]
    NOMBRE_HOJA = "Hoja 1" # Ajusta si el nombre de la pestaña es diferente
except KeyError:
    st.error("Error: Falta configurar 'nombre_hoja_calculo' en secrets.toml")
    st.stop()


# Inicialización de Google Sheets (usando caché para no autenticar en cada ejecución)
@st.cache_resource(ttl=None) 
def get_sheets_client():
    """Conecta con Google Sheets usando la cuenta de servicio desde st.secrets."""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Lee las credenciales como un diccionario de Python desde st.secrets
        creds_dict = st.secrets["gcp_service_account"] 
        
        # Autoriza con el diccionario de credenciales
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        # Esto atrapará errores si el JSON es inválido o faltan campos
        st.error(f"❌ Error al conectar con Google Sheets. Verifica tus secretos en secrets.toml y que las APIs estén habilitadas. Error: {e}")
        st.stop() # Detiene la ejecución para evitar errores posteriores
        return None

# --- Funciones de Lógica de Negocio (Ahora para Sheets) ---

def marcar_asistencia(nombre, apellido):
    """Registra la asistencia directamente en Google Sheets."""
    client = get_sheets_client()
    
    try:
        # Abrir la hoja de cálculo y seleccionar la pestaña
        sheet = client.open(NOMBRE_HOJA_CALCULO).worksheet(NOMBRE_HOJA)
        
        # Preparar los datos
        ahora = datetime.now()
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M:%S")
        
        # Escribir la fila
        registro = [fecha, hora, nombre, apellido]
        sheet.append_row(registro)
        
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ Error: Hoja de cálculo '{NOMBRE_HOJA_CALCULO}' no encontrada. Verifica el nombre y la compartición.")
        return False
    except Exception as e:
        st.error(f"❌ Error al escribir en Google Sheets. ¿Está compartida con la cuenta de servicio? Error: {e}")
        return False

# ¡Se mantiene el caché para la lectura! Es esencial para el rendimiento.
# Se le añade un "hash" del cliente para forzar la recarga si las credenciales cambian.
@st.cache_data(show_spinner="Cargando datos de Google Sheets...") 
def leer_asistencias():
    """Lee todos los registros de Google Sheets."""
    client = get_sheets_client()

    try:
        sheet = client.open(NOMBRE_HOJA_CALCULO).worksheet(NOMBRE_HOJA)
        # Obtener todos los valores, incluyendo el encabezado
        data = sheet.get_all_values()
        
        if not data:
             return pd.DataFrame(columns=["Fecha", "Hora", "Nombre", "Apellido"])

        # El primer elemento es el encabezado
        headers = data[0]
        records = data[1:]
        
        # Crear DataFrame
        df = pd.DataFrame(records, columns=headers)
        
        # Asegurarse de que la columna 'Fecha' sea de tipo datetime para el filtro
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce') 
        return df
    except Exception as e:
        st.error(f"❌ Error al leer de Google Sheets. Verifica que el nombre de la hoja sea correcto. Error: {e}")
        return pd.DataFrame(columns=["Fecha", "Hora", "Nombre", "Apellido"])

def limpiar_registros_sheets():
    """Borra todos los registros (dejando solo el encabezado) de Google Sheets."""
    client = get_sheets_client()
    
    try:
        sheet = client.open(NOMBRE_HOJA_CALCULO).worksheet(NOMBRE_HOJA)
        # Borrar todas las filas excepto la primera (encabezado)
        sheet.delete_rows(2, sheet.row_count)
        return True
    except Exception as e:
        st.error(f"❌ Error al limpiar la hoja de cálculo: {e}")
        return False

# --- Funciones de Estado de Limpieza (Mismo uso de Session State) ---

if 'confirmar_limpieza' not in st.session_state:
    st.session_state.confirmar_limpieza = False

def solicitar_confirmacion():
    st.session_state.confirmar_limpieza = True

def cancelar_limpieza():
    st.session_state.confirmar_limpieza = False
    st.rerun()

def ejecutar_limpieza_y_recargar():
    if limpiar_registros_sheets():
        st.session_state.confirmar_limpieza = False
        st.success("Historial borrado exitosamente de Google Sheets.")
        # Limpiar el caché de la función de lectura para que recargue los datos
        st.cache_data.clear() 
        time.sleep(1) # Pequeña pausa para que se vea el mensaje de éxito
        st.rerun()

# --- Configuración y Diseño de la Interfaz (Streamlit) ---

st.set_page_config(page_title="Control de Asistencia Gym - Google Sheets", layout="wide")
st.title("Sistema de Control de Asistencia (Con Google Sheets) 📝")
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
            if marcar_asistencia(nombre.strip(), apellido.strip()):
                st.success(f"✅ ¡Asistencia registrada para **{nombre} {apellido}** en Google Sheets!")
                # Limpiar el caché y forzar la recarga
                st.cache_data.clear() 
                st.rerun()
        else:
            st.error("Por favor, completá tu nombre y apellido.")

st.markdown("---")

# ===================================================================
# 2. SECCIÓN DE VISUALIZACIÓN, FILTROS Y REPORTES
# ===================================================================

st.header("2. Lista Histórica de Asistencias")

df_asistencias = leer_asistencias()

if df_asistencias.empty or len(df_asistencias) == 0:
    st.info("Aún no hay asistencias registradas.")
else:
    # --- FILTROS ---
    st.subheader("Filtros y Búsqueda")
    
    col_search, col_date, col_total = st.columns(3)

    # Filtro por Nombre/Apellido (Búsqueda)
    filtro_texto = col_search.text_input("Buscar por Nombre o Apellido:", key="filtro_nombre")
    
    # Filtro por Fecha (Reporte por Fecha)
    fecha_min = df_asistencias['Fecha'].min().date() if not df_asistencias['Fecha'].isnull().all() else datetime.today().date()
    fecha_max = df_asistencias['Fecha'].max().date() if not df_asistencias['Fecha'].isnull().all() else datetime.today().date()
    
    filtro_fecha = col_date.date_input("Filtrar por Fecha Específica:", 
                                       value=None, 
                                       min_value=fecha_min, 
                                       max_value=fecha_max,
                                       key="filtro_fecha")

    # Aplicar filtros
    df_filtrado = df_asistencias.copy()
    
    if filtro_fecha:
        df_filtrado = df_filtrado[df_filtrado['Fecha'].dt.date == filtro_fecha]

    if filtro_texto:
        df_filtrado = df_filtrado[
            df_filtrado['Nombre'].str.contains(filtro_texto, case=False, na=False) |
            df_filtrado['Apellido'].str.contains(filtro_texto, case=False, na=False)
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
            label="Descargar Reporte (CSV)",
            data=df_filtrado.to_csv(index=False).encode('utf-8'),
            file_name=f'asistencias_gym_reporte_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
    
    with col_clean:
        st.markdown("### Administración")
        
        if not st.session_state.confirmar_limpieza:
            if st.button("🔴 LIMPIAR TODO EL HISTORIAL (PELIGRO)", type="secondary", on_click=solicitar_confirmacion):
                pass
        else:
            # Diálogo de confirmación
            st.warning("⚠️ ¿Estás *totalmente* seguro? Esta acción eliminará **TODO** el historial de asistencias en Google Sheets y es irreversible.")
            
            col_confirm_si, col_confirm_no = st.columns(2)
            
            with col_confirm_si:
                st.button("SÍ, BORRAR DEFINITIVAMENTE", type="primary", on_click=ejecutar_limpieza_y_recargar)
            with col_confirm_no:
                st.button("NO, CANCELAR", on_click=cancelar_limpieza)