import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import math
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="📊 Calculadora de Intervalos de Confianza",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def safe_numeric(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except:
        return default

def crear_comparacion(resultados, parametro, etiqueta_x, titulo=None):
    """Crea gráfico de comparación de intervalos"""
    resultados = resultados.sort_values('Conf')

    fig = go.Figure()

    for i, row in resultados.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['LI'], row['LS']],
            y=[row['Nivel'], row['Nivel']],
            mode='lines+markers',
            name=row['Nivel'],
            line=dict(color=row['Color'], width=6),
            marker=dict(size=10)
        ))

    # Línea del parámetro
    fig.add_vline(x=parametro, line_dash="dash", line_color="#2c3e50")

    fig.update_layout(
        title=titulo if titulo else "Comparación de Intervalos según Nivel de Confianza",
        xaxis_title=etiqueta_x,
        yaxis_title="Nivel de Confianza",
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def format_interval(li, ls, decimals=4):
    """Formatea un intervalo de confianza"""
    return f"({li:.{decimals}f}, {ls:.{decimals}f})"

# ============================================================
# FUNCIÓN PARA SELECCIONAR NIVEL DE CONFIANZA PERSONALIZADO
# ============================================================

def selector_nivel_confianza(key_suffix=""):
    """Crea un selector de nivel de confianza con opciones predefinidas y personalizadas"""
    
    st.subheader("🎯 Nivel de Confianza")
    
    # Opciones predefinidas + personalizado
    conf_opciones = ["80%", "85%", "90%", "95%", "96%", "98%", "99%", "99.5%", "Personalizado"]
    
    conf_seleccionado = st.selectbox(
        "Selecciona el nivel de confianza:",
        options=conf_opciones,
        index=3,  # 95% por defecto
        key=f"conf_select_{key_suffix}"
    )
    
    if conf_seleccionado == "Personalizado":
        # Slider con valores entre 0.50 y 0.999 (50% a 99.9%)
        conf_val = st.slider(
            "Nivel de confianza personalizado:",
            min_value=0.500,
            max_value=0.999,
            value=0.950,
            step=0.001,
            format="%.1f%%",
            key=f"conf_slider_{key_suffix}"
        )
        # Mostrar el valor exacto
        st.caption(f"Valor exacto: {conf_val*100:.1f}%")
        return conf_val
    else:
        # Eliminar el % y convertir a float
        return float(conf_seleccionado.replace("%", "")) / 100

# ============================================================
# FUNCIÓN PARA INPUT DE NÚMEROS CON ALTA PRECISIÓN
# ============================================================

def number_input_high_precision(label, min_value=None, max_value=None, value=0.0, step=0.0001, format="%.6f", key=None):
    """Input numérico con alta precisión para valores pequeños"""
    
    # Si no hay límite mínimo, permitir 0
    if min_value is None:
        min_value = 0.0
    
    # Si el valor es demasiado pequeño, redondear
    if value is not None and value < 1e-10 and value > 0:
        value = 0.0
    
    return st.number_input(
        label,
        min_value=min_value,
        max_value=max_value,
        value=value,
        step=step,
        format=format,
        key=key
    )

# ============================================================
# FUNCIÓN PARA VALIDAR VARIANZA PEQUEÑA
# ============================================================

def calcular_ic_varianza(n, s2, conf_val, tipo_intervalo):
    """Calcula el IC para varianza con manejo de valores muy pequeños"""
    
    alpha = 1 - conf_val
    df = n - 1
    
    # Verificar que la varianza no sea demasiado pequeña
    if s2 < 1e-10:
        st.warning("⚠️ La varianza es extremadamente pequeña. Los resultados pueden ser poco precisos.")
    
    try:
        if tipo_intervalo == "Dos colas (σ² ≠ σ²₀)":
            chi2_inf = stats.chi2.ppf(alpha/2, df)
            chi2_sup = stats.chi2.ppf(1 - alpha/2, df)
            
            # Manejar valores extremadamente pequeños
            if chi2_inf < 1e-10:
                li = 0
            else:
                li = df * s2 / chi2_sup if chi2_sup > 0 else 0
            ls = df * s2 / chi2_inf if chi2_inf > 0 else float('inf')
            
        elif tipo_intervalo == "Cola superior (σ² > σ²₀)":
            chi2_inf = stats.chi2.ppf(1 - alpha, df)
            li = df * s2 / chi2_inf if chi2_inf > 0 else 0
            ls = float('inf')
            
        else:  # Cola inferior
            chi2_sup = stats.chi2.ppf(1 - alpha, df)
            li = 0
            ls = df * s2 / chi2_sup if chi2_sup > 0 else 0
        
        return {
            'li': li,
            'ls': ls,
            'df': df,
            'chi2_inf': chi2_inf if 'chi2_inf' in locals() and chi2_inf != float('inf') else None,
            'chi2_sup': chi2_sup if 'chi2_sup' in locals() and chi2_sup != float('inf') else None
        }
        
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {e}")
        return None

# ============================================================
# INTERFAZ DE USUARIO
# ============================================================

st.title("📊 Calculadora de Intervalos de Confianza")
st.markdown("---")

# Crear todas las pestañas
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Media Poblacional",
    "📐 Varianza Poblacional",
    "🎯 Proporción Poblacional",
    "📊 Diferencia de Medias",
    "📐 Cociente de Varianzas",
    "🎯 Diferencia de Proporciones"
])

# ============================================================
# PESTAÑA 1: MEDIA POBLACIONAL
# ============================================================

with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📊 Datos de la Muestra")
        n = st.number_input("Tamaño de muestra (n):", min_value=2, value=30, step=1)
        xbar = st.number_input("Media muestral (x̄):", value=100.0, step=0.1)

        st.subheader("🔧 Configuración")
        tipo_media = st.radio(
            "¿Conoces la desviación estándar poblacional?",
            ["Sí, conozco σ", "No, uso s (muestral)"],
            key="tipo_media"
        )

        if tipo_media == "Sí, conozco σ":
            # PERMITIR VALORES MUY PEQUEÑOS
            sigma = st.number_input(
                "σ (desviación poblacional):", 
                min_value=0.0, 
                value=15.0, 
                step=0.001,
                format="%.6f"
            )
            if sigma == 0:
                st.warning("⚠️ σ = 0 hará que el error estándar sea cero")
        else:
            s = st.number_input(
                "s (desviación muestral):", 
                min_value=0.0, 
                value=12.0, 
                step=0.001,
                format="%.6f"
            )
            if s == 0:
                st.warning("⚠️ s = 0 hará que el error estándar sea cero")

        # NIVEL DE CONFIANZA PERSONALIZADO
        conf_val = selector_nivel_confianza("media")

        st.subheader("📌 Tipo de Intervalo")
        tipo_intervalo = st.radio(
            "Selecciona el tipo:",
            ["Dos colas (μ ≠ μ₀)", "Cola superior (μ > μ₀)", "Cola inferior (μ < μ₀)"],
            key="tipo_intervalo_media"
        )

        if st.button("🔍 Calcular", key="calcular_media"):
            alpha = 1 - conf_val

            if tipo_media == "Sí, conozco σ":
                if tipo_intervalo == "Dos colas (μ ≠ μ₀)":
                    z = stats.norm.ppf(1 - alpha/2)
                    error = z * sigma / np.sqrt(n) if sigma > 0 else 0
                    li = xbar - error
                    ls = xbar + error
                    metodo = "Normal (σ conocida) - Dos colas"
                    valor_critico = z
                    valor_critico_nombre = "Z"
                elif tipo_intervalo == "Cola superior (μ > μ₀)":
                    z = stats.norm.ppf(1 - alpha)
                    error = z * sigma / np.sqrt(n) if sigma > 0 else 0
                    li = xbar - error
                    ls = float('inf')
                    metodo = "Normal (σ conocida) - Cola superior"
                    valor_critico = z
                    valor_critico_nombre = "Z"
                else:  # Cola inferior
                    z = stats.norm.ppf(1 - alpha)
                    error = z * sigma / np.sqrt(n) if sigma > 0 else 0
                    li = -float('inf')
                    ls = xbar + error
                    metodo = "Normal (σ conocida) - Cola inferior"
                    valor_critico = z
                    valor_critico_nombre = "Z"
                df = None
                gl_metodo = "Z - Normal Estándar"
            else:
                df = n - 1
                if tipo_intervalo == "Dos colas (μ ≠ μ₀)":
                    t = stats.t.ppf(1 - alpha/2, df)
                    error = t * s / np.sqrt(n) if s > 0 else 0
                    li = xbar - error
                    ls = xbar + error
                    metodo = "t-Student (σ desconocida) - Dos colas"
                    valor_critico = t
                    valor_critico_nombre = "t"
                elif tipo_intervalo == "Cola superior (μ > μ₀)":
                    t = stats.t.ppf(1 - alpha, df)
                    error = t * s / np.sqrt(n) if s > 0 else 0
                    li = xbar - error
                    ls = float('inf')
                    metodo = "t-Student (σ desconocida) - Cola superior"
                    valor_critico = t
                    valor_critico_nombre = "t"
                else:  # Cola inferior
                    t = stats.t.ppf(1 - alpha, df)
                    error = t * s / np.sqrt(n) if s > 0 else 0
                    li = -float('inf')
                    ls = xbar + error
                    metodo = "t-Student (σ desconocida) - Cola inferior"
                    valor_critico = t
                    valor_critico_nombre = "t"
                gl_metodo = f"t-Student con ν = {df}"

            st.session_state['media'] = {
                'li': li, 'ls': ls, 'error': error if error != float('inf') else None,
                'xbar': xbar, 'n': n, 'conf': conf_val,
                'metodo': metodo, 'valor_critico': valor_critico,
                'valor_critico_nombre': valor_critico_nombre,
                'gl_metodo': gl_metodo, 'df': df,
                'tipo_intervalo': tipo_intervalo
            }

            if tipo_intervalo == "Dos colas (μ ≠ μ₀)":
                st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.6f}, {ls:.6f})")
            elif tipo_intervalo == "Cola superior (μ > μ₀)":
                st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.6f}, ∞)")
            else:
                st.success(f"✅ IC al {conf_val*100:.1f}%: (-∞, {ls:.6f})")

    with col2:
        if 'media' in st.session_state:
            res = st.session_state['media']

            st.subheader("📊 Resultado")
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.metric("Media muestral", f"{res['xbar']:.6f}")
            with col_res2:
                if res['li'] == -float('inf'):
                    st.metric("Límite Inferior", "-∞")
                else:
                    st.metric("Límite Inferior", f"{res['li']:.6f}")
            with col_res3:
                if res['ls'] == float('inf'):
                    st.metric("Límite Superior", "∞")
                else:
                    st.metric("Límite Superior", f"{res['ls']:.6f}")

            st.info(f"📌 {res['metodo']} | {res['valor_critico_nombre']} = {res['valor_critico']:.4f}")
            if res['df']:
                st.info(f"📌 Grados de libertad: ν = {res['df']}")

            # Gráfico
            if res['tipo_intervalo'] == "Dos colas (μ ≠ μ₀)":
                x_min = res['li'] - 2*res['error'] if res['error'] else res['xbar'] - 30
                x_max = res['ls'] + 2*res['error'] if res['error'] else res['xbar'] + 30
                x_vals = np.linspace(x_min, x_max, 1000)
            else:
                # Para colas, mostrar un rango razonable
                rango = 4 * (res['error'] if res['error'] else 10)
                x_min = res['xbar'] - rango
                x_max = res['xbar'] + rango
                x_vals = np.linspace(x_min, x_max, 1000)

            if tipo_media == "Sí, conozco σ":
                se = res['error'] / stats.norm.ppf(1 - (1-res['conf'])/2) if res['error'] else 5
                y_vals = stats.norm.pdf(x_vals, res['xbar'], se)
                titulo = "Distribución Normal"
            else:
                se = res['error'] / stats.t.ppf(1 - (1-res['conf'])/2, res['df']) if res['error'] else 5
                y_vals = stats.t.pdf((x_vals - res['xbar']) / se, res['df']) / se
                titulo = "Distribución t-Student"

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                name='Densidad',
                line=dict(color='#3498db', width=2)
            ))

            # Área sombreada según tipo
            if res['tipo_intervalo'] == "Dos colas (μ ≠ μ₀)":
                mask = (x_vals >= res['li']) & (x_vals <= res['ls'])
                nombre_area = f'IC {res["conf"]*100:.1f}%'
            elif res['tipo_intervalo'] == "Cola superior (μ > μ₀)":
                mask = x_vals >= res['li']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola superior)'
            else:  # Cola inferior
                mask = x_vals <= res['ls']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola inferior)'

            if np.any(mask):
                fig.add_trace(go.Scatter(
                    x=x_vals[mask],
                    y=y_vals[mask],
                    fill='tozeroy',
                    name=nombre_area,
                    line=dict(color='#e74c3c'),
                    fillcolor='rgba(231, 76, 60, 0.4)'
                ))

            fig.add_vline(x=res['xbar'], line_dash="dash", line_color="#2c3e50")

            fig.update_layout(
                title=f"{titulo} - {res['tipo_intervalo']}",
                xaxis_title="Media muestral",
                yaxis_title="Densidad",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # Comparación de niveles
            st.subheader("📊 Comparación de Niveles de Confianza")

            # Generar niveles desde 70% hasta 99% con pasos de 1%
            niveles = np.arange(0.70, 0.99, 0.01)
            # Añadir 99.5% y 99.9% si están dentro del rango
            for extra in [0.995, 0.999]:
                if extra <= 0.999:
                    niveles = np.append(niveles, extra)
            niveles = sorted(niveles)
            
            resultados = []
            colores_paleta = px.colors.qualitative.Plotly + px.colors.qualitative.Set1 + px.colors.qualitative.Set2

            for i, conf_comp in enumerate(niveles):
                alpha = 1 - conf_comp
                if tipo_media == "Sí, conozco σ":
                    if res['tipo_intervalo'] == "Dos colas (μ ≠ μ₀)":
                        z = stats.norm.ppf(1 - alpha/2)
                    else:
                        z = stats.norm.ppf(1 - alpha)
                    error = z * sigma / np.sqrt(n) if sigma > 0 else 0
                else:
                    df = n - 1
                    if res['tipo_intervalo'] == "Dos colas (μ ≠ μ₀)":
                        t = stats.t.ppf(1 - alpha/2, df)
                    else:
                        t = stats.t.ppf(1 - alpha, df)
                    error = t * s / np.sqrt(n) if s > 0 else 0

                if res['tipo_intervalo'] == "Dos colas (μ ≠ μ₀)":
                    resultados.append({
                        'Nivel': f"{conf_comp*100:.1f}%",
                        'LI': xbar - error,
                        'LS': xbar + error,
                        'Conf': conf_comp,
                        'Color': colores_paleta[i % len(colores_paleta)]
                    })
                elif res['tipo_intervalo'] == "Cola superior (μ > μ₀)":
                    resultados.append({
                        'Nivel': f"{conf_comp*100:.1f}%",
                        'LI': xbar - error,
                        'LS': xbar + error*2,
                        'Conf': conf_comp,
                        'Color': colores_paleta[i % len(colores_paleta)]
                    })
                else:  # Cola inferior
                    resultados.append({
                        'Nivel': f"{conf_comp*100:.1f}%",
                        'LI': xbar - error*2,
                        'LS': xbar + error,
                        'Conf': conf_comp,
                        'Color': colores_paleta[i % len(colores_paleta)]
                    })

            df_res = pd.DataFrame(resultados)
            fig_comp = crear_comparacion(df_res, xbar, "Intervalo para μ")
            st.plotly_chart(fig_comp, use_container_width=True)

# ============================================================
# PESTAÑA 2: VARIANZA POBLACIONAL (CORREGIDA)
# ============================================================

with tab2:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📊 Datos de la Muestra")
        n = st.number_input("Tamaño de muestra (n):", min_value=2, value=20, step=1)
        
        # PERMITIR VALORES MUY PEQUEÑOS PARA LA VARIANZA
        s2 = st.number_input(
            "Varianza muestral (s²):", 
            min_value=0.0, 
            value=25.0, 
            step=0.0001,
            format="%.6f"
        )

        # Advertencia para valores muy pequeños
        if s2 < 0.001 and s2 > 0:
            st.info(f"ℹ️ Varianza ingresada: {s2:.6f}")

        # NIVEL DE CONFIANZA PERSONALIZADO
        conf_val = selector_nivel_confianza("varianza")

        st.subheader("📌 Tipo de Intervalo")
        tipo_intervalo = st.radio(
            "Selecciona el tipo:",
            ["Dos colas (σ² ≠ σ²₀)", "Cola superior (σ² > σ²₀)", "Cola inferior (σ² < σ²₀)"],
            key="tipo_intervalo_var"
        )

        if st.button("🔍 Calcular", key="calcular_var"):
            alpha = 1 - conf_val
            df = n - 1
            
            # Si la varianza es 0, mostrar mensaje especial
            if s2 == 0:
                st.warning("⚠️ La varianza es 0. El intervalo será [0, 0]")
                st.session_state['var'] = {
                    'li': 0, 'ls': 0,
                    'li_sd': 0, 'ls_sd': 0,
                    'df': df, 's2': 0,
                    'conf': conf_val, 'n': n,
                    'tipo_intervalo': tipo_intervalo,
                    'chi2_inf': None, 'chi2_sup': None
                }
                st.success(f"✅ IC al {conf_val*100:.1f}% para σ²: (0, 0)")
            else:
                # Usar la función mejorada
                resultado = calcular_ic_varianza(n, s2, conf_val, tipo_intervalo)
                
                if resultado:
                    li = resultado['li']
                    ls = resultado['ls']
                    
                    st.session_state['var'] = {
                        'li': li, 'ls': ls,
                        'li_sd': np.sqrt(li) if li != float('inf') and li > 0 else 0,
                        'ls_sd': np.sqrt(ls) if ls != float('inf') and ls > 0 else 0,
                        'df': df, 's2': s2,
                        'conf': conf_val, 'n': n,
                        'tipo_intervalo': tipo_intervalo,
                        'chi2_inf': resultado['chi2_inf'],
                        'chi2_sup': resultado['chi2_sup']
                    }

                    if tipo_intervalo == "Dos colas (σ² ≠ σ²₀)":
                        if li == 0:
                            st.success(f"✅ IC al {conf_val*100:.1f}% para σ²: (0, {ls:.6f})")
                        else:
                            st.success(f"✅ IC al {conf_val*100:.1f}% para σ²: ({li:.6f}, {ls:.6f})")
                    elif tipo_intervalo == "Cola superior (σ² > σ²₀)":
                        st.success(f"✅ IC al {conf_val*100:.1f}% para σ²: ({li:.6f}, ∞)")
                    else:
                        st.success(f"✅ IC al {conf_val*100:.1f}% para σ²: (0, {ls:.6f})")
                else:
                    st.error("❌ Error en el cálculo. Verifica los valores ingresados.")

    with col2:
        if 'var' in st.session_state:
            res = st.session_state['var']

            st.subheader("📊 Resultado")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                if res['li'] == 0:
                    st.metric("LI σ²", "0")
                elif res['li'] == float('inf'):
                    st.metric("LI σ²", "∞")
                else:
                    st.metric("LI σ²", f"{res['li']:.6f}")
                st.metric("LI σ", f"{res['li_sd']:.6f}" if res['li_sd'] > 0 else "0")
            with col_res2:
                if res['ls'] == float('inf'):
                    st.metric("LS σ²", "∞")
                else:
                    st.metric("LS σ²", f"{res['ls']:.6f}")
                st.metric("LS σ", f"{res['ls_sd']:.6f}" if res['ls_sd'] > 0 else "0")

            st.info(f"📌 Grados de libertad: ν = {res['df']}")
            if res['chi2_inf'] is not None and res['chi2_inf'] > 0:
                st.info(f"📌 χ² inferior: {res['chi2_inf']:.4f}")
            if res['chi2_sup'] is not None and res['chi2_sup'] > 0:
                st.info(f"📌 χ² superior: {res['chi2_sup']:.4f}")

            # Gráfico
            try:
                # Calcular el rango adecuado para el gráfico
                if res['ls'] != float('inf') and res['ls'] > 0:
                    x_max = min(max(res['ls'] * 2, 10), 1000)
                else:
                    x_max = max(10, res['s2'] * 4 if res['s2'] > 0 else 10)
                
                x_vals = np.linspace(0.001, x_max, 1000)
                y_vals = stats.chi2.pdf(x_vals, res['df'])
                
                # Escalar para la varianza
                if res['s2'] > 0:
                    x_scaled = x_vals * res['s2'] / res['df']
                    y_scaled = y_vals * res['df'] / res['s2']
                else:
                    x_scaled = x_vals
                    y_scaled = y_vals

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=x_scaled,
                    y=y_scaled,
                    mode='lines',
                    name='Densidad',
                    line=dict(color='#3498db', width=2)
                ))

                if res['tipo_intervalo'] == "Dos colas (σ² ≠ σ²₀)":
                    mask = (x_scaled >= res['li']) & (x_scaled <= res['ls'])
                    nombre_area = f'IC {res["conf"]*100:.1f}%'
                elif res['tipo_intervalo'] == "Cola superior (σ² > σ²₀)":
                    mask = x_scaled >= res['li']
                    nombre_area = f'IC {res["conf"]*100:.1f}% (cola superior)'
                else:  # Cola inferior
                    mask = x_scaled <= res['ls']
                    nombre_area = f'IC {res["conf"]*100:.1f}% (cola inferior)'

                if np.any(mask):
                    fig.add_trace(go.Scatter(
                        x=x_scaled[mask],
                        y=y_scaled[mask],
                        fill='tozeroy',
                        name=nombre_area,
                        line=dict(color='#e74c3c'),
                        fillcolor='rgba(231, 76, 60, 0.4)'
                    ))

                fig.update_layout(
                    title=f"Distribución Chi-Cuadrado - {res['tipo_intervalo']}",
                    xaxis_title="Varianza",
                    yaxis_title="Densidad",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.warning(f"⚠️ No se pudo generar el gráfico: {e}")

# ============================================================
# PESTAÑA 3: PROPORCIÓN POBLACIONAL
# ============================================================

with tab3:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📊 Datos de la Muestra")
        n = st.number_input("Tamaño de muestra (n):", min_value=1, value=100, step=1)
        x = st.number_input("Número de éxitos (x):", min_value=0, value=45, step=1)

        # NIVEL DE CONFIANZA PERSONALIZADO
        conf_val = selector_nivel_confianza("proporcion")

        st.subheader("📌 Tipo de Intervalo")
        tipo_intervalo = st.radio(
            "Selecciona el tipo:",
            ["Dos colas (p ≠ p₀)", "Cola superior (p > p₀)", "Cola inferior (p < p₀)"],
            key="tipo_intervalo_prop"
        )

        if st.button("🔍 Calcular", key="calcular_prop"):
            if x > n:
                st.error("❌ Error: x no puede ser mayor que n")
            else:
                alpha = 1 - conf_val
                p_hat = x / n

                if tipo_intervalo == "Dos colas (p ≠ p₀)":
                    z = stats.norm.ppf(1 - alpha/2)
                    error = z * np.sqrt(p_hat * (1 - p_hat) / n)
                    li = max(0, p_hat - error)
                    ls = min(1, p_hat + error)
                    metodo = "Dos colas"
                elif tipo_intervalo == "Cola superior (p > p₀)":
                    z = stats.norm.ppf(1 - alpha)
                    error = z * np.sqrt(p_hat * (1 - p_hat) / n)
                    li = max(0, p_hat - error)
                    ls = 1
                    metodo = "Cola superior"
                else:  # Cola inferior
                    z = stats.norm.ppf(1 - alpha)
                    error = z * np.sqrt(p_hat * (1 - p_hat) / n)
                    li = 0
                    ls = min(1, p_hat + error)
                    metodo = "Cola inferior"

                st.session_state['prop'] = {
                    'li': li, 'ls': ls,
                    'p_hat': p_hat, 'error': error,
                    'z': z, 'n': n, 'conf': conf_val,
                    'x': x, 'tipo_intervalo': tipo_intervalo,
                    'metodo': metodo
                }

                if tipo_intervalo == "Dos colas (p ≠ p₀)":
                    st.success(f"✅ IC al {conf_val*100:.1f}% para p: ({li:.4f}, {ls:.4f})")
                elif tipo_intervalo == "Cola superior (p > p₀)":
                    st.success(f"✅ IC al {conf_val*100:.1f}% para p: ({li:.4f}, 1)")
                else:
                    st.success(f"✅ IC al {conf_val*100:.1f}% para p: (0, {ls:.4f})")

    with col2:
        if 'prop' in st.session_state:
            res = st.session_state['prop']

            st.subheader("📊 Resultado")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Proporción muestral", f"{res['p_hat']:.4f}")
                if res['li'] == 0:
                    st.metric("Límite Inferior", "0")
                else:
                    st.metric("Límite Inferior", f"{res['li']:.4f}")
            with col_res2:
                st.metric("Error", f"±{res['error']:.4f}")
                if res['ls'] == 1:
                    st.metric("Límite Superior", "1")
                else:
                    st.metric("Límite Superior", f"{res['ls']:.4f}")

            # Verificar condiciones
            n_p = res['n'] * res['p_hat']
            n_q = res['n'] * (1 - res['p_hat'])

            if n_p >= 5 and n_q >= 5:
                st.success(f"✅ Condiciones cumplidas: n·p̂ = {n_p:.1f}, n·(1-p̂) = {n_q:.1f}")
            else:
                st.warning(f"⚠️ Condiciones NO cumplidas: n·p̂ = {n_p:.1f}, n·(1-p̂) = {n_q:.1f}")

            # Gráfico
            x_min = max(0, res['p_hat'] - 0.3)
            x_max = min(1, res['p_hat'] + 0.3)
            x_vals = np.linspace(x_min, x_max, 1000)
            se = res['error'] / res['z']
            y_vals = stats.norm.pdf(x_vals, res['p_hat'], se)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                name='Densidad',
                line=dict(color='#3498db', width=2)
            ))

            if res['tipo_intervalo'] == "Dos colas (p ≠ p₀)":
                mask = (x_vals >= res['li']) & (x_vals <= res['ls'])
                nombre_area = f'IC {res["conf"]*100:.1f}%'
            elif res['tipo_intervalo'] == "Cola superior (p > p₀)":
                mask = x_vals >= res['li']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola superior)'
            else:  # Cola inferior
                mask = x_vals <= res['ls']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola inferior)'

            if np.any(mask):
                fig.add_trace(go.Scatter(
                    x=x_vals[mask],
                    y=y_vals[mask],
                    fill='tozeroy',
                    name=nombre_area,
                    line=dict(color='#e74c3c'),
                    fillcolor='rgba(231, 76, 60, 0.4)'
                ))

            fig.update_layout(
                title=f"Distribución de la Proporción - {res['tipo_intervalo']}",
                xaxis_title="Proporción",
                yaxis_title="Densidad",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PESTAÑA 4: DIFERENCIA DE MEDIAS (CON PAREADAS)
# ============================================================

with tab4:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📌 Tipo de Muestras")
        tipo_muestras = st.radio(
            "Selecciona el tipo de muestras:",
            ["Muestras independientes", "Muestras pareadas"],
            key="tipo_muestras_dif"
        )

        if tipo_muestras == "Muestras independientes":
            st.subheader("📊 Muestra 1")
            n1 = st.number_input("n₁:", min_value=2, value=25, step=1)
            xbar1 = st.number_input("x̄₁:", value=100.0, step=0.1)
            s1 = st.number_input("s₁:", min_value=0.0, value=15.0, step=0.001, format="%.6f")

            st.subheader("📊 Muestra 2")
            n2 = st.number_input("n₂:", min_value=2, value=30, step=1)
            xbar2 = st.number_input("x̄₂:", value=110.0, step=0.1)
            s2 = st.number_input("s₂:", min_value=0.0, value=18.0, step=0.001, format="%.6f")

            st.subheader("🔧 Configuración de Varianzas")
            tipo_var = st.radio(
                "¿Qué sabes de las varianzas poblacionales?",
                [
                    "Varianzas poblacionales conocidas",
                    "Varianzas poblacionales desconocidas pero iguales",
                    "Varianzas poblacionales desconocidas y diferentes"
                ],
                key="tipo_var_dif"
            )

            if tipo_var == "Varianzas poblacionales conocidas":
                sigma1_2 = st.number_input("σ₁²:", min_value=0.0, value=225.0, step=0.001, format="%.6f")
                sigma2_2 = st.number_input("σ₂²:", min_value=0.0, value=324.0, step=0.001, format="%.6f")

        else:  # Muestras pareadas
            st.subheader("📊 Datos de las Diferencias")
            n = st.number_input("Número de pares (n):", min_value=2, value=20, step=1)
            d_bar = st.number_input("Media de las diferencias (d̄):", value=5.0, step=0.1)
            sd_d = st.number_input("Desviación estándar de diferencias (s_d):", min_value=0.0, value=8.0, step=0.001, format="%.6f")

            st.caption("📝 d̄ = Σdᵢ/n, s_d = √(Σ(dᵢ-d̄)²/(n-1))")
            st.caption("📌 Ejemplo: dᵢ = Antes - Después")

        # NIVEL DE CONFIANZA PERSONALIZADO
        conf_val = selector_nivel_confianza("dif_medias")

        st.subheader("📌 Tipo de Intervalo")
        tipo_intervalo = st.radio(
            "Selecciona el tipo:",
            ["Dos colas (μ₁ ≠ μ₂)", "Cola superior (μ₁ > μ₂)", "Cola inferior (μ₁ < μ₂)"],
            key="tipo_intervalo_dif"
        )

        if st.button("🔍 Calcular", key="calcular_dif"):
            alpha = 1 - conf_val

            if tipo_muestras == "Muestras independientes":
                diff = xbar1 - xbar2

                if tipo_var == "Varianzas poblacionales conocidas":
                    if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                        z = stats.norm.ppf(1 - alpha/2)
                    else:
                        z = stats.norm.ppf(1 - alpha)
                    error = z * np.sqrt(sigma1_2/n1 + sigma2_2/n2)
                    if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                        li = diff - error
                        ls = diff + error
                        metodo = "Varianzas conocidas (Z) - Dos colas"
                    elif tipo_intervalo == "Cola superior (μ₁ > μ₂)":
                        li = diff - error
                        ls = float('inf')
                        metodo = "Varianzas conocidas (Z) - Cola superior"
                    else:  # Cola inferior
                        li = -float('inf')
                        ls = diff + error
                        metodo = "Varianzas conocidas (Z) - Cola inferior"
                    valor_critico = z
                    valor_critico_nombre = "Z"
                    gl_metodo = "Z - Normal Estándar"
                    df = None

                elif tipo_var == "Varianzas poblacionales desconocidas pero iguales":
                    df = n1 + n2 - 2
                    s_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / df)
                    if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                        t = stats.t.ppf(1 - alpha/2, df)
                    else:
                        t = stats.t.ppf(1 - alpha, df)
                    error = t * s_pooled * np.sqrt(1/n1 + 1/n2)
                    if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                        li = diff - error
                        ls = diff + error
                        metodo = "Varianzas iguales (t-pooled) - Dos colas"
                    elif tipo_intervalo == "Cola superior (μ₁ > μ₂)":
                        li = diff - error
                        ls = float('inf')
                        metodo = "Varianzas iguales (t-pooled) - Cola superior"
                    else:  # Cola inferior
                        li = -float('inf')
                        ls = diff + error
                        metodo = "Varianzas iguales (t-pooled) - Cola inferior"
                    valor_critico = t
                    valor_critico_nombre = "t"
                    gl_metodo = f"t-Student con ν = {df}"

                else:  # Diferentes
                    df = (s1**2/n1 + s2**2/n2)**2 / ((s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1))
                    if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                        t = stats.t.ppf(1 - alpha/2, df)
                    else:
                        t = stats.t.ppf(1 - alpha, df)
                    error = t * np.sqrt(s1**2/n1 + s2**2/n2)
                    if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                        li = diff - error
                        ls = diff + error
                        metodo = "Varianzas diferentes (Welch) - Dos colas"
                    elif tipo_intervalo == "Cola superior (μ₁ > μ₂)":
                        li = diff - error
                        ls = float('inf')
                        metodo = "Varianzas diferentes (Welch) - Cola superior"
                    else:  # Cola inferior
                        li = -float('inf')
                        ls = diff + error
                        metodo = "Varianzas diferentes (Welch) - Cola inferior"
                    valor_critico = t
                    valor_critico_nombre = "t"
                    gl_metodo = f"t-Student (Welch) con ν = {df:.2f}"

                st.session_state['dif'] = {
                    'li': li, 'ls': ls, 'diff': diff, 'error': error,
                    'conf': conf_val, 'metodo': metodo,
                    'valor_critico': valor_critico,
                    'valor_critico_nombre': valor_critico_nombre,
                    'gl_metodo': gl_metodo,
                    'tipo_muestras': 'independientes',
                    'n1': n1, 'n2': n2,
                    'xbar1': xbar1, 'xbar2': xbar2,
                    's1': s1, 's2': s2,
                    'df': df,
                    'tipo_intervalo': tipo_intervalo
                }

            else:  # Muestras pareadas
                diff = d_bar
                df = n - 1
                if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                    t = stats.t.ppf(1 - alpha/2, df)
                else:
                    t = stats.t.ppf(1 - alpha, df)
                error = t * sd_d / np.sqrt(n)
                if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                    li = diff - error
                    ls = diff + error
                    metodo = "Muestras pareadas (t-pareada) - Dos colas"
                elif tipo_intervalo == "Cola superior (μ₁ > μ₂)":
                    li = diff - error
                    ls = float('inf')
                    metodo = "Muestras pareadas (t-pareada) - Cola superior"
                else:  # Cola inferior
                    li = -float('inf')
                    ls = diff + error
                    metodo = "Muestras pareadas (t-pareada) - Cola inferior"
                valor_critico = t
                valor_critico_nombre = "t"
                gl_metodo = f"t-Student con ν = {df}"

                st.session_state['dif'] = {
                    'li': li, 'ls': ls, 'diff': diff, 'error': error,
                    'conf': conf_val, 'metodo': metodo,
                    'valor_critico': valor_critico,
                    'valor_critico_nombre': valor_critico_nombre,
                    'gl_metodo': gl_metodo,
                    'tipo_muestras': 'pareadas',
                    'n': n,
                    'd_bar': d_bar,
                    'sd_d': sd_d,
                    'df': df,
                    'tipo_intervalo': tipo_intervalo
                }

            if tipo_intervalo == "Dos colas (μ₁ ≠ μ₂)":
                st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.4f}, {ls:.4f})")
            elif tipo_intervalo == "Cola superior (μ₁ > μ₂)":
                st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.4f}, ∞)")
            else:
                st.success(f"✅ IC al {conf_val*100:.1f}%: (-∞, {ls:.4f})")

    with col2:
        if 'dif' in st.session_state:
            res = st.session_state['dif']

            st.subheader("📊 Resultado")

            if res['tipo_muestras'] == 'pareadas':
                st.info("📌 MUESTRAS PAREADAS")
                st.metric("Media de diferencias (d̄)", f"{res['diff']:.4f}")
            else:
                st.info("📌 MUESTRAS INDEPENDIENTES")
                st.metric("Diferencia de medias", f"{res['diff']:.4f}")

            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                if res['li'] == -float('inf'):
                    st.metric("Límite Inferior", "-∞")
                else:
                    st.metric("Límite Inferior", f"{res['li']:.4f}")
            with col_res2:
                if res['ls'] == float('inf'):
                    st.metric("Límite Superior", "∞")
                else:
                    st.metric("Límite Superior", f"{res['ls']:.4f}")
            with col_res3:
                st.metric(f"{res['valor_critico_nombre']}", f"{res['valor_critico']:.4f}")

            st.info(f"📌 {res['metodo']}")
            st.info(f"📌 {res['gl_metodo']}")

            # Gráfico
            if res['tipo_intervalo'] == "Dos colas (μ₁ ≠ μ₂)":
                x_min = res['li'] - 2*res['error']
                x_max = res['ls'] + 2*res['error']
            else:
                rango = 4 * res['error']
                x_min = res['diff'] - rango
                x_max = res['diff'] + rango
            x_vals = np.linspace(x_min, x_max, 1000)

            if res['tipo_muestras'] == 'pareadas':
                se = res['error'] / stats.t.ppf(1 - (1-res['conf'])/2, res['df'])
                y_vals = stats.t.pdf((x_vals - res['diff']) / se, res['df']) / se
                titulo = "Distribución t-Student para Muestras Pareadas"
            else:
                if 'Z' in res['metodo']:
                    se = res['error'] / stats.norm.ppf(1 - (1-res['conf'])/2)
                    y_vals = stats.norm.pdf(x_vals, res['diff'], se)
                    titulo = "Distribución Normal Estándar (Z)"
                else:
                    se = res['error'] / stats.t.ppf(1 - (1-res['conf'])/2, res['df'])
                    y_vals = stats.t.pdf((x_vals - res['diff']) / se, res['df']) / se
                    titulo = "Distribución t-Student"

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                name='Densidad',
                line=dict(color='#3498db', width=2)
            ))

            if res['tipo_intervalo'] == "Dos colas (μ₁ ≠ μ₂)":
                mask = (x_vals >= res['li']) & (x_vals <= res['ls'])
                nombre_area = f'IC {res["conf"]*100:.1f}%'
            elif res['tipo_intervalo'] == "Cola superior (μ₁ > μ₂)":
                mask = x_vals >= res['li']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola superior)'
            else:  # Cola inferior
                mask = x_vals <= res['ls']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola inferior)'

            if np.any(mask):
                fig.add_trace(go.Scatter(
                    x=x_vals[mask],
                    y=y_vals[mask],
                    fill='tozeroy',
                    name=nombre_area,
                    line=dict(color='#e74c3c'),
                    fillcolor='rgba(231, 76, 60, 0.4)'
                ))

            fig.add_vline(x=res['diff'], line_dash="dash", line_color="#2c3e50")
            fig.add_vline(x=0, line_dash="dot", line_color="#999999")

            fig.update_layout(
                title=f"{titulo} - {res['tipo_intervalo']}",
                xaxis_title="Diferencia",
                yaxis_title="Densidad",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # Interpretación
            st.subheader("📝 Interpretación")
            if res['tipo_intervalo'] == "Dos colas (μ₁ ≠ μ₂)":
                if res['li'] > 0:
                    st.success("✅ El intervalo es completamente POSITIVO - Hay diferencia significativa")
                elif res['ls'] < 0:
                    st.success("✅ El intervalo es completamente NEGATIVO - Hay diferencia significativa")
                else:
                    st.warning("⚠️ El intervalo CONTIENE EL CERO - No hay evidencia de diferencia")
            elif res['tipo_intervalo'] == "Cola superior (μ₁ > μ₂)":
                st.info("📌 Intervalo de cola superior (μ₁ > μ₂)")
                if res['li'] > 0:
                    st.success("✅ μ₁ es significativamente mayor que μ₂")
                else:
                    st.warning("⚠️ No hay evidencia suficiente para afirmar que μ₁ > μ₂")
            else:  # Cola inferior
                st.info("📌 Intervalo de cola inferior (μ₁ < μ₂)")
                if res['ls'] < 0:
                    st.success("✅ μ₁ es significativamente menor que μ₂")
                else:
                    st.warning("⚠️ No hay evidencia suficiente para afirmar que μ₁ < μ₂")

# ============================================================
# PESTAÑA 5: COCIENTE DE VARIANZAS
# ============================================================

with tab5:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📊 Muestra 1")
        n1 = st.number_input("n₁:", min_value=2, value=15, step=1)
        s1_2 = st.number_input("s₁²:", min_value=0.0, value=25.0, step=0.001, format="%.6f")

        st.subheader("📊 Muestra 2")
        n2 = st.number_input("n₂:", min_value=2, value=20, step=1)
        s2_2 = st.number_input("s₂²:", min_value=0.0, value=16.0, step=0.001, format="%.6f")

        # NIVEL DE CONFIANZA PERSONALIZADO
        conf_val = selector_nivel_confianza("cociente")

        st.subheader("📌 Tipo de Intervalo")
        tipo_intervalo = st.radio(
            "Selecciona el tipo:",
            ["Dos colas (σ₁² ≠ σ₂²)", "Cola superior (σ₁² > σ₂²)", "Cola inferior (σ₁² < σ₂²)"],
            key="tipo_intervalo_coc"
        )

        if st.button("🔍 Calcular", key="calcular_coc"):
            alpha = 1 - conf_val
            df1 = n1 - 1
            df2 = n2 - 1

            if s1_2 == 0 or s2_2 == 0:
                st.warning("⚠️ Una de las varianzas es 0. El cociente será 0 o infinito.")
                ratio = s1_2 / s2_2 if s2_2 > 0 else float('inf')
            else:
                ratio = s1_2 / s2_2

            if tipo_intervalo == "Dos colas (σ₁² ≠ σ₂²)":
                F_inf = stats.f.ppf(alpha/2, df1, df2)
                F_sup = stats.f.ppf(1 - alpha/2, df1, df2)
                li = ratio / F_sup if F_sup > 0 else 0
                ls = ratio / F_inf if F_inf > 0 else float('inf')
                metodo = "Dos colas"
            elif tipo_intervalo == "Cola superior (σ₁² > σ₂²)":
                F_inf = stats.f.ppf(1 - alpha, df1, df2)
                F_sup = float('inf')
                li = ratio / F_inf if F_inf > 0 else 0
                ls = float('inf')
                metodo = "Cola superior"
            else:  # Cola inferior
                F_inf = 0
                F_sup = stats.f.ppf(1 - alpha, df1, df2)
                li = 0
                ls = ratio / F_sup if F_sup > 0 else 0
                metodo = "Cola inferior"

            st.session_state['coc'] = {
                'li': li, 'ls': ls,
                'ratio': ratio,
                'F_inf': F_inf if F_inf != float('inf') else None,
                'F_sup': F_sup if F_sup != float('inf') else None,
                'df1': df1, 'df2': df2,
                'conf': conf_val,
                'tipo_intervalo': tipo_intervalo,
                'metodo': metodo
            }

            if tipo_intervalo == "Dos colas (σ₁² ≠ σ₂²)":
                st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.4f}, {ls:.4f})")
            elif tipo_intervalo == "Cola superior (σ₁² > σ₂²)":
                st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.4f}, ∞)")
            else:
                st.success(f"✅ IC al {conf_val*100:.1f}%: (0, {ls:.4f})")

    with col2:
        if 'coc' in st.session_state:
            res = st.session_state['coc']

            st.subheader("📊 Resultado")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Cociente", f"{res['ratio']:.4f}")
                if res['li'] == 0:
                    st.metric("Límite Inferior", "0")
                elif res['li'] == float('inf'):
                    st.metric("Límite Inferior", "∞")
                else:
                    st.metric("Límite Inferior", f"{res['li']:.4f}")
            with col_res2:
                if res['ls'] == float('inf'):
                    st.metric("Límite Superior", "∞")
                else:
                    st.metric("Límite Superior", f"{res['ls']:.4f}")
                if res['F_sup'] is not None:
                    st.metric("F crítico", f"{res['F_sup']:.4f}")

            st.info(f"📌 df1 = {res['df1']}, df2 = {res['df2']}")
            st.info(f"📌 Método: {res['metodo']}")

            # Gráfico
            x_max = max(10, res['ls'] * 1.5 if res['ls'] != float('inf') else 20)
            x_vals = np.linspace(0.01, x_max, 1000)
            y_vals = stats.f.pdf(x_vals, res['df1'], res['df2'])

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                name='Densidad',
                line=dict(color='#3498db', width=2)
            ))

            if res['tipo_intervalo'] == "Dos colas (σ₁² ≠ σ₂²)":
                mask = (x_vals >= res['li']) & (x_vals <= res['ls'])
                nombre_area = f'IC {res["conf"]*100:.1f}%'
            elif res['tipo_intervalo'] == "Cola superior (σ₁² > σ₂²)":
                mask = x_vals >= res['li']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola superior)'
            else:  # Cola inferior
                mask = x_vals <= res['ls']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola inferior)'

            if np.any(mask):
                fig.add_trace(go.Scatter(
                    x=x_vals[mask],
                    y=y_vals[mask],
                    fill='tozeroy',
                    name=nombre_area,
                    line=dict(color='#e74c3c'),
                    fillcolor='rgba(231, 76, 60, 0.4)'
                ))

            fig.add_vline(x=1, line_dash="dot", line_color="#999999")

            fig.update_layout(
                title=f"Distribución F - {res['tipo_intervalo']}",
                xaxis_title="Cociente de varianzas",
                yaxis_title="Densidad",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PESTAÑA 6: DIFERENCIA DE PROPORCIONES
# ============================================================

with tab6:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📊 Muestra 1")
        n1 = st.number_input("n₁:", min_value=1, value=100, step=1)
        x1 = st.number_input("x₁:", min_value=0, value=45, step=1)

        st.subheader("📊 Muestra 2")
        n2 = st.number_input("n₂:", min_value=1, value=120, step=1)
        x2 = st.number_input("x₂:", min_value=0, value=50, step=1)

        # NIVEL DE CONFIANZA PERSONALIZADO
        conf_val = selector_nivel_confianza("prop_dif")

        st.subheader("📌 Tipo de Intervalo")
        tipo_intervalo = st.radio(
            "Selecciona el tipo:",
            ["Dos colas (p₁ ≠ p₂)", "Cola superior (p₁ > p₂)", "Cola inferior (p₁ < p₂)"],
            key="tipo_intervalo_prop_dif"
        )

        if st.button("🔍 Calcular", key="calcular_prop_dif"):
            if x1 > n1 or x2 > n2:
                st.error("❌ Error: x no puede ser mayor que n")
            else:
                alpha = 1 - conf_val
                p1_hat = x1 / n1
                p2_hat = x2 / n2
                diff = p1_hat - p2_hat

                if tipo_intervalo == "Dos colas (p₁ ≠ p₂)":
                    z = stats.norm.ppf(1 - alpha/2)
                    metodo = "Dos colas"
                else:
                    z = stats.norm.ppf(1 - alpha)
                    metodo = "Cola superior" if tipo_intervalo == "Cola superior (p₁ > p₂)" else "Cola inferior"

                error = z * np.sqrt(p1_hat*(1-p1_hat)/n1 + p2_hat*(1-p2_hat)/n2)

                if tipo_intervalo == "Dos colas (p₁ ≠ p₂)":
                    li = diff - error
                    ls = diff + error
                elif tipo_intervalo == "Cola superior (p₁ > p₂)":
                    li = diff - error
                    ls = 1
                else:  # Cola inferior
                    li = -1
                    ls = diff + error

                st.session_state['prop_dif'] = {
                    'li': li, 'ls': ls,
                    'diff': diff, 'error': error,
                    'p1_hat': p1_hat, 'p2_hat': p2_hat,
                    'z': z, 'conf': conf_val,
                    'n1': n1, 'n2': n2,
                    'tipo_intervalo': tipo_intervalo,
                    'metodo': metodo
                }

                if tipo_intervalo == "Dos colas (p₁ ≠ p₂)":
                    st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.4f}, {ls:.4f})")
                elif tipo_intervalo == "Cola superior (p₁ > p₂)":
                    st.success(f"✅ IC al {conf_val*100:.1f}%: ({li:.4f}, 1)")
                else:
                    st.success(f"✅ IC al {conf_val*100:.1f}%: (-1, {ls:.4f})")

    with col2:
        if 'prop_dif' in st.session_state:
            res = st.session_state['prop_dif']

            st.subheader("📊 Resultado")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("p̂₁", f"{res['p1_hat']:.4f}")
                st.metric("p̂₂", f"{res['p2_hat']:.4f}")
                st.metric("Diferencia", f"{res['diff']:.4f}")
            with col_res2:
                if res['li'] == -1:
                    st.metric("Límite Inferior", "-1")
                else:
                    st.metric("Límite Inferior", f"{res['li']:.4f}")
                if res['ls'] == 1:
                    st.metric("Límite Superior", "1")
                else:
                    st.metric("Límite Superior", f"{res['ls']:.4f}")
                st.metric("Error", f"±{res['error']:.4f}")

            # Gráfico
            if res['tipo_intervalo'] == "Dos colas (p₁ ≠ p₂)":
                x_min = res['li'] - 2*res['error']
                x_max = res['ls'] + 2*res['error']
            else:
                rango = 4 * res['error']
                x_min = res['diff'] - rango
                x_max = res['diff'] + rango
            x_vals = np.linspace(x_min, x_max, 1000)
            se = res['error'] / res['z']
            y_vals = stats.norm.pdf(x_vals, res['diff'], se)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                name='Densidad',
                line=dict(color='#3498db', width=2)
            ))

            if res['tipo_intervalo'] == "Dos colas (p₁ ≠ p₂)":
                mask = (x_vals >= res['li']) & (x_vals <= res['ls'])
                nombre_area = f'IC {res["conf"]*100:.1f}%'
            elif res['tipo_intervalo'] == "Cola superior (p₁ > p₂)":
                mask = x_vals >= res['li']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola superior)'
            else:  # Cola inferior
                mask = x_vals <= res['ls']
                nombre_area = f'IC {res["conf"]*100:.1f}% (cola inferior)'

            if np.any(mask):
                fig.add_trace(go.Scatter(
                    x=x_vals[mask],
                    y=y_vals[mask],
                    fill='tozeroy',
                    name=nombre_area,
                    line=dict(color='#e74c3c'),
                    fillcolor='rgba(231, 76, 60, 0.4)'
                ))

            fig.add_vline(x=0, line_dash="dot", line_color="#999999")

            fig.update_layout(
                title=f"Diferencia de Proporciones - {res['tipo_intervalo']}",
                xaxis_title="Diferencia",
                yaxis_title="Densidad",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # Interpretación
            st.subheader("📝 Interpretación")
            if res['tipo_intervalo'] == "Dos colas (p₁ ≠ p₂)":
                if res['li'] > 0:
                    st.success("✅ p₁ > p₂ - Diferencia significativa")
                elif res['ls'] < 0:
                    st.success("✅ p₁ < p₂ - Diferencia significativa")
                else:
                    st.warning("⚠️ No hay diferencia significativa entre las proporciones")
            elif res['tipo_intervalo'] == "Cola superior (p₁ > p₂)":
                st.info("📌 Intervalo de cola superior (p₁ > p₂)")
                if res['li'] > 0:
                    st.success("✅ p₁ es significativamente mayor que p₂")
                else:
                    st.warning("⚠️ No hay evidencia suficiente para afirmar que p₁ > p₂")
            else:  # Cola inferior
                st.info("📌 Intervalo de cola inferior (p₁ < p₂)")
                if res['ls'] < 0:
                    st.success("✅ p₁ es significativamente menor que p₂")
                else:
                    st.warning("⚠️ No hay evidencia suficiente para afirmar que p₁ < p₂")

st.markdown("---")
st.caption("📊 Calculadora de Intervalos de Confianza - Desarrollada con ❤️ usando Streamlit")
