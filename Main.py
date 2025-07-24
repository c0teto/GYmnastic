import streamlit as st
import pandas as pd
import base64
import io
from github import Github
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Registro de Gym - GitHub",
    page_icon="🏋️",
    layout="wide"
)

# --- Configuración Segura de GitHub ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB"]["TOKEN"]
    REPO_NAME = st.secrets["GITHUB"]["REPO"]
    CSV_PATH = "workout_data.csv"
except KeyError:
    st.error("Error: Configuración de GitHub no encontrada en secrets")
    st.stop()

# --- Funciones Seguras para GitHub ---
@st.cache_resource
def get_github_connection():
    try:
        return Github(GITHUB_TOKEN)
    except Exception as e:
        st.error(f"Error de conexión con GitHub: {str(e)}")
        st.stop()

def safe_load_data():
    try:
        g = get_github_connection()
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(CSV_PATH)
        data = base64.b64decode(contents.content)
        df = pd.read_csv(io.StringIO(data.decode('utf-8')))
        
        # Columnas obligatorias
        required_columns = ['Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones']
        for col in required_columns:
            if col not in df.columns:
                df[col] = None if col == 'Fecha' else (0 if 'Peso' in col else 1)
        
        return df
    except Exception as e:
        st.warning(f"Creando nuevo archivo. Error al cargar datos: {str(e)}")
        return pd.DataFrame(columns=['Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones', 'Notas'])

def safe_save_data(df):
    try:
        g = get_github_connection()
        repo = g.get_repo(REPO_NAME)
        
        # Convertir DataFrame a CSV
        csv_content = df.to_csv(index=False)
        
        try:
            contents = repo.get_contents(CSV_PATH)
            repo.update_file(
                path=contents.path,
                message=f"Actualización desde Streamlit - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                content=csv_content,
                sha=contents.sha
            )
        except:
            repo.create_file(
                path=CSV_PATH,
                message="Creación inicial desde Streamlit",
                content=csv_content
            )
        return True
    except Exception as e:
        st.error(f"Error al guardar en GitHub: {str(e)}")
        return False

# --- Manejo Seguro de Fechas ---
def safe_date_conversion(df):
    if 'Fecha' not in df.columns:
        df['Fecha'] = datetime.now().strftime('%Y-%m-%d')
    
    try:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Fecha'] = df['Fecha'].fillna(pd.Timestamp('today'))
    except Exception as e:
        st.warning(f"Error al convertir fechas: {str(e)}")
        df['Fecha'] = pd.Timestamp('today')
    
    return df

# --- Interfaz de Usuario ---
st.title("🏋️ Registro de Ejercicios (GitHub Backend)")

# Cargar datos
df = safe_load_data()
df = safe_date_conversion(df)

# Sidebar para nuevos registros
with st.sidebar:
    st.header("➕ Nuevo Registro")
    with st.form("nuevo_ejercicio", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.now())
        ejercicio = st.selectbox(
            "Ejercicio",
            ["Press banca", "Sentadillas", "Peso muerto", "Dominadas", 
             "Press militar", "Curl bíceps", "Tríceps polea", "Otro"]
        )
        if ejercicio == "Otro":
            ejercicio = st.text_input("Especificar ejercicio")
        peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5)
        reps = st.number_input("Repeticiones", min_value=1, step=1, value=8)
        notas = st.text_area("Notas")
        
        if st.form_submit_button("💾 Guardar Ejercicio"):
            nuevo_registro = pd.DataFrame([[
                fecha.strftime('%Y-%m-%d'),
                ejercicio,
                peso,
                reps,
                notas
            ]], columns=df.columns)
            
            df = pd.concat([df, nuevo_registro], ignore_index=True)
            if safe_save_data(df):
                st.success("¡Registro guardado en GitHub!")
                st.rerun()
            else:
                st.error("Error al guardar. Intenta nuevamente.")

# Mostrar datos
st.header("📊 Tus Registros")

if not df.empty:
    try:
        # Ordenamiento seguro
        df_sorted = df.sort_values("Fecha", ascending=False, ignore_index=True)
        st.dataframe(df_sorted, use_container_width=True)
        
        # Gráficos de progreso
        st.header("📈 Progreso")
        ejercicio_seleccionado = st.selectbox(
            "Seleccionar ejercicio para gráfico",
            df["Ejercicio"].unique()
        )
        
        df_filtrado = df[df["Ejercicio"] == ejercicio_seleccionado]
        df_filtrado = df_filtrado.sort_values("Fecha")
        
        if len(df_filtrado) > 1:
            try:
                import matplotlib.pyplot as plt
                
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df_filtrado["Fecha"], df_filtrado["Peso (kg)"], 'o-')
                ax.set_title(f"Progreso en {ejercicio_seleccionado}")
                ax.set_xlabel("Fecha")
                ax.set_ylabel("Peso (kg)")
                plt.xticks(rotation=45)
                st.pyplot(fig)
            except Exception as e:
                st.warning(f"No se pudo generar gráfico: {str(e)}")
        else:
            st.warning("Se necesitan al menos 2 registros para mostrar gráficos")
    except Exception as e:
        st.error(f"Error al procesar datos: {str(e)}")
        st.dataframe(df)  # Fallback seguro
else:
    st.info("No hay registros aún. ¡Empieza a agregar algunos desde el panel lateral!")

# Sección de respaldo/exportación
with st.expander("🔒 Opciones de Respaldo"):
    st.download_button(
        label="📥 Descargar Copia de Seguridad",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"backup_ejercicios_{datetime.now().strftime('%Y%m%d')}.csv",
        mime='text/csv'
    )
    
    if st.button("🔄 Forzar Recarga de Datos"):
        st.cache_resource.clear()
        st.rerun()

st.markdown("---")
st.caption("ℹ️ Los datos se guardan directamente en tu repositorio GitHub de forma segura")