import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime

# --- SYSTEM CONFIGURATION & STATE ---
st.set_page_config(page_title="FastLane Health App", layout="wide")

if "refill_count" not in st.session_state:
    st.session_state.refill_count = 1
if "patient_data" not in st.session_state:
    st.session_state.patient_data = []

# --- TRIAGE & FRAUD PREVENTION ENGINE ---
def evaluate_health(hr, sys_bp, dia_bp, source):
    """Evaluates vitals and returns status and routing decision."""
    # 1. Enforce Mandatory Doctor Visit (Every 4th Refill)
    if st.session_state.refill_count % 4 == 0:
        return "Mandatory Visit", "Please see a doctor for your 4th refill physical checkup. Express code denied.", "warning"

    # 2. Trust Weights & Fraud Detection
    trust_score = {"Camera (rPPG)": 1.0, "Bluetooth": 1.0, "IoT Kiosk": 1.0, "HealthKit/Connect": 0.9, "Manual": 0.3}
    
    if source == "Manual":
        # Flag highly suspicious "perfect" manual entries
        if sys_bp == 120 and dia_bp == 80 and hr == 72:
            return "Flagged for Review", "Data appears synthetically perfect. Trust score low. Please use a verified device or see the clinic.", "error"
        if sys_bp % 10 == 0 and dia_bp % 10 == 0: # Rounded numbers
            st.warning("Manual entries detected with heavy rounding. Trust score reduced.")

    # 3. Clinical Triage Logic
    if hr > 120 or hr < 50 or sys_bp > 160 or dia_bp > 100:
        return "Danger - Alert Clinic", "Vitals indicate risk. The clinic has been alerted for urgent care.", "error"
    elif 60 <= hr <= 100 and 90 <= sys_bp <= 130 and 60 <= dia_bp <= 85:
        express_code = f"RX-{random.randint(1000,9999)}"
        return "Normal - Express Route", f"Vitals normal. Bypass the doctor. Pharmacy Code: {express_code}", "success"
    else:
        return "Review Required", "Vitals are borderline. A nurse will review your case shortly.", "warning"

def log_reading(source, hr, sys_bp, dia_bp, spo2=98):
    status, message, msg_type = evaluate_health(hr, sys_bp, dia_bp, source)
    
    record = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Source": source,
        "HR (bpm)": hr,
        "BP (mmHg)": f"{sys_bp}/{dia_bp}",
        "SpO2 (%)": spo2,
        "Refill #": st.session_state.refill_count,
        "Status": status
    }
    st.session_state.patient_data.append(record)
    st.session_state.refill_count += 1
    
    return status, message, msg_type

# --- UI LAYOUT ---
st.title("🏥 FastLane Health & Triage System")
st.markdown("Bypass the clinic queue. Secure, verified remote health checks.")

tab1, tab2, tab3, tab4 = st.tabs(["📱 Patient App", "🏪 Community Kiosk (IoT)", "🩺 Clinic Dashboard", "⚙️ Integrations"])

# --- TAB 1: PATIENT APP ---
with tab1:
    st.header("Take a Reading")
    method = st.radio("Select Measurement Method:", 
                      ["Camera (rPPG)", "Bluetooth Device", "Manual Entry"])

    if method == "Camera (rPPG)":
        st.info("rPPG uses your smartphone camera to detect micro-color changes in your skin to calculate heart and breathing rate.")
        camera_input = st.camera_input("Scan Face for 10 seconds")
        if camera_input:
            with st.spinner("Analyzing rPPG data from video stream..."):
                time.sleep(2) # Simulating OpenCV processing time
                # In production, OpenCV extracts the green channel mean over time and applies Fast Fourier Transform (FFT)
                hr = random.randint(65, 80) 
                sys_bp, dia_bp = random.randint(110, 125), random.randint(70, 80)
                status, msg, msg_type = log_reading(method, hr, sys_bp, dia_bp)
                getattr(st, msg_type)(f"**{status}**: {msg}")

    elif method == "Bluetooth Device":
        st.info("Ensure your smart BP cuff or Glucose monitor is paired via Bluetooth.")
        if st.button("Sync from Device"):
            with st.spinner("Connecting to BLE MAC Address..."):
                time.sleep(1.5)
                # Simulating incoming Bluetooth Low Energy (BLE) GATT characteristics
                hr, sys_bp, dia_bp = 75, 118, 78
                status, msg, msg_type = log_reading(method, hr, sys_bp, dia_bp)
                getattr(st, msg_type)(f"**{status}**: {msg}")

    elif method == "Manual Entry":
        st.warning("Manual entries have a lower trust score and are subject to fraud-detection algorithms.")
        col1, col2, col3 = st.columns(3)
        with col1:
            hr_input = st.number_input("Heart Rate", min_value=30, max_value=200, value=72)
        with col2:
            sys_input = st.number_input("Systolic (Top)", min_value=70, max_value=250, value=120)
        with col3:
            dia_input = st.number_input("Diastolic (Bottom)", min_value=40, max_value=150, value=80)
        
        if st.button("Submit Manual Data"):
            status, msg, msg_type = log_reading(method, hr_input, sys_input, dia_input)
            getattr(st, msg_type)(f"**{status}**: {msg}")

# --- TAB 2: COMMUNITY KIOSK (IoT) ---
with tab2:
    st.header("ESP32 Micro-Kiosk Simulator")
    st.markdown("Simulates payload received from a local pharmacy/surau kiosk via MQTT/HTTPS.")
    
    # Simulate a JSON payload that the ESP32 would send over POST or MQTT
    example_payload = {
        "device_id": "KIOSK-PERAK-001",
        "patient_qr": "USER-9942",
        "sensors": {
            "max30102_hr": 88,
            "max30102_spo2": 97,
            "uart_bp_sys": 135,
            "uart_bp_dia": 85
        }
    }
    st.json(example_payload)
    
    if st.button("Simulate Incoming Kiosk Payload"):
        status, msg, msg_type = log_reading("IoT Kiosk", 
                                            example_payload["sensors"]["max30102_hr"], 
                                            example_payload["sensors"]["uart_bp_sys"], 
                                            example_payload["sensors"]["uart_bp_dia"],
                                            example_payload["sensors"]["max30102_spo2"])
        st.success("Payload received and processed by Cloud Engine.")
        getattr(st, msg_type)(f"**{status}**: {msg}")

# --- TAB 3: CLINIC DASHBOARD ---
with tab3:
    st.header("Triage Database & Fraud Monitoring")
    if st.session_state.patient_data:
        df = pd.DataFrame(st.session_state.patient_data)
        
        # Color coding for clinic staff
        def highlight_danger(val):
            color = 'red' if 'Danger' in str(val) or 'Flagged' in str(val) else 'green' if 'Express' in str(val) else ''
            return f'color: {color}'
            
        st.dataframe(df.style.map(highlight_danger, subset=['Status']), use_container_width=True)
    else:
        st.info("No patient data logged yet.")

# --- TAB 4: OS AGGREGATORS ---
with tab4:
    st.header("Passive Background Logging")
    st.markdown("Integrations with Apple HealthKit & Google Health Connect")
    
    if st.button("Force Sync HealthKit / Health Connect"):
        with st.spinner("Calling OS APIs..."):
            time.sleep(1)
            st.success("Successfully imported passive data.")
            col1, col2 = st.columns(2)
            col1.metric("Average Resting HR (Last 7 Days)", "62 bpm", "-2 bpm")
            col2.metric("Average Sleep Duration", "7h 12m", "+15m")
            st.caption("This passive data increases the overall 'Trust Score' of the patient's profile.")
