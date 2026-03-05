import streamlit as st
import psutil

def tooltip_success(message: str):
    tooltip_html = f"""
    <style>
    .tooltip-success {{
      position: relative;
      display: inline-block;
      cursor: pointer;
    }}

    .tooltip-success .tooltiptext {{
      visibility: hidden;
      width: 200px;
      background-color: #555;
      color: #fff;
      text-align: center;
      border-radius: 6px;
      padding: 5px;
      position: absolute;
      z-index: 1;
      bottom: 125%;
      left: 50%;
      margin-left: -100px;
      opacity: 0;
      transition: opacity 0.3s;
    }}

    .tooltip-success:hover .tooltiptext {{
      visibility: visible;
      opacity: 1;
    }}

    .tooltip-success-icon {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background-color: #4CAF50;  /* Material Design Green */
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 16px;
    }}
    </style>

    <div class="tooltip-success">
      <div class="tooltip-success-icon">👍</div>
      <div class="tooltiptext">{message}</div>
    </div>
    """
    st.markdown(tooltip_html, unsafe_allow_html=True)

def tooltip_info(message: str):
    tooltip_html = f"""
    <style>
    .tooltip {{
      position: relative;
      display: inline-block;
      cursor: pointer;
    }}

    .tooltip .tooltiptext {{
      visibility: hidden;
      width: 200px;
      background-color: #555;
      color: #fff;
      text-align: center;
      border-radius: 6px;
      padding: 5px;
      position: absolute;
      z-index: 1;
      bottom: 125%;
      left: 50%;
      margin-left: -100px;
      opacity: 0;
      transition: opacity 0.3s;
    }}

    .tooltip:hover .tooltiptext {{
      visibility: visible;
      opacity: 1;
    }}

    .tooltip-icon {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background-color: #2196F3;  /* Changed from red to blue */
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 16px;
      font-style: italic;  /* Added italic style */
    }}
    </style>

    <div class="tooltip">
      <div class="tooltip-icon">?</div>  <!-- Changed from ! to ? -->
      <div class="tooltiptext">{message}</div>
    </div>
    """
    st.markdown(tooltip_html, unsafe_allow_html=True)

def tooltip_alert(message: str):
    tooltip_html = f"""
    <style>
    .tooltip-alert {{
      position: relative;
      display: inline-block;
      cursor: pointer;
    }}

    .tooltip-alert .tooltiptext {{
      visibility: hidden;
      width: 200px;
      background-color: #555;
      color: #fff;
      text-align: center;
      border-radius: 6px;
      padding: 5px;
      position: absolute;
      z-index: 1;
      bottom: 125%;
      left: 50%;
      margin-left: -100px;
      opacity: 0;
      transition: opacity 0.3s;
    }}

    .tooltip-alert:hover .tooltiptext {{
      visibility: visible;
      opacity: 1;
    }}

    .tooltip-alert-icon {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background-color: #f44336;  /* Material Design Red */
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 16px;
    }}
    </style>

    <div class="tooltip-alert">
      <div class="tooltip-alert-icon">!</div>
      <div class="tooltiptext">{message}</div>
    </div>
    """
    st.markdown(tooltip_html, unsafe_allow_html=True)


def get_memory_usage():
    process = psutil.Process()
    mem_info = process.memory_info()
    return mem_info.rss / (1024 ** 2)  # Convertir en Mo
