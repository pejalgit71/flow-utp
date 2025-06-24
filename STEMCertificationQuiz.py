# === Google Sheets Integration ===
import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import io
import zipfile
from datetime import datetime
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = "STEM Certification Data"


def get_gsheet_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    return gspread.authorize(creds)

def load_users_sheet():
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("users")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
        df["certified"] = pd.to_numeric(df["certified"], errors="coerce").fillna(0).astype(int)
    return df

def save_users_sheet(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("users")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def load_questions_sheet():
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("questions")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_questions_sheet(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("questions")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())



# === Original App Code (modified) ===
# stem_quiz_app/app.py

# --- CSV FILE PATHS ---


CERT_DIR = "certificates"

def generate_certificate(username, score):
    pdf = FPDF()
    pdf.add_page()

    # Logos (optional)
    if os.path.exists("MyFlowLab_logo.png"):
        pdf.image("MyFlowLab_logo.png", x=20, y=10, w=40)
    if os.path.exists("UTP_logo.png"):
        pdf.image("UTP_logo.png", x=150, y=10, w=40)

    pdf.ln(50)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Certificate of Completion", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, f"This certifies that", ln=True, align='C')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"{username}", ln=True, align='C')
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, "has successfully completed the", ln=True, align='C')
    pdf.cell(0, 10, "STEM Flowlab Certification Quiz", ln=True, align='C')
    pdf.cell(0, 10, f"with a score of {score}%", ln=True, align='C')
    pdf.ln(20)
    pdf.cell(0, 10, "Authorized by MyFlowLab and UTP", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%B %d, %Y')}", ln=True, align='C')

    os.makedirs("certificates", exist_ok=True)
    cert_path = f"certificates/{username}_certificate.pdf"
    pdf.output(cert_path)
    return cert_path


# --- HELPER FUNCTIONS ---
def load_users():
    try:
        df = load_users_sheet()
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
        df["certified"] = pd.to_numeric(df["certified"], errors="coerce").fillna(0).astype(int)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["username", "password", "score", "certified"])

def load_questions():
    try:
        return load_questions_sheet()
    except FileNotFoundError:
        return pd.DataFrame(columns=["question", "option_a", "option_b", "option_c", "option_d", "correct_answer"])

def save_questions(df):
    save_questions_sheet(df)

def add_question(question, option_a, option_b, option_c, option_d, correct_answer):
    df = load_questions_sheet()
    new_row = pd.DataFrame([{"question": question, "option_a": option_a, "option_b": option_b, "option_c": option_c, "option_d": option_d, "correct_answer": correct_answer}])
    df = pd.concat([df, new_row], ignore_index=True)
    save_questions_sheet(df)
    return True

def delete_question(index):
    df = load_questions_sheet()
    if 0 <= index < len(df):
        df = df.drop(index).reset_index(drop=True)
        save_questions_sheet(df)
        return True
    return False

def update_question(index, question, option_a, option_b, option_c, option_d, correct_answer):
    df = load_questions_sheet()
    if 0 <= index < len(df):
        df.loc[index] = [question, option_a, option_b, option_c, option_d, correct_answer]
        save_questions_sheet(df)
        return True
    return False

def calculate_score(answers, questions):
    """Calculate score as a percentage"""
    correct = 0
    for i, row in questions.iterrows():
        if answers.get(i) == row["correct_answer"].lower():
            correct += 1
    return int((correct / len(questions)) * 100)

# --- ADMIN QUESTION MANAGER ---
def admin_question_gui():
    st.subheader("🛠️ Manage Quiz Questions and 📊 Certified Users Report")
   
    from sheets_utils import load_users_sheet
    df = load_users_sheet()
    
    certified_users = df[df["certified"] == 1]
    
    if not certified_users.empty:
        st.dataframe(certified_users[["username", "score"]])
    
        if st.button("🎓 Generate All Certificates (ZIP)"):
            import zipfile
            import io
    
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as zipf:
                for _, row in certified_users.iterrows():
                    cert_path = generate_certificate(row["username"], row["score"])
                    zipf.write(cert_path, os.path.basename(cert_path))
    
            buffer.seek(0)
            st.download_button("📥 Download All Certificates", data=buffer, file_name="certificates.zip", mime="application/zip")
    else:
        st.info("No certified users yet.")

    admin_pass = st.text_input("Enter Admin Password", type="password")
    if admin_pass != "fladmin":
        st.warning("Access restricted. Please enter the correct admin password.")
        return

    with st.expander("➕ Add New Question"):
        with st.form("add_question_form"):
            q = st.text_area("Question")
            a = st.text_input("Option A")
            b = st.text_input("Option B")
            c = st.text_input("Option C")
            d = st.text_input("Option D")
            correct = st.selectbox("Correct Answer", ["a", "b", "c", "d"])
            if st.form_submit_button("Add Question"):
                if all([q, a, b, c, d, correct]):
                    add_question(q, a, b, c, d, correct)
                    st.success("Question added successfully!")
                else:
                    st.warning("Please complete all fields.")

    st.markdown("---")
    st.subheader("✏️ Edit Existing Questions")
    df = load_questions()
    if df.empty:
        st.info("No questions available.")
    else:
        for i, row in df.iterrows():
            with st.expander(f"Question {i+1}: {row['question'][:80]}"):
                with st.form(f"edit_form_{i}"):
                    q = st.text_area("Question", value=row["question"])
                    a = st.text_input("Option A", value=row["option_a"])
                    b = st.text_input("Option B", value=row["option_b"])
                    c = st.text_input("Option C", value=row["option_c"])
                    d = st.text_input("Option D", value=row["option_d"])
                    correct = st.selectbox("Correct Answer", ["a", "b", "c", "d"], index=["a", "b", "c", "d"].index(row["correct_answer"]))
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            update_question(i, q, a, b, c, d, correct)
                            st.success("Question updated!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Delete"):
                            delete_question(i)
                            st.success("Question deleted!")
                            st.rerun()
# --- MAIN APP ENTRY ---
def main():
    st.set_page_config(page_title="STEM Certification Quiz", layout="wide")

    st.title("STEM Flowlab-UTP Certification Quiz")

    if "username" not in st.session_state:
        st.session_state["username"] = ""
    st.sidebar.image("MyFLowlab.png")
    st.sidebar.image("UTP.png")
    menu = ["Login", "Sign Up"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Sign Up":
        st.subheader("Create Account")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        if st.button("Sign Up"):
            df = load_users()
            if new_user in df["username"].values:
                st.warning("Username already exists.")
            else:
                new_row = pd.DataFrame([[new_user, new_pass, 0, 0]], columns=["username", "password", "score", "certified"])
                df = pd.concat([df, new_row], ignore_index=True)
                save_users_sheet(df)
                st.success("Account created! Please login.")

    elif choice == "Login":
        st.subheader("Login")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            df = load_users_sheet()
            if user in df["username"].values and pw == df[df["username"] == user]["password"].values[0]:
                st.session_state["username"] = user
                st.success(f"Welcome, {user}!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

    # If user logged in
    if st.session_state["username"]:
        st.sidebar.markdown("---")
        st.sidebar.success(f"Logged in as: {st.session_state['username']}")
        if st.sidebar.button("Logout"):
            st.session_state["username"] = ""
            st.rerun()

        if st.session_state["username"] == "admin":
            admin_question_gui()
        else:
            st.subheader("🧪 STEM Quiz")

            questions = load_questions()
            if questions.empty:
                st.warning("No questions found. Please contact the admin.")
            else:
                with st.form("quiz_form"):
                    answers = {}
                    for i, row in questions.iterrows():
                        st.markdown(f"**Q{i+1}:** {row['question']}")
                        selected = st.radio(
                            label="",
                            options=[
                                f"a. {row['option_a']}",
                                f"b. {row['option_b']}",
                                f"c. {row['option_c']}",
                                f"d. {row['option_d']}"
                            ],
                            key=f"q_{i}"
                        )
                        answers[i] = selected[0].lower()
                        st.markdown("---")
        
                    submitted = st.form_submit_button("Submit Quiz")
        
                if submitted:
                    score = calculate_score(answers, questions)
                    st.success(f"Your score: {score}%")
        
                    # Update user's score
                    df = load_users_sheet()
                    df.loc[df["username"] == st.session_state["username"], "score"] = score
                    df.loc[df["username"] == st.session_state["username"], "certified"] = int(score >= 70)
                    save_users_sheet(df)
        
                    if score >= 70:
                        st.balloons()
                        st.success("Congratulations! You passed and are now certified.")
                        cert_path = generate_certificate(st.session_state["username"], score)
                        with open(cert_path, "rb") as f:
                            st.download_button("🎓 Download Your Certificate", f.read(), file_name=f"{st.session_state['username']}_certificate.pdf", mime="application/pdf")
                    else:
                        st.error("You did not pass. Try again later.")

if __name__ == "__main__":
    main()
