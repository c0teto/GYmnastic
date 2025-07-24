import streamlit as st
import pandas as pd
import base64
import io
from github import Github
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de la página
st.set_page_config(
    page_title="Progreso de Entrenamiento",
    page_icon="🏋️",
    layout="wide"
)

# --- Configuración Segura de GitHub ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB"]["TOKEN"]
    REPO_NAME = st.secrets["GITHUB"]["REPO"]
    CSV_PATH = "workout_data.csv"
except Exception as e:
    st.error("Error de configuración: " + str(e))
    st.stop()

# --- Funciones Seguras para GitHub ---
@st.cache_resource
def get_github_connection():
    try:
        return Github(GITHUB_TOKEN)
    except Exception as e:
        st.error(f"Error de conexión con GitHub: {str(e)}")
        st.stop()

def load_data_from_github():
    try:
        g = get_github_connection()
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(CSV_PATH)
        data = base64.b64decode(contents.content)
        df = pd.read_csv(io.StringIO(data.decode('utf-8')))
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        return df
    except Exception as e:
        st.warning(f"Creando nuevo archivo. Error: {str(e)}")
        return pd.DataFrame(columns=['Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones', 'Notas'])

def save_data_to_github(df):
    try:
        g = get_github_connection()
        repo = g.get_repo(REPO_NAME)
        csv_content = df.to_csv(index=False)
        
        try:
            contents = repo.get_contents(CSV_PATH)
            repo.update_file(
                path=contents.path,
                message=f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                content=csv_content,
                sha=contents.sha
            )
        except:
            repo.create_file(
                path=CSV_PATH,
                message="Initial workout data",
                content=csv_content
            )
        return True
    except Exception as e:
        st.error(f"Error al guardar: {str(e)}")
        return False

# Estilo de los gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 5)

# Cargar datos
df = load_data_from_github()

# Sidebar para nuevo registro
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
                fecha,
                ejercicio,
                peso,
                reps,
                notas
            ]], columns=df.columns)
            
            df = pd.concat([df, nuevo_registro], ignore_index=True)
            if save_data_to_github(df):
                st.success("¡Registro guardado en GitHub!")
                st.rerun()
            else:
                st.error("Error al guardar. Intenta nuevamente.")

# Mostrar datos
st.title("📊 Mi Progreso de Entrenamiento")

if not df.empty:
    # Calcular volumen
    df['Volumen'] = df['Peso (kg)'] * df['Repeticiones']
    
    # Seleccionar ejercicio
    ejercicio_seleccionado = st.selectbox(
        "Selecciona un ejercicio para analizar",
        df['Ejercicio'].unique()
    )
    
    # Filtrar datos
    df_ejercicio = df[df['Ejercicio'] == ejercicio_seleccionado].sort_values('Fecha')
    
    # Métricas clave
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Máximo peso", f"{df_ejercicio['Peso (kg)'].max()} kg")
    with col2:
        st.metric("Máximas reps", df_ejercicio['Repeticiones'].max())
    with col3:
        st.metric("Mejor volumen", f"{df_ejercicio['Volumen'].max()} kg")
    
    # Gráficos
    tab1, tab2, tab3 = st.tabs(["📈 Peso", "🔢 Repeticiones", "💪 Volumen"])
    
    with tab1:
        fig, ax = plt.subplots()
        sns.lineplot(data=df_ejercicio, x='Fecha', y='Peso (kg)', marker='o', ax=ax)
        plt.title(f"Progreso en Peso - {ejercicio_seleccionado}")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    
    with tab2:
        fig, ax = plt.subplots()
        sns.lineplot(data=df_ejercicio, x='Fecha', y='Repeticiones', marker='o', color='orange', ax=ax)
        plt.title(f"Progreso en Repeticiones - {ejercicio_seleccionado}")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    
    with tab3:
        fig, ax = plt.subplots()
        sns.lineplot(data=df_ejercicio, x='Fecha', y='Volumen', marker='o', color='green', ax=ax)
        plt.title(f"Progreso en Volumen - {ejercicio_seleccionado}")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    
    # Resumen general
    st.header("📌 Resumen General")
    df_max_pesos = df.groupby(['Ejercicio', pd.Grouper(key='Fecha', freq='W')])['Peso (kg)'].max().reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(
        data=df_max_pesos, 
        x='Fecha', 
        y='Peso (kg)', 
        hue='Ejercicio',
        marker='o',
        ax=ax
    )
    plt.title("Evolución Semanal de Pesos Máximos")
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    st.pyplot(fig)
    
    # Tabla completa
    st.subheader("📋 Historial Completo")
    st.dataframe(df.sort_values('Fecha', ascending=False), hide_index=True)
    
else:
    st.info("No hay registros aún. ¡Agrega ejercicios desde el panel lateral!")

st.markdown("---")
st.caption("ℹ️ Los datos se guardan directamente en tu repositorio GitHub de forma segura")