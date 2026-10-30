import streamlit as st
import sys
import importlib.util
import importlib.metadata

st.title("MQTT Installation Test")

st.write("Python version:", sys.version)

try:
    version = importlib.metadata.version("paho-mqtt")
    st.success(f"paho-mqtt installed: {version}")
except Exception as e:
    st.error(f"Package not found: {e}")

spec = importlib.util.find_spec("paho")

if spec:
    st.success("Paho module found!")
else:
    st.error("Paho module NOT found!")
