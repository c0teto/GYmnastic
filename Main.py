import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from github import Github
import base64
import io
import traceback

# Page configuration
st.set_page_config(
    page_title="Gym Progress Tracker",
    page_icon="🏋️",
    layout="wide"
)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        'Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones', 'RPE', 'Notas'
    ])

# --- GitHub Functions ---
@st.cache_resource
def get_github_connection():
    try:
        return Github(st.secrets["GITHUB"]["TOKEN"])
    except Exception as e:
        st.error(f"GitHub connection error: {str(e)}")
        st.stop()

def load_github_data():
    try:
        g = get_github_connection()
        repo = g.get_repo(st.secrets["GITHUB"]["REPO"])
        contents = repo.get_contents("workout_data.csv")
        data = base64.b64decode(contents.content)
        df = pd.read_csv(io.StringIO(data.decode('utf-8')))
        
        # Ensure required columns exist
        required_cols = ['Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones']
        for col in required_cols:
            if col not in df.columns:
                df[col] = None if col == 'Fecha' else (0 if 'Peso' in col else 1)
        
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        return df
    except Exception as e:
        st.warning(f"Creating new file. Error: {str(e)}")
        return pd.DataFrame(columns=[
            'Fecha', 'Ejercicio', 'Peso (kg)', 'Repeticiones', 'RPE', 'Notas'
        ])

def save_to_github(df):
    try:
        g = get_github_connection()
        repo = g.get_repo(st.secrets["GITHUB"]["REPO"])
        csv_content = df.to_csv(index=False)
        
        try:
            contents = repo.get_contents("workout_data.csv")
            repo.update_file(
                path=contents.path,
                message=f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                content=csv_content,
                sha=contents.sha
            )
        except:
            repo.create_file(
                path="workout_data.csv",
                message="Initial workout data",
                content=csv_content
            )
        return True
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        return False

# --- Data Calculations ---
def calculate_metrics(df):
    if df.empty:
        return df
    
    # Calculate advanced metrics
    df['Volumen'] = df['Peso (kg)'] * df['Repeticiones']
    df['1RM'] = df['Peso (kg)'] * (1 + df['Repeticiones']/30)  # Epley formula
    df['Intensidad'] = df['Peso (kg)'] / df.groupby('Ejercicio')['Peso (kg)'].transform('max')
    df['Progreso'] = df.groupby('Ejercicio')['1RM'].pct_change() * 100
    
    # Ensure proper date format
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    return df

# --- UI Components ---
def show_new_entry_form():
    with st.sidebar:
        st.header("➕ New Workout")
        with st.form("workout_form", clear_on_submit=True):
            fecha = st.date_input("Date", datetime.now())
            ejercicio = st.selectbox(
                "Exercise",
                ["Bench Press", "Squats", "Deadlift", "Pull-ups", 
                 "Overhead Press", "Bicep Curls", "Tricep Pushdown", "Other"]
            )
            if ejercicio == "Other":
                ejercicio = st.text_input("Specify exercise")
            
            col1, col2 = st.columns(2)
            with col1:
                peso = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
            with col2:
                reps = st.number_input("Reps", min_value=1, step=1, value=8)
            
            rpe = st.slider("RPE (1-10)", 1, 10, 7)
            notas = st.text_area("Notes")
            
            if st.form_submit_button("💾 Save Workout"):
                new_entry = {
                    'Fecha': fecha,
                    'Ejercicio': ejercicio,
                    'Peso (kg)': peso,
                    'Repeticiones': reps,
                    'RPE': rpe,
                    'Notas': notas
                }
                return new_entry
    return None

def show_progress_charts(df):
    if df.empty:
        return
    
    st.header("📈 Progress Analysis")
    
    # Exercise selector
    selected_exercise = st.selectbox(
        "Select Exercise", 
        df['Ejercicio'].unique(),
        key="exercise_selector"
    )
    
    # Filter data
    exercise_data = df[df['Ejercicio'] == selected_exercise].sort_values('Fecha')
    
    if len(exercise_data) > 1:
        # Metrics summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Weight", f"{exercise_data['Peso (kg)'].max():.1f} kg")
        with col2:
            st.metric("Max Reps", exercise_data['Repeticiones'].max())
        with col3:
            st.metric("Estimated 1RM", f"{exercise_data['1RM'].max():.1f} kg")
        
        # Progress charts
        tab1, tab2, tab3 = st.tabs(["Weight", "Reps", "Volume"])
        
        with tab1:
            fig = px.line(
                exercise_data, 
                x='Fecha', 
                y='Peso (kg)',
                title=f"Weight Progress - {selected_exercise}",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            fig = px.line(
                exercise_data, 
                x='Fecha', 
                y='Repeticiones',
                title=f"Reps Progress - {selected_exercise}",
                markers=True,
                color_discrete_sequence=['orange']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            fig = px.line(
                exercise_data, 
                x='Fecha', 
                y='Volumen',
                title=f"Volume Progress - {selected_exercise}",
                markers=True,
                color_discrete_sequence=['green']
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Need at least 2 entries for {selected_exercise} to show progress")

# --- Main App Logic ---
def main():
    st.title("🏋️ Gym Progress Tracker")
    
    # Load data
    try:
        if st.session_state.df.empty:
            st.session_state.df = load_github_data()
            st.session_state.df = calculate_metrics(st.session_state.df)
    except Exception as e:
        st.error(f"Initial load error: {str(e)}")
        st.stop()
    
    # New entry form
    new_entry = show_new_entry_form()
    if new_entry:
        try:
            new_df = pd.DataFrame([new_entry])
            st.session_state.df = pd.concat([
                st.session_state.df, 
                new_df
            ], ignore_index=True)
            
            st.session_state.df = calculate_metrics(st.session_state.df)
            
            if save_to_github(st.session_state.df):
                st.success("Workout saved successfully!")
            else:
                st.error("Saved locally but failed to update GitHub")
            
            st.rerun()
        except Exception as e:
            st.error(f"Save error: {str(e)}")
            st.error(traceback.format_exc())
    
    # Display data
    if not st.session_state.df.empty:
        show_progress_charts(st.session_state.df)
        
        with st.expander("📋 Full Workout History"):
            st.dataframe(
                st.session_state.df.sort_values('Fecha', ascending=False),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No workouts recorded yet. Add your first workout using the sidebar!")

if __name__ == "__main__":
    main()