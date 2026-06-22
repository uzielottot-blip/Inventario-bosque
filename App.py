
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime
import time

# Configuración de página profesional
st.set_page_config(page_title="Bosque Eterno - Inventario Realtime", layout="wide", page_icon="🌳")

st.title("🌳 Gestión de Insumos - Bosque Eterno (Nube)")
st.markdown("---")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Asegúrate de haber compartido tu hoja con el correo de la cuenta de servicio
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer datos (ttl=0 para ver cambios al instante)
try:
    df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1bXMFdp8zZ_l1h3kPtIpINesdm1QPw1d_RYMuh7kBkc0/edit", ttl="0s")
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- BARRA LATERAL: ENTRADA DINÁMICA ---
with st.sidebar:
    if "limpiador" not in st.session_state:
        st.session_state.limpiador = 0
    st.header("📥 Nueva Entrada")
    nombre_in = st.text_input("Nombre del producto", key=f"nombre_{st.session_state.limpiador}")
    area_in = st.selectbox("Área de destino", ["Selecciona...", "Operativo", "Caseta", "Boutique", "Vivero", "Papeleria", "Sala de despedida"], key=f"area_{st.session_state.limpiador}")
    empaque_in = st.selectbox("¿Cómo viene el empaque?", ["Selecciona...", "Caja", "Pieza Única", "Bulto"], key=f"empaque_{st.session_state.limpiador}")
    
    total_calc = 0
    medida_in = ""

    if empaque_in == "Caja":
        c_cajas = st.number_input("¿Cuántas cajas?", min_value=1, step=1)
        u_caja = st.number_input("¿Piezas por caja?", min_value=1, step=1)
        medida_in, total_calc = "Piezas", c_cajas * u_caja
    elif empaque_in == "Pieza Única":
        medida_in = st.selectbox("Presentación", ["Piezas", "Gramos (g)", "Mililitros (ml)", "Litros (L)"])
        total_calc = st.number_input(f"Cantidad de {medida_in}", min_value=1.0, step=1.0)
    elif empaque_in == "Bulto":
        c_bultos = st.number_input("¿Bultos?", min_value=1, step=1)
        medida_in = st.selectbox("Unidad", ["Kilogramos (kg)", "Gramos (g)", "Litros (L)"])
        g_bulto = st.number_input(f"Peso/Capacidad", min_value=0.1, step=1.0)
        total_calc = c_bultos * g_bulto

    f_llegada_in = st.date_input("Llegada", date.today())
    f_apert_in = st.date_input("Apertura (opcional)", value=None)
    notas_in = st.text_area("Notas")
    
    if st.button("Subir a la Nube", type="primary"):
        if nombre_in and empaque_in != "Selecciona..." and area_in != "Selecciona...":
            # Crear nueva fila
            nueva_fila = pd.DataFrame([{
                "Producto": nombre_in.replace("*", "").strip(),
                "Área": area_in,
                "Empaque": empaque_in,
                "Stock": float(total_calc),
                "Medida": medida_in,
                "Llegada": str(f_llegada_in),
                "Apertura": str(f_apert_in) if f_apert_in else "-",
                "Terminado": "-",
                "Notas": notas_in
            }])
            # Actualizar Google Sheets
            df_actualizado = conn.read()
            df_final = pd.concat([df_actualizado, nueva_fila], ignore_index=True)
            conn.update(data=df_final)
            st.success(f"✅ ¡{nombre_in} se registró exitosamente en la nube!")
            st.session_state.limpiador += 1
            time.sleep(1)
            for clave in ["k_nombre", "k_area", "k_empaque"]:
                if clave in st.session_state:
                    st.session_state[clave] = "" if "nombre" in clave else "Selecciona..."
            st.rerun()

# --- PESTAÑAS ---
tab_ver, tab_usar, tab_admin = st.tabs(["🔍 Buscador e Inventario", "➖ Registrar Salida", "🛠️ Editar o Borrar"])

with tab_ver:
    if not df.empty:
        busqueda = st.text_input("🔎 Buscar producto...", placeholder="Ej: Café, Sanitas...")
        df_mostrar = df.copy()
        if busqueda:
            df_mostrar = df[df["Producto"].str.contains(busqueda, case=False, na=False)]

        st.divider()
        # Encabezados visuales
        h_cols = st.columns([2, 1.5, 1, 1, 1, 1, 2])
        headers = ["Producto", "Área", "Stock", "Medida", "Estado", "Apertura", "Notas / Historial"]
        for i, h in enumerate(headers): h_cols[i].write(f"**{h}**")
        st.divider()

        for index, fila in df_mostrar.iterrows():
            stock_val = float(fila["Stock"])
            # Semáforo
            if stock_val <= 0: semaforo = "🔴 Agotado"
            elif stock_val < 10: semaforo = "🟡 Bajo"
            else: semaforo = "🟢 OK"

            r_cols = st.columns([2, 1.5, 1, 1, 1, 1, 2])
            r_cols[0].write(f"**{fila['Producto']}**")
            r_cols[1].write(str(fila['Área']).replace('nan', '-')) # Muestra el área o un guión si está vacío
            r_cols[2].write(f"{fila['Stock']}")
            r_cols[3].write(f"{fila['Medida']}")
            r_cols[4].write(semaforo)
            r_cols[5].write(fila["Apertura"])
            r_cols[6].write(f"_{fila['Notas']}_")
            st.divider()
    else:
        st.info("La nube está vacía.")

with tab_usar:
    st.header("➖ Descontar Insumo")
    if not df.empty:
        # Solo mostrar productos con stock
        opciones = [f"{i} | {df.at[i, 'Producto']} - {df.at[i, 'Área']} ({df.at[i, 'Stock']} {df.at[i, 'Medida']})" 
                    for i in df.index if float(df.at[i, 'Stock']) > 0]
        
        if opciones:
            
                sel = st.selectbox("¿Qué vas a ocupar?", opciones)
                cant_u = st.number_input("Cantidad a retirar", min_value=1.0, step=1.0)
                f_u = st.date_input("Fecha de hoy", date.today())
                mot_u = st.text_input("Motivo (Ej: Servicio Sala A)")
                
                if st.button("Confirmar Salida", type="primary"):
                    idx_u = int(sel.split(" | ")[0])
                    stock_act = float(df.at[idx_u, 'Stock'])
                    
                    if cant_u <= stock_act:
                        df.at[idx_u, 'Stock'] = round(stock_act - cant_u, 2)
                        # Fecha de apertura automática
                        if df.at[idx_u, 'Apertura'] == "-": df.at[idx_u, 'Apertura'] = str(f_u)
                        # Fecha terminado
                        if df.at[idx_u, 'Stock'] <= 0: df.at[idx_u, 'Terminado'] = str(f_u)
                        # Historial
                        nota_actual = str(df.at[idx_u, 'Notas'])

                        df['Notas'] = df['Notas'].astype(object)
                        nota_actual = str(df.at[idx_u, 'Notas'])
                        if nota_actual == "nan" or nota_actual == "None":nota_actual = ""
                        df.at[idx_u, 'Notas'] = nota_actual + f" | [{f_u}] -{cant_u} ({mot_u})"
                        conn.update(data=df)
                        st.success("¡Nube actualizada!")
                        st.success(f"✅ ¡Salida confirmada exitosamente! Se retiró la cantidad solicitada.")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("No hay suficiente stock.")

with tab_admin:
    st.header("🛠️ Modificar o Borrar")
    if not df.empty:
        edit_list = [f"{i} | {df.at[i, 'Producto']} - {df.at[i, 'Área']}" for i in df.index]
        sel_edit = st.selectbox("Selecciona para editar:", edit_list)
        idx_e = int(sel_edit.split(" | ")[0])
        
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.subheader("📝 Editar")
            n_nom = st.text_input("Nombre", value=df.at[idx_e, 'Producto'])
            n_area = st.text_input("Área", value=str(df.at[idx_e, 'Área']).replace('nan', ''))
            n_stk = st.number_input("Stock", value=float(df.at[idx_e, 'Stock']))
            n_ape = st.text_input("Fecha Apertura (YYYY-MM-DD)", value=df.at[idx_e, 'Apertura'])
            n_not = st.text_area("Notas", value=df.at[idx_e, 'Notas'])
            if st.button("Guardar Cambios", type="primary"):
                df.at[idx_e, 'Producto'], df.at[idx_e, 'Stock'] = n_nom, n_stk
                df.at[idx_e, 'Apertura'], df.at[idx_e, 'Notas'] = n_ape, n_not
                df.at[idx_e, 'Área'] = n_area
                conn.update(data=df)
                st.rerun()
        with col_e2:
            st.subheader("🗑️ Eliminar")
            if st.button("BORRAR DE LA NUBE"):
                df = df.drop(idx_e)
                conn.update(data=df)
                st.success("🗑️ El producto se ha borrado correctamente de la base de datos.")
                time.sleep(2)
                st.rerun()
                st.divider() # Dibuja una línea separadora bonita
st.subheader("🛒 Lista de Compras Urgente")

# Convertimos la columna a números por si hay algún texto accidental
df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce')

# Filtramos solo los que tienen stock menor o igual a tu límite (stock_minimo)
# Definimos el límite de alerta (puedes cambiar este 5 por el número que quieras)
stock_minimo = 5
df_compras = df[df['Stock'] <= stock_minimo]

# Si la lista NO está vacía, mostramos la advertencia y la tabla
if not df_compras.empty:
    st.warning("⚠️ Atención: Es necesario pedir los siguientes insumos a la brevedad:")
    # Solo mostramos el Nombre, el Stock actual y la Medida
    st.dataframe(df_compras[['Producto', 'Stock', 'Medida']])
else:
    # Si la lista está vacía, mostramos un mensaje de tranquilidad
    st.success("✨ ¡Todo el inventario está en niveles óptimos! No hay compras urgentes.")