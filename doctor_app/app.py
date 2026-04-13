import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

DB_FILE = 'clinic.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            address TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            visit_date TEXT,
            symptoms TEXT,
            diagnosis TEXT,
            treatment TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER,
            treatment_cost REAL,
            amount_paid REAL,
            balance REAL,
            FOREIGN KEY (visit_id) REFERENCES visits(id)
        )
    ''')
    conn.commit()
    conn.close()

def run_query(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.commit()
    conn.close()
    return data

def get_dataframe(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def main():
    st.set_page_config(page_title="Doctor-Patient Management System", page_icon="🏥", layout="wide")
    init_db()

    st.sidebar.title("🏥 Clinic Manager")
    menu = ["Dashboard", "Patients", "Add Patient"]
    choice = st.sidebar.selectbox("Navigation", menu)

    if choice == "Dashboard":
        show_dashboard()
    elif choice == "Patients":
        show_patients()
    elif choice == "Add Patient":
        show_add_patient()

def show_dashboard():
    st.title("📊 Dashboard")
    
    total_patients_res = run_query("SELECT COUNT(*) FROM patients")
    total_patients = total_patients_res[0][0] if total_patients_res else 0
    
    billing_data = run_query("SELECT SUM(treatment_cost), SUM(balance) FROM billing")
    if billing_data and billing_data[0][0] is not None:
        total_revenue = billing_data[0][0]
        pending_balance = billing_data[0][1]
    else:
        total_revenue = 0.0
        pending_balance = 0.0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Patients", total_patients)
    col2.metric("Total Revenue", f"${total_revenue:,.2f}")
    col3.metric("Pending Balance", f"${pending_balance:,.2f}")
    
    st.subheader("Recent Visits")
    recent_visits_query = '''
        SELECT v.visit_date as "Date", p.name as "Patient", v.diagnosis as "Diagnosis", b.balance as "Balance"
        FROM visits v
        JOIN patients p ON v.patient_id = p.id
        LEFT JOIN billing b ON v.id = b.visit_id
        ORDER BY v.visit_date DESC LIMIT 5
    '''
    df_recent = get_dataframe(recent_visits_query)
    if not df_recent.empty:
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("No recent visits found.")

def show_patients():
    st.title("👥 Patients")
    
    search_term = st.text_input("🔍 Search Patient by Name")
    
    if search_term:
        query = "SELECT id, name as 'Name', age as 'Age', gender as 'Gender', phone as 'Phone' FROM patients WHERE name LIKE ?"
        df = get_dataframe(query, ('%' + search_term + '%',))
    else:
        query = "SELECT id, name as 'Name', age as 'Age', gender as 'Gender', phone as 'Phone' FROM patients"
        df = get_dataframe(query)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.subheader("📄 Patient Details")
        patient_names = [f"{row['id']} - {row['Name']}" for index, row in df.iterrows()]
        selected_patient = st.selectbox("Select Patient", [""] + patient_names)
        
        if selected_patient:
            patient_id = int(selected_patient.split(" - ")[0])
            show_patient_details(patient_id)
    else:
        st.info("No patients match your search criteria.")

def show_add_patient():
    st.title("➕ Add New Patient")
    
    with st.form("add_patient_form", clear_on_submit=True):
        name = st.text_input("Name *")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, step=1)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            
        phone = st.text_input("Phone")
        address = st.text_area("Address")
        submit = st.form_submit_button("Register Patient")
        
        if submit:
            if not name.strip():
                st.error("Name is required!")
            else:
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                run_query('''
                    INSERT INTO patients (name, age, gender, phone, address, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, age, gender, phone, address, created_at))
                st.success(f"Patient '{name}' registered successfully!")

def show_patient_details(patient_id):
    patient_info = run_query("SELECT * FROM patients WHERE id=?", (patient_id,))
    if not patient_info:
        st.error("Patient not found.")
        return
        
    p = patient_info[0]
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {p[1]}")
        st.markdown(f"**Age:** {p[2]}")
        st.markdown(f"**Gender:** {p[3]}")
    with col2:
        st.markdown(f"**Phone:** {p[4]}")
        st.markdown(f"**Address:** {p[5]}")
        st.markdown(f"**Registered:** {p[6]}")
        
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 Visit History", "➕ Add Visit", "⚙️ Edit/Delete"])
    
    with tab1:
        st.subheader("Visit History")
        visits_query = '''
            SELECT v.id as "Visit ID", v.visit_date as "Date", v.symptoms as "Symptoms", 
                   v.diagnosis as "Diagnosis", v.treatment as "Treatment", 
                   b.treatment_cost as "Cost", b.amount_paid as "Paid", b.balance as "Balance"
            FROM visits v
            LEFT JOIN billing b ON v.id = b.visit_id
            WHERE v.patient_id = ?
            ORDER BY v.visit_date DESC
        '''
        df_visits = get_dataframe(visits_query, (patient_id,))
        if not df_visits.empty:
            st.dataframe(df_visits, use_container_width=True, hide_index=True)
        else:
            st.info("No visits recorded yet.")
            
    with tab2:
        st.subheader("Record New Visit")
        with st.form("add_visit_form", clear_on_submit=True):
            visit_date = st.date_input("Visit Date", datetime.today())
            symptoms = st.text_area("Symptoms")
            diagnosis = st.text_input("Diagnosis")
            treatment = st.text_area("Treatment")
            
            st.markdown("---")
            st.markdown("**Billing Details**")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                cost = st.number_input("Treatment Cost ($)", min_value=0.0, step=0.01)
            with col_b2:
                paid = st.number_input("Amount Paid ($)", min_value=0.0, step=0.01)
            
            submit_visit = st.form_submit_button("Save Visit & Billing")
            
            if submit_visit:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO visits (patient_id, visit_date, symptoms, diagnosis, treatment)
                    VALUES (?, ?, ?, ?, ?)
                ''', (patient_id, visit_date.strftime("%Y-%m-%d"), symptoms, diagnosis, treatment))
                visit_id = c.lastrowid
                
                balance = cost - paid
                c.execute('''
                    INSERT INTO billing (visit_id, treatment_cost, amount_paid, balance)
                    VALUES (?, ?, ?, ?)
                ''', (visit_id, cost, paid, balance))
                
                conn.commit()
                conn.close()
                st.success("Visit and billing recorded successfully!")
                st.rerun()

    with tab3:
        st.subheader("Edit Patient Information")
        with st.form("edit_patient_form"):
            new_name = st.text_input("Name *", value=p[1])
            new_age = st.number_input("Age", min_value=0, max_value=120, step=1, value=int(p[2]) if p[2] else 0)
            
            gender_options = ["Male", "Female", "Other"]
            gender_idx = gender_options.index(p[3]) if p[3] in gender_options else 0
            new_gender = st.selectbox("Gender", gender_options, index=gender_idx)
            
            new_phone = st.text_input("Phone", value=p[4] if p[4] else "")
            new_address = st.text_area("Address", value=p[5] if p[5] else "")
            
            update_btn = st.form_submit_button("Update Details")
            
            if update_btn:
                if not new_name.strip():
                    st.error("Name is required!")
                else:
                    run_query('''
                        UPDATE patients 
                        SET name=?, age=?, gender=?, phone=?, address=?
                        WHERE id=?
                    ''', (new_name, new_age, new_gender, new_phone, new_address, patient_id))
                    st.success("Patient details updated!")
                    st.rerun()
        
        st.markdown("---")
        st.subheader("Danger Zone")
        if st.button("🚨 Delete Patient"):
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM visits WHERE patient_id=?", (patient_id,))
            visits = c.fetchall()
            for v in visits:
                c.execute("DELETE FROM billing WHERE visit_id=?", (v[0],))
            c.execute("DELETE FROM visits WHERE patient_id=?", (patient_id,))
            c.execute("DELETE FROM patients WHERE id=?", (patient_id,))
            conn.commit()
            conn.close()
            st.success("Patient and all related records deleted.")
            st.rerun()

if __name__ == "__main__":
    main()
