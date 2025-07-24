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

# --- Configuración de GitHub ---
# (Los secrets se configuran en Streamlit Cloud)
GITHUB_TOKEN = st.secrets["GITHUB"]["TOKEN"]
REPO_NAME = st.secrets["GITHUB"]["REPO"]
CSV_PATH = "workout_data.csv"  # Ruta en tu repositorio

# --- Funciones para manejar GitHub ---
@st.cache_resource
def get_github_connection():
    return Github(GITHUB_TOKEN)

def load_data_from_github():
    try:
        g = get_github_connection()
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(CSV_PATH)
        data = base64.b64decode(contents.content)
        return pd.read_csv(io.StringIO(data.decode('utf-8')))
    except:
        # Si el archivo no existe, crea uno vacío
        return pd.DataFrame(columns=[
            'Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones', 'Notas'
        ])

def save_data_to_github(df):
    g = get_github_connection()
    repo = g.get_repo(REPO_NAME)
    
    try:
        contents = repo.get_contents(CSV_PATH)
        repo.update_file(
            path=contents.path,
            message=f"Actualización desde Streamlit - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            content=df.to_csv(index=False),
            sha=contents.sha
        )
    except:
        # Si el archivo no existe, lo crea
        repo.create_file(
            path=CSV_PATH,
            message="Creación inicial desde Streamlit",
            content=df.to_csv(index=False)
        )

# --- Interfaz de la aplicación ---
st.title("🏋️ Registro de Ejercicios (GitHub Backend)")

# Cargar datos
df = load_data_from_github()

# Sidebar para nuevos registros
with st.sidebar:
    st.header("➕ Nuevo Registro")
    with st.form("nuevo_ejercicio"):
        fecha = st.date_input("Fecha", datetime.now())
        ejercicio = st.selectbox(
            "Ejercicio",
            ["Press banca", "Sentadillas", "Peso muerto", "Dominadas", 
             "Press militar", "Curl bíceps", "Tríceps polea", "Otro"]
        )
        if ejercicio == "Otro":
            ejercicio = st.text_input("Especificar ejercicio")
        peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5)
        reps = st.number_input("Repeticiones", min_value=1, step=1)
        notas = st.text_area("Notas")
        
        if st.form_submit_button("Guardar"):
            nuevo_registro = pd.DataFrame([[
                fecha,
                ejercicio,
                peso,
                reps,
                notas
            ]], columns=df.columns)
            
            df = pd.concat([df, nuevo_registro], ignore_index=True)
            save_data_to_github(df)
            st.success("¡Registro guardado en GitHub!")

# Mostrar datos
st.header("📊 Tus Registros")
st.dataframe(df.sort_values("Fecha", ascending=False))

# Gráficos de progreso (requiere matplotlib)
if not df.empty:
    st.header("📈 Progreso")
    ejercicio_seleccionado = st.selectbox(
        "Seleccionar ejercicio para gráfico",
        df["Ejercicio"].unique()
    )
    
    df_filtrado = df[df["Ejercicio"] == ejercicio_seleccionado].sort_values("Fecha")
    
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
        except:
            st.warning("No se pudo cargar matplotlib para gráficos")
    else:
        st.warning("Se necesitan al menos 2 registros para mostrar gráficos")
else:
    st.info("No hay registros aún. ¡Empieza a agregar algunos desde el panel lateral!")