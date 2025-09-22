import streamlit as st
import pandas as pd
import re
from sqlalchemy import create_engine, inspect, text

# ----------------- DB CONFIG -----------------
db_user = 'isa_user'
db_password = '4-]8sd51D£A6'
db_host = 'tp-vendor-db.ch6c0kme2q7u.ap-south-1.rds.amazonaws.com'
db_name = 'isa_logistics'
db_port = 3306

# Create DB engine
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

# ----------------- COLUMN CLEAN FUNCTION -----------------
def clean_column_names(df, table_name):
    target_tables = ["SeaExport_Actual", "SeaExport_Planned", "SeaImport_Actual", "SeaImport_Planned", "AirExport_Actual", "AirExport_Planned", "AirImport_Actual", "AirImport_Planned"]

    if table_name in target_tables:
        new_columns = []
        for col in df.columns:
            orig_col = col

            # If starts with "*", add Planned_
            if col.strip().startswith("*"):
                col = col.strip().lstrip("*").strip()
                col = "Planned_" + col

            # Replace common symbols & phrases
            col = col.replace(".", "")
            col = col.replace("20'", "twenty_ft")
            col = col.replace("40'", "fourty_ft")
            col = col.replace("ContCount_20FT", "twenty_ft")
            col = col.replace("ContCount_40FT", "fourty_ft")
            col = col.replace("P/L %", "p_l_percent")
            col = col.replace("P/L", "p_l")
            col = col.replace("&", "and")
            col = col.replace("imp/exp", "imp_exp")
            col = col.replace("imp/ exp", "imp_exp")
            col = col.replace("Tax Invoice to Client", "Tax_Invoice_to_Client")
            col = col.replace("Docs Sent to customer", "Docs_Sent_to_Customer")
            col = col.replace("Billing to customer", "Billing_to_customer")
            col = col.replace("Cargo Handover to Airlines", "Cargo_Handover_to_Airlines")
            col = col.replace("Pick up Date at Origin", "Pick_up_Date_at_Origin")
            col = col.replace("Console / IGM Filing", "Console_IGM_Filing")

            # Replace whole words "from" and "to" safely
            col = re.sub(r'\bfrom\b', 'pick_up_from', col, flags=re.IGNORECASE)
            col = re.sub(r'\bto\b', 'drop_at', col, flags=re.IGNORECASE)

            # Replace spaces with underscores
            col = col.replace(" ", "_")

            # Replace other invalid chars with underscore
            col = re.sub(r'[^A-Za-z0-9_]', "_", col)

            new_columns.append(col)

            # Debugging
            if orig_col != col:
                print(f"Renamed: {orig_col} → {col}")

        df.columns = new_columns
    return df

# ----------------- ADD DEPARTMENT FUNCTION -----------------
def add_department_column(df, table_name):
    if table_name in ["SeaExport_Actual", "SeaExport_Planned"]:
        df["Department"] = "Sea Export"
    elif table_name in ["SeaImport_Actual", "SeaImport_Planned"]:
        df["Department"] = "Sea Import"
    return df

# ----------------- STREAMLIT APP -----------------
st.set_page_config(page_title="Excel to MySQL Uploader", layout="wide")

st.title("📊 Excel → MySQL Upload Tool")

# Step 1: Upload Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Load Excel
    df = pd.read_excel(uploaded_file)
    st.info("📂 Original Excel Columns:")
    st.write(df.columns.tolist())

    # Step 2: Fetch DB tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if tables:
        selected_table = st.selectbox("Select a table to upload into:", tables)

        if st.button("Clean & Upload Data"):
            try:
                # Clean column names
                df = clean_column_names(df, selected_table)

                # Add Department column if required
                df = add_department_column(df, selected_table)

                # Show cleaned DataFrame
                st.success("✅ Columns cleaned!")
                st.write("🔄 Final Column Names:", df.columns.tolist())
                st.dataframe(df.head())

                # -------- DELETE EXISTING DATA --------
                with engine.connect() as conn:
                    conn.execute(text(f"DELETE FROM {selected_table}"))
                    conn.commit()
                st.warning(f"⚠️ Existing data in `{selected_table}` deleted!")

                # -------- UPLOAD NEW DATA --------
                df.to_sql(name=selected_table, con=engine, if_exists="append", index=False)
                st.success(f"🚀 New data uploaded into `{selected_table}` successfully!")

            except Exception as e:
                st.error(f"❌ Error during upload: {e}")
    else:
        st.warning("⚠️ No tables found in the database.")
