import streamlit as st
import serial
import serial.tools.list_ports
import numpy as np
import pandas as pd
import joblib
import time
import os
from collections import deque

st.set_page_config(
    page_title="Live EMG RF + SVM",
    layout="wide"
)

st.title("Live EMG Classification Dashboard")
st.warning(
    "Experimental demonstration only. The uploaded training "
    "dataset is RNA sequencing data, not EMG data. Model outputs "
    "must not be interpreted as medical diagnoses."
)

# ------------------------------------------------
# MODEL FILES
# ------------------------------------------------

RF_FILE = "optimized_emg_rf.joblib"
SVM_FILE = "emg_svm_classifier.joblib"
SCALER_FILE = "emg_scaler(1).joblib"

@st.cache_resource
def load_models():
    rf = joblib.load(RF_FILE)
    svm = joblib.load(SVM_FILE)
    scaler = joblib.load(SCALER_FILE)
    return rf, svm, scaler

missing = [
    f for f in [RF_FILE, SVM_FILE, SCALER_FILE]
    if not os.path.exists(f)
]

if missing:
    st.error("Missing files: " + ", ".join(missing))
    st.stop()

try:
    rf_model, svm_model, scaler = load_models()
except Exception as e:
    st.error(f"Model loading error: {e}")
    st.stop()

if list(scaler.feature_names_in_) != [
    "MAV", "RMS", "Decrement_Ratio"
]:
    st.error("Unexpected scaler feature order.")
    st.stop()

st.success("Random Forest, SVM and scaler loaded.")

st.write("RF classes:", list(rf_model.classes_))
st.write("SVM classes:", list(svm_model.classes_))

# ------------------------------------------------
# SETTINGS
# ------------------------------------------------

SAMPLE_RATE = 250
WINDOW_SIZE = SAMPLE_RATE * 2

if "serial_connection" not in st.session_state:
    st.session_state.serial_connection = None

if "signal" not in st.session_state:
    st.session_state.signal = deque(maxlen=WINDOW_SIZE)

if "total_samples" not in st.session_state:
    st.session_state.total_samples = 0

# ------------------------------------------------
# SERIAL CONNECTION
# ------------------------------------------------

st.sidebar.header("ESP32 connection")

available_ports = [
    p.device for p in serial.tools.list_ports.comports()
]

selected_port = st.sidebar.selectbox(
    "Select ESP32 port",
    available_ports if available_ports else ["COM8"]
)

if st.sidebar.button("Connect ESP32"):
    try:
        if st.session_state.serial_connection is not None:
            st.session_state.serial_connection.close()

        st.session_state.serial_connection = serial.Serial(
            selected_port,
            115200,
            timeout=0.02
        )

        st.session_state.signal.clear()
        st.session_state.total_samples = 0

        st.sidebar.success("ESP32 connected")

    except Exception as e:
        st.sidebar.error(str(e))

if st.sidebar.button("Disconnect ESP32"):
    if st.session_state.serial_connection is not None:
        st.session_state.serial_connection.close()

    st.session_state.serial_connection = None
    st.sidebar.info("Disconnected")

# ------------------------------------------------
# FEATURE EXTRACTION
# ------------------------------------------------

def extract_features(signal):

    signal = np.asarray(signal, dtype=float)

    # Remove DC offset
    centered = signal - np.mean(signal)

    # Mean Absolute Value
    mav = np.mean(np.abs(centered))

    # Root Mean Square
    rms = np.sqrt(np.mean(centered ** 2))

    # PROVISIONAL decrement ratio:
    # RMS of second half divided by RMS of first half.
    # This formula is not confirmed against model training.
    middle = len(centered) // 2

    first = centered[:middle]
    second = centered[middle:]

    rms_first = np.sqrt(np.mean(first ** 2))
    rms_second = np.sqrt(np.mean(second ** 2))

    decrement_ratio = (
        rms_second / rms_first
        if rms_first > 1e-9 else 0.0
    )

    return mav, rms, decrement_ratio

# ------------------------------------------------
# LIVE DASHBOARD
# ------------------------------------------------

@st.fragment(run_every="250ms")
def live_dashboard():

    connection = st.session_state.serial_connection

    if connection is None or not connection.is_open:
        st.info("Connect ESP32 to start live monitoring.")
        return

    try:
        while connection.in_waiting:
            line = connection.readline().decode(
                "utf-8", errors="ignore"
            ).strip()

            if line == "EMG_STREAM_START":
                continue

            try:
                value = int(line)

                if 0 <= value <= 4095:
                    st.session_state.signal.append(value)
                    st.session_state.total_samples += 1

            except ValueError:
                continue

    except Exception as e:
        st.error(f"Serial error: {e}")
        return

    signal = np.array(st.session_state.signal)

    if len(signal) < WINDOW_SIZE:
        st.info(
            f"Collecting samples: {len(signal)}/{WINDOW_SIZE}"
        )
        return

    # Extract provisional features
    mav, rms, decrement_ratio = extract_features(signal)

    # Prepare model input in the scaler's expected order
    features = np.array([[
        mav,
        rms,
        decrement_ratio
    ]])

    # Scale features
    scaled_features = scaler.transform(features)

    # Predictions
    rf_prediction = rf_model.predict(scaled_features)[0]
    svm_prediction = svm_model.predict(scaled_features)[0]

    # Display features
    st.subheader("Live signal features")

    c1, c2, c3 = st.columns(3)

    c1.metric("MAV", f"{mav:.4f}")
    c2.metric("RMS", f"{rms:.4f}")
    c3.metric("Decrement Ratio", f"{decrement_ratio:.4f}")

    # Display waveform
    st.subheader("Live EMG waveform")

    chart = pd.DataFrame({
        "ADC reading": signal,
        "Centered signal": signal - np.mean(signal)
    })

    st.line_chart(chart)

    # Display model outputs
    st.subheader("Experimental model outputs")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Random Forest")
        st.metric("Model output", str(rf_prediction))

    with c2:
        st.markdown("### SVM")
        st.metric("Model output", str(svm_prediction))

    if rf_prediction == svm_prediction:
        st.info("Both models returned the same class.")
    else:
        st.warning("The models returned different classes.")

    st.write(
        "Total samples received:",
        st.session_state.total_samples
    )

    st.caption(
        "The feature extraction and model outputs are provisional. "
        "The decrement ratio is an assumed formula, not a validated "
        "clinical measurement."
    )

live_dashboard()
