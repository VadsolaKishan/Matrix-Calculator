import streamlit as st
import requests
import numpy as np
import json
from datetime import datetime
import os

st.set_page_config(page_title="Matrix Calculator (Streamlit)", layout="wide")

# Determine the API base URL based on the environment
API_BASE = "http://localhost:5000"

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Calculator", "History"])

def resize_matrix(mat, r, c):
    """
    Safely resizes or creates a matrix with a given number of rows and columns,
    filling new cells with random integer values as strings.
    """
    if not isinstance(mat, list) or len(mat) == 0:
        # Generate a new matrix with random integers and convert them to strings
        return np.random.randint(0, 10, size=(r, c)).astype(str).tolist()
    
    # Existing resizing logic (modified to use random values for new cells)
    new_mat = []
    for i in range(r):
        new_row = []
        for j in range(c):
            if i < len(mat) and j < len(mat[i]):
                new_row.append(mat[i][j])
            else:
                new_row.append(str(np.random.randint(0, 10)))
        new_mat.append(new_row)
    return new_mat

# Map internal operation names to display names
op_display_map = {
    "add": "Addition",
    "sub": "Subtraction",
    "mul": "Multiplication",
    "a2": "A$^2$",
    "b2": "B$^2$",
    "ta": "T(A)",
    "tb": "T(B)",
    "det-a": "$|A|$",
    "det-b": "$|B|$",
}


if page == "Calculator":
    st.title("Matrix Calculator")
    
    # Left column for inputs
    left_col = st.columns([1])[0]

    with left_col:
        st.subheader("Operation: ")
        
        op = st.radio(
            "Choose operation",
            ("Addition", "Subtraction", "Multiplication", "$|A|$", "$|B|$", "A$^2$", "B$^2$", "T(A)", "T(B)"),
            key="operation_selector",
            horizontal=True
        )
        
        st.markdown("---") 

        st.subheader("Matrix A")
        
        size_row_col1, size_row_col2 = st.columns([1,1])
        with size_row_col1:
            st.write("Size row:")
            rowsA = st.number_input("", min_value=1, max_value=5, value=3, key="rowsA_size", label_visibility="collapsed")
        
        with size_row_col2:
            st.write("Size column:")
            colsA = st.number_input("", min_value=1, max_value=5, value=3, key="colsA_size", label_visibility="collapsed")

        st.write("Matrix: A")
        if "A" not in st.session_state:
            st.session_state.A = resize_matrix([], rowsA, colsA)
        else:
            if len(st.session_state.A) != rowsA or (rowsA > 0 and len(st.session_state.A[0]) != colsA):
                st.session_state.A = resize_matrix(st.session_state.A, rowsA, colsA)

        for i in range(rowsA):
            cols = st.columns(colsA)
            for j in range(colsA):
                key = f"A-{i}-{j}"
                current_value = st.session_state.A[i][j]
                new_val = cols[j].text_input("", value=current_value, key=key)
                st.session_state.A[i][j] = new_val

        st.markdown("---") 

        # The conditional statement is removed to always display Matrix B
        st.subheader("Matrix B")
        
        size_row_col1_B, size_row_col2_B = st.columns([1,1])
        with size_row_col1_B:
            st.write("Size row:")
            rowsB = st.number_input("", min_value=1, max_value=5, value=3, key="rowsB_size", label_visibility="collapsed")
        with size_row_col2_B:
            st.write("Size column:")
            colsB = st.number_input("", min_value=1, max_value=5, value=3, key="colsB_size", label_visibility="collapsed")
        
        st.write("Matrix: B") 
        if "B" not in st.session_state:
            st.session_state.B = resize_matrix([], rowsB, colsB)
        else:
            if len(st.session_state.B) != rowsB or (rowsB > 0 and len(st.session_state.B[0]) != colsB):
                st.session_state.B = resize_matrix(st.session_state.B, rowsB, colsB)
        
        for i in range(rowsB):
            cols = st.columns(colsB)
            for j in range(colsB):
                key = f"B-{i}-{j}"
                current_value = st.session_state.B[i][j]
                new_val = cols[j].text_input("", value=current_value, key=key)
                st.session_state.B[i][j] = new_val
        
        st.markdown("---") 

    # Centering the Calculate button 
    cols = st.columns([1, 1, 1])
    with cols[1]:
        if st.button("Calculate", use_container_width=True):
            api_op_map = {
                "Addition": "add",
                "Subtraction": "sub",
                "Multiplication": "mul",
                "A$^2$": "a2",
                "B$^2$": "b2",
                "T(A)": "ta",
                "T(B)": "tb",
                "$|A|$": "det-a",
                "$|B|$": "det-b"
            }
            api_op = api_op_map.get(op)
            
            if api_op:
                payload = {"A": st.session_state.A, "B": st.session_state.B, "operation": api_op}
                try:
                    resp = requests.post(f"{API_BASE}/calculate", json=payload, timeout=10)
                    data = resp.json()
                    if resp.ok:
                        st.session_state.last_result = data["result"]
                        st.session_state.last_id = data.get("id")
                        st.session_state.last_time = data.get("time")
                        st.session_state.last_op_type = op # Store the operation type for display
                        st.success("Operation successful — saved in history")
                    else:
                        st.error(data.get("error","Unknown API error"))
                except Exception as e:
                    st.error(f"Network/API error: {e}")
            else:
                st.error("Invalid operation selected.")

    # Result section at the bottom
    st.markdown("---")
    
    st.subheader("Result:")
    if "last_result" in st.session_state:
        st.markdown("<h2 style='text-align:center; color:#00a3e0;'>YOUR INPUT</h2>", unsafe_allow_html=True)
        
        # Display inputs based on the operation type
        if st.session_state.last_op_type in ["Addition", "Subtraction", "Multiplication"]:
            input_cols = st.columns(2)
            with input_cols[0]:
                st.markdown("### Matrix A:")
                try:
                    st.table(np.array(st.session_state.A))
                except Exception:
                    st.text(str(st.session_state.A))
            with input_cols[1]:
                st.markdown("### Matrix B:")
                try:
                    st.table(np.array(st.session_state.B))
                except Exception:
                    st.text(str(st.session_state.B))
        elif st.session_state.last_op_type in ["A$^2$", "T(A)", "$|A|$"]:
            st.markdown("### Matrix A:")
            try:
                st.table(np.array(st.session_state.A))
            except Exception:
                st.text(str(st.session_state.A))
        elif st.session_state.last_op_type in ["B$^2$", "T(B)", "$|B|$"]:
            st.markdown("### Matrix B:")
            try:
                st.table(np.array(st.session_state.B))
            except Exception:
                st.text(str(st.session_state.B))
                
        # Display the operation and result
        st.markdown("<h2 style='text-align:center; color:#00a3e0;'>ANSWER</h2>", unsafe_allow_html=True)
        
        if isinstance(st.session_state.last_result, (float, int)):
            # If the result is a single number (determinant), write it directly
            st.markdown(f"### Determinant of {st.session_state.last_op_type.replace('$', '').replace('|', '')}")
            st.write(st.session_state.last_result)
        else:
            # Otherwise, it's a matrix and can be displayed as a table
            st.markdown(f"### Result of {st.session_state.last_op_type} operation")
            st.table(np.array(st.session_state.last_result))
            
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
            # Use the op_display_map to get the user-friendly name
            display_op = op_display_map.get(h['operation'], h['operation'])
            st.markdown(f"**#{h['id']} — {display_op}** _{h['time']}_")
            
            # Use the existence of matrix data to decide what to display
            if h["A"] and h["B"]:
                st.write("Matrix A:")
                st.table(np.array(h["A"]))
                st.write("Matrix B:")
                st.table(np.array(h["B"]))
            elif h["A"] and not h["B"]:
                st.write("Matrix A:")
                st.table(np.array(h["A"]))
            elif not h["A"] and h["B"]:
                st.write("Matrix B:")
                st.table(np.array(h["B"]))

            st.write("Result:")
            try:
                # Handle single float result from determinant in history as well
                if isinstance(h["result"], (float, int)):
                    st.write(h["result"])
                else:
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