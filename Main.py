import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from github import Github
import base64
import io

# Configuración de la página
st.set_page_config(
    page_title="Analizador de Progreso de Fuerza",
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

# --- Funciones para GitHub ---
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
        return pd.DataFrame(columns=['Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones', 'RPE', 'Notas'])

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

# --- Métricas Avanzadas ---
def calcular_metricas(df):
    if df.empty:
        return df
    
    df['Volumen'] = df['Peso (kg)'] * df['Repeticiones']
    df['1RM'] = df['Peso (kg)'] * (1 + df['Repeticiones']/30)  # Fórmula de Epley
    df['Intensidad'] = df['Peso (kg)'] / df.groupby('Ejercicio')['Peso (kg)'].transform('max')
    df['Progreso'] = df.groupby('Ejercicio')['1RM'].pct_change() * 100
    return df

# --- Análisis de Progreso ---
def generar_analisis(df):
    if len(df) < 2:
        return ["⚠️ Necesitas al menos 2 registros por ejercicio para análisis"]
    
    resultados = []
    for ejercicio in df['Ejercicio'].unique():
        sub_df = df[df['Ejercicio'] == ejercicio].sort_values('Fecha')
        if len(sub_df) > 1:
            ultimo = sub_df.iloc[-1]
            mejor = sub_df.loc[sub_df['1RM'].idxmax()]
            
            if ultimo['1RM'] >= mejor['1RM']:
                resultados.append(f"🏆 {ejercicio}: Nuevo récord! (1RM: {ultimo['1RM']:.1f}kg)")
            elif ultimo['Repeticiones'] > sub_df.iloc[-2]['Repeticiones']:
                resultados.append(f"📈 {ejercicio}: +{ultimo['Repeticiones']-sub_df.iloc[-2]['Repeticiones']} repeticiones")
            elif ultimo['Peso (kg)'] > sub_df.iloc[-2]['Peso (kg)']:
                resultados.append(f"💪 {ejercicio}: +{ultimo['Peso (kg)']-sub_df.iloc[-2]['Peso (kg)']:.1f}kg")
            else:
                resultados.append(f"🔄 {ejercicio}: Mantenimiento")
    
    return resultados

# --- Interfaz de Usuario ---
st.title("💪 Analizador de Progreso de Fuerza")

# Cargar y procesar datos
df = load_data_from_github()
df = calcular_metricas(df)

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
        col1, col2 = st.columns(2)
        with col1:
            peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5)
        with col2:
            reps = st.number_input("Repeticiones", min_value=1, step=1, value=8)
        rpe = st.slider("Esfuerzo percibido (RPE)", 1, 10, 7)
        notas = st.text_area("Notas")
        
        if st.form_submit_button("💾 Guardar Entrenamiento"):
            nuevo_registro = pd.DataFrame([[
                fecha,
                ejercicio,
                peso,
                reps,
                rpe,
                notas
            ]], columns=df.columns)
            
            df = pd.concat([df, nuevo_registro], ignore_index=True)
            if save_data_to_github(df):
                st.success("¡Datos guardados!")
                st.rerun()
            else:
                st.error("Error al guardar. Intenta nuevamente.")

# Pestañas principales
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Progreso", "🔍 Análisis"])

with tab1:
    if not df.empty:
        st.header("📌 Resumen General")
        
        # Métricas clave
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sesiones registradas", len(df))
        with col2:
            st.metric("Ejercicios diferentes", df['Ejercicio'].nunique())
        with col3:
            st.metric("Mejor 1RM", f"{df['1RM'].max():.1f}kg")
        with col4:
            st.metric("Mayor volumen", f"{df['Volumen'].max():.1f}kg")
        
        # Análisis automático
        st.header("📌 Tu Progreso")
        for analisis in generar_analisis(df):
            st.write(analisis)
        
        # Evolución reciente
        st.header("📅 Evolución Reciente (últimas 4 semanas)")
        df_reciente = df[df['Fecha'] > (datetime.now() - pd.Timedelta(weeks=4))]
        
        if not df_reciente.empty:
            fig = px.line(df_reciente.groupby(['Ejercicio', pd.Grouper(key='Fecha', freq='W')])['1RM'].max().reset_index(), 
                         x='Fecha', y='1RM', color='Ejercicio', markers=True,
                         title="1RM Semanal por Ejercicio")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos recientes para mostrar")

with tab2:
    if not df.empty:
        st.header("📈 Evolución de Fuerza")
        
        # Selector de ejercicio
        ejercicio = st.selectbox("Seleccionar ejercicio", df['Ejercicio'].unique(), key='ejercicio_progreso')
        df_ejercicio = df[df['Ejercicio'] == ejercicio].sort_values('Fecha')
        
        if len(df_ejercicio) > 1:
            # Gráfico combinado
            fig = px.line(df_ejercicio, x='Fecha', y=['Peso (kg)', 'Repeticiones', '1RM', 'Volumen'],
                         title=f"Progreso en {ejercicio}",
                         labels={'value': 'Valor', 'variable': 'Métrica'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de relación peso-reps
            st.header("🔍 Relación Peso-Repeticiones")
            fig = px.scatter(df_ejercicio, x='Peso (kg)', y='Repeticiones', 
                            trendline="lowess", color='Fecha',
                            hover_data=['RPE', 'Notas'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Necesitas al menos 2 registros de {ejercicio} para ver el progreso")

with tab3:
    if not df.empty:
        st.header("🔍 Análisis Detallado")
        
        # Heatmap de progreso
        st.subheader("🔥 Heatmap de Progreso")
        df_heatmap = df.groupby(['Ejercicio', pd.Grouper(key='Fecha', freq='W')])['1RM'].max().unstack()
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(df_heatmap.T, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax)
        plt.title("1RM Máximo Semanal por Ejercicio (kg)")
        st.pyplot(fig)
        
        # Comparativa entre ejercicios
        st.subheader("🔄 Comparativa entre Ejercicios")
        fig = px.box(df, x='Ejercicio', y='1RM', 
                    title="Distribución de 1RM por Ejercicio")
        st.plotly_chart(fig, use_container_width=True)
        
        # Análisis de volumen
        st.subheader("📦 Análisis de Volumen")
        fig = px.bar(df.groupby('Ejercicio')['Volumen'].sum().reset_index(), 
                    x='Ejercicio', y='Volumen',
                    title="Volumen Total Acumulado por Ejercicio")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No hay registros aún. ¡Agrega tu primer entrenamiento desde el panel lateral!")

        # Footer
        st.markdown("---")
        st.caption("💡 Consejo: Intenta aumentar el peso o las repeticiones cada 2-3 semanas para progresar consistentemente")