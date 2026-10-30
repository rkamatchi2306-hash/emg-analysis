import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import numpy as np
import json
from collections import deque

st.set_page_config(
    page_title="Live EMG Monitor",
    page_icon="📈",
    layout="wide"
)

st.title("Live EMG Monitoring Dashboard")
st.caption("ESP32 + AD8232 + MQTT + Streamlit")

# MQTT connection
@st.cache_resource
def start_mqtt():

    data = deque(maxlen=2000)

    host = st.secrets["MQTT_HOST"]
    port = int(st.secrets["MQTT_PORT"])
    username = st.secrets["MQTT_USER"]
    password = st.secrets["MQTT_PASS"]
    topic = st.secrets["MQTT_TOPIC"]

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(topic)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())

            for value in payload["samples"]:
                data.append(int(value))

        except Exception:
            pass

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="Streamlit_EMG_Dashboard"
    )

    client.username_pw_set(username, password)
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(host, port, keepalive=60)
    client.loop_start()

    return data, client


try:
    emg_data, client = start_mqtt()

    st.success("MQTT dashboard connected")

except Exception as error:
    st.error("MQTT connection failed. Check your secrets and broker.")
    st.stop()


@st.fragment(run_every="1s")
def live_dashboard():

    samples = list(emg_data)

    if len(samples) < 2:
        st.info("Waiting for live EMG samples from ESP32...")
        return

    signal = np.array(samples, dtype=float)

    # Remove DC baseline for RMS calculation
    centered = signal - np.mean(signal)

    rms = np.sqrt(np.mean(centered ** 2))
    mav = np.mean(np.abs(centered))
    variance = np.var(centered)

    # Metrics
    c1, c2, c3 = st.columns(3)

    c1.metric("RMS", f"{rms:.2f}")
    c2.metric("MAV", f"{mav:.2f}")
    c3.metric("Variance", f"{variance:.2f}")

    # Waveform
    st.subheader("Live EMG Waveform")

    chart_data = pd.DataFrame({
        "ADC Signal": signal
    })

    st.line_chart(chart_data, height=350)

    st.subheader("Processed Signal")

    processed_data = pd.DataFrame({
        "Centered Signal": centered
    })

    st.line_chart(processed_data, height=250)

    st.caption(
        f"Received samples: {len(samples)} | "
        "Target sampling rate: 250 Hz"
    )


live_dashboard()
