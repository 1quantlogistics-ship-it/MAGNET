"""
MAGNET Streamlit Dashboard
===========================

Web interface for MAGNET multi-agent naval design system.
Runs on port 8501.

From Operations Guide:
- Chat interface for design input
- Status display for system state
- Design visualization
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
API_URL = "http://localhost:8002"

st.set_page_config(
    page_title="MAGNET Naval Design",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fetch_status() -> Optional[Dict[str, Any]]:
    """Fetch system status from API."""
    try:
        response = requests.get(f"{API_URL}/status", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def fetch_design() -> Optional[Dict[str, Any]]:
    """Fetch current design from API."""
    try:
        response = requests.get(f"{API_URL}/design", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def send_chat(message: str) -> Optional[Dict[str, Any]]:
    """Send chat message to API."""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"message": message},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error sending message: {e}")
        return None


def validate_design() -> Optional[Dict[str, Any]]:
    """Validate current design."""
    try:
        response = requests.post(
            f"{API_URL}/validate",
            json={"validate_all": True},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


# Sidebar - System Status
with st.sidebar:
    st.header("System Status")

    status = fetch_status()

    if status:
        st.success(f"Status: {status.get('status', 'unknown')}")
        st.info(f"Phase: {status.get('current_phase', 'unknown')}")
        st.metric("Design Iteration", status.get("design_iteration", 0))
        st.metric("Phase Iteration", status.get("phase_iteration", 0))

        active_agents = status.get("active_agents", [])
        if active_agents:
            st.caption("Active Agents:")
            for agent in active_agents:
                st.text(f"  • {agent}")
    else:
        st.error("API Not Connected")
        st.caption(f"Ensure API is running at {API_URL}")

    st.divider()

    # Validate button
    if st.button("Validate Design", use_container_width=True):
        validation = validate_design()
        if validation:
            if validation.get("valid"):
                st.success("Design Valid")
            else:
                st.error("Validation Failed")
            with st.expander("Details"):
                st.json(validation)

    # Refresh button
    if st.button("Refresh", use_container_width=True):
        st.rerun()


# Main content
st.title("MAGNET Naval Design System")
st.caption("Multi-Agent Guided Naval Engineering Testbed")

# Chat interface
st.header("Design Chat")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Describe your design requirements..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to API
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            response = send_chat(prompt)

        if response:
            agent = response.get("agent", "system")
            content = response.get("response", "No response")
            confidence = response.get("confidence", 0)

            # Format response
            formatted_response = f"**[{agent}]** {content}\n\n_Confidence: {confidence:.0%}_"

            # Show concerns if any
            concerns = response.get("concerns", [])
            if concerns:
                formatted_response += "\n\n**Concerns:**\n"
                for concern in concerns:
                    formatted_response += f"- {concern}\n"

            st.markdown(formatted_response)
            st.session_state.messages.append({
                "role": "assistant",
                "content": formatted_response,
            })
        else:
            st.error("Failed to get response from API")

st.divider()

# Design State Display
st.header("Current Design State")

design = fetch_design()

if design:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Mission")
        mission = design.get("mission")
        if mission:
            st.json(mission)
        else:
            st.info("No mission defined")

    with col2:
        st.subheader("Hull Parameters")
        hull = design.get("hull_params")
        if hull:
            # Key metrics
            if "length_overall" in hull:
                st.metric("LOA", f"{hull['length_overall']:.1f} m")
            if "beam" in hull:
                st.metric("Beam", f"{hull['beam']:.1f} m")
            if "displacement_tonnes" in hull:
                st.metric("Displacement", f"{hull['displacement_tonnes']:.0f} t")

            with st.expander("Full Details"):
                st.json(hull)
        else:
            st.info("No hull parameters defined")

    with col3:
        st.subheader("Stability")
        stability = design.get("stability_results")
        if stability:
            if "GM" in stability:
                st.metric("GM", f"{stability['GM']:.3f} m")
            if "imo_criteria_passed" in stability:
                if stability["imo_criteria_passed"]:
                    st.success("IMO Criteria: PASSED")
                else:
                    st.error("IMO Criteria: FAILED")

            with st.expander("Full Details"):
                st.json(stability)
        else:
            st.info("No stability results")

    # Second row for weight and propulsion
    col4, col5 = st.columns(2)

    with col4:
        st.subheader("Weight Estimate")
        weight = design.get("weight_estimate")
        if weight:
            if "lightship_weight_tonnes" in weight:
                st.metric("Lightship", f"{weight['lightship_weight_tonnes']:.1f} t")
            with st.expander("Details"):
                st.json(weight)
        else:
            st.info("No weight estimate")

    with col5:
        st.subheader("Phase & Iteration")
        st.info(f"Phase: {design.get('phase', 'unknown')}")
        st.info(f"Iteration: {design.get('iteration', 0)}")

else:
    st.warning("Could not fetch design state. Ensure API is running.")

# Footer
st.divider()
st.caption(f"MAGNET v1.0 | Connected to {API_URL}")
