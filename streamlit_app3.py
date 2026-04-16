import streamlit as st
import json
from pathlib import Path
from prompts import get_system_prompt, build_generation_direct_prompt

st.set_page_config(
    page_title="IPO Bot v2 - Style Profile Edition",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- 样式 ----------
st.markdown("""
<style>
.hero-card { padding
