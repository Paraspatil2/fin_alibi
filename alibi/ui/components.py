import streamlit as st

def status_chip(status: str) -> str:
    s_upper = status.upper()
    if s_upper in ["APPROVE", "APPROVED"]:
        return '<span class="pill pill-approve">Approved</span>'
    elif s_upper in ["PARTIAL_APPROVE", "PARTIAL"]:
        return '<span class="pill pill-partial">Partial Approve</span>'
    elif s_upper in ["REJECT", "REJECTED"]:
        return '<span class="pill pill-review">Rejected</span>'
    else:
        return '<span class="pill pill-review">Manual Review</span>'

def kpi_card(label: str, value: str):
    st.markdown(f"""
    <div class="card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def empty_state(title: str, subtitle: str):
    st.markdown(f"""
    <div class="card" style="text-align: center; padding: 3rem;">
        <h3 style="color: #f8fafc; margin-bottom: 0.5rem;">{title}</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)
