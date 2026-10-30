
import streamlit as st
import streamlit.components.v1 as components
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import urllib.parse
import time
from collections import deque

st.set_page_config(
    page_title="Live EMG Monitoring",
    layout="wide"
)

st.title("Live EMG Monitoring System")

# Shared signal storage
if "emg_data" not in st.session_state:
    st.session_state.emg_data = []

st.info("Live EMG monitoring dashboard")

st.warning(
    "This is a demonstration receiver. "
    "A separate HTTP receiver service is required "
    "to accept ESP32 requests."
)

st.write("ESP32 sends samples to the receiver; "
         "the dashboard displays the received signal.")

st.subheader("Live EMG Signal")

placeholder = st.empty()

if st.button("Refresh Waveform"):
    st.rerun()

st.caption(
    "For Streamlit Cloud, deploy the receiver separately "
    "or use an MQTT broker. Streamlit Cloud does not expose "
    "a normal inbound HTTP endpoint for ESP32 requests."
)
