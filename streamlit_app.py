import streamlit as st
import requests
import numpy as np
import json
from datetime import datetime
import os

st.set_page_config(page_title="Matrix Calculator (Streamlit)", layout="wide")

# Determine the API base URL based on the environment
# For local development, use localhost
# For deployment, replace with your public Flask API URL
API_BASE = "http://127.0.0.1:5000"

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Calculator", "History"])

if page == "Calculator":
    st.title("Matrix Calculator — Streamlit UI")
    st.write("Use the controls to build matrices, run operations (NumPy), and view history (stored by Flask).")
    
    left, right = st.columns([2, 1])

    def resize_matrix(mat, r, c):
        """
        Safely resizes or creates a matrix with a given number of rows and columns.
        """
        if not isinstance(mat, list) or len(mat) == 0:
            # Change initial values to int
            return [[0 for _ in range(c)] for _ in range(r)]
        
        while len(mat) < r:
            mat.append([0] * c)
        while len(mat) > r:
            mat.pop()
        
        for i in range(len(mat)):
            while len(mat[i]) < c:
                mat[i].append(0)
            while len(mat[i]) > c:
                mat[i].pop()
        return mat

    with left:
        st.subheader("Inputs")
        colA1, colA2 = st.columns(2)
        with colA1:
            rowsA = st.number_input("Rows (A)", min_value=1, max_value=10, value=2, key="rowsA")
        with colA2:
            colsA = st.number_input("Cols (A)", min_value=1, max_value=10, value=2, key="colsA")

        colB1, colB2 = st.columns(2)
        with colB1:
            rowsB = st.number_input("Rows (B)", min_value=1, max_value=10, value=2, key="rowsB")
        with colB2:
            colsB = st.number_input("Cols (B)", min_value=1, max_value=10, value=2, key="colsB")

        st.markdown("---")
        st.write("Edit matrix values:")

        st.write("Matrix A")
        if "A" not in st.session_state:
            st.session_state.A = [[0] * colsA for _ in range(rowsA)]
        st.session_state.A = resize_matrix(st.session_state.get("A", []), rowsA, colsA)

        for i in range(rowsA):
            cols = st.columns(colsA)
            for j in range(colsA):
                key = f"A-{i}-{j}"
                # Use step=1 and convert to int
                val = int(cols[j].number_input(f"A[{i+1}-{j+1}]", value=int(st.session_state.A[i][j]), key=key, step=1))
                st.session_state.A[i][j] = val

        st.write("Matrix B")
        if "B" not in st.session_state:
            st.session_state.B = [[0] * colsB for _ in range(rowsB)]
        st.session_state.B = resize_matrix(st.session_state.get("B", []), rowsB, colsB)

        for i in range(rowsB):
            cols = st.columns(colsB)
            for j in range(colsB):
                key = f"B-{i}-{j}"
                # Use step=1 and convert to int
                val = int(cols[j].number_input(f"B[{i+1}-{j+1}]", value=int(st.session_state.B[i][j]), key=key, step=1))
                st.session_state.B[i][j] = val

        st.markdown("---")
        st.subheader("Operations")
        op = st.radio("Choose operation", ("add","sub","mul","transposeA","transposeB"), index=0, horizontal=True)

        if st.button("Run"):
            payload = {"A": st.session_state.A, "B": st.session_state.B, "operation": op}
            try:
                resp = requests.post(f"{API_BASE}/calculate", json=payload, timeout=10)
                if resp.ok and resp.headers['Content-Type'].startswith('application/json'):
                    data = resp.json()
                    st.session_state.last_result = data["result"]
                    st.session_state.last_id = data.get("id")
                    st.session_state.last_time = data.get("time")
                    st.success("Operation successful — saved in history")
                else:
                    st.error(f"API returned a non-JSON or unsuccessful response. Status Code: {resp.status_code}. Response: {resp.text}")
            except Exception as e:
                st.error(f"Network/API error: {e}")

    with right:
        st.subheader("Result")
        if "last_result" in st.session_state:
            last = st.session_state.last_result
            try:
                st.table(np.array(last))
            except Exception:
                st.text(str(last))
        else:
            st.write("_No result yet_")

elif page == "History":
    st.header("Operation History")
    
    st.sidebar.subheader("History Options")
    history_limit = st.sidebar.slider("Number of history entries to show", min_value=1, max_value=20, value=5)

    if st.sidebar.button("Refresh history"):
        st.rerun()

    history = []
    try:
        res = requests.get(f"{API_BASE}/history?limit={history_limit}", timeout=5)
        history = res.json() if res.ok else []
    except Exception as e:
        st.error(f"Cannot fetch history: {e}")
        history = []

    if history:
        for h in history:
            st.markdown(f"**#{h['id']} — {h['operation']}** _{h['time']}_")
            st.write("Matrix A:")
            try:
                st.table(np.array(h["A"]))
            except Exception:
                st.text(str(h["A"]))
            st.write("Matrix B:")
            try:
                st.table(np.array(h["B"]))
            except Exception:
                st.text(str(h["B"]))
            st.write("Result:")
            try:
                st.table(np.array(h["result"]))
            except Exception:
                st.text(str(h["result"]))

            cols = st.columns([1,1,1])
            try:
                ts = h["time"].split(".")[0]
                safe = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d_%H%M%S")
            except Exception:
                safe = str(h["time"]).replace(" ", "_").replace(":", "_").split(".")[0]
            saved_url = f"{API_BASE}/saved_pages/entry_{h['id']}_{safe}.html"

            if cols[0].button(f"Open {h['id']}", key=f"open-{h['id']}"):
                st.markdown(f"[Open saved page]({saved_url})")

            if cols[1].button(f"Export {h['id']}", key=f"export-{h['id']}"):
                try:
                    r = requests.get(f"{API_BASE}/export-entry/{h['id']}", timeout=5)
                    if r.ok:
                        data = r.json()
                        st.download_button(label="Download JSON", data=json.dumps(data, indent=2), file_name=f"entry_{h['id']}.json", mime="application/json")
                    else:
                        st.error("Cannot export")
                except Exception as e:
                    st.error(f"Export failed: {e}")

            if cols[2].button(f"Delete {h['id']}", key=f"del-{h['id']}"):
                try:
                    r = requests.post(f"{API_BASE}/delete-entry/{h['id']}", timeout=5)
                    if r.ok:
                        st.success("Deleted")
                        st.rerun()
                    else:
                        st.error("Delete failed")
                except Exception as e:
                    st.error(f"Delete failed: {e}")
    else:
        st.write("_No history entries yet_")