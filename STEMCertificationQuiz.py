# === STEM Certification Quiz App ===

import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime
import gspread
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
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
    df["certified"] = pd.to_numeric(df["certified"], errors="coerce").fillna(0).astype(int)
    df["attempts"] = pd.to_numeric(df["attempts"], errors="coerce").fillna(0).astype(int)
    return df

def save_users_sheet(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("users")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

def load_questions_sheet():
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("questions")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_questions_sheet(df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("questions")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

def load_candidate_list():
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("Certification candidate list")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df["STATUS"] = pd.to_numeric(df["STATUS"], errors="coerce").fillna(0).astype(int)
    return df

def update_candidate_list(new_df):
    gc = get_gsheet_client()
    sheet = gc.open(SHEET_NAME).worksheet("Certification candidate list")
    old_data = pd.DataFrame(sheet.get_all_records())
    combined = pd.concat([old_data, new_df], ignore_index=True).drop_duplicates(subset=["ACCESSCODE"])
    sheet.clear()
    sheet.update([combined.columns.values.tolist()] + combined.fillna("").values.tolist())

def generate_certificate(username, score):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("MyFLowlab.png"):
        pdf.image("MyFLowlab.png", x=20, y=10, w=40)
    if os.path.exists("UTP.png"):
        pdf.image("UTP.png", x=150, y=10, w=40)
    pdf.ln(50)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Certificate of Completion", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, "This certifies that", ln=True, align='C')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, username, ln=True, align='C')
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, "has successfully completed the", ln=True, align='C')
    pdf.cell(0, 10, "STEM Flowlab Certification Quiz", ln=True, align='C')
    pdf.cell(0, 10, f"with a score of {score}%", ln=True, align='C')
    pdf.ln(20)
    pdf.cell(0, 10, "Authorized by MyFlowLab and UTP", ln=True, align='C')
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%B %d, %Y')}", ln=True, align='C')
    os.makedirs("certificates", exist_ok=True)
    cert_path = f"certificates/{username}_certificate.pdf"
    pdf.output(cert_path)
    return cert_path

def calculate_score(answers, questions):
    correct = 0
    for i, row in questions.iterrows():
        if answers.get(i) == row["correct_answer"].lower():
            correct += 1
    return int((correct / len(questions)) * 100)

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
        access_code = st.text_input("Enter Access Code")
        if st.button("Sign Up"):
            user_df = load_users_sheet()
            candidate_df = load_candidate_list()
            matched = candidate_df[candidate_df["ACCESSCODE"] == access_code]
            if matched.empty:
                st.warning("Access code not found in the database.")
            elif matched.iloc[0]["STATUS"] != 1:
                st.error("Access code not yet activated. Please activate via Arduino first.")
            elif new_user in user_df["username"].values:
                st.warning("Username already exists.")
            else:
                new_row = pd.DataFrame([[new_user, new_pass, 0, 0, 0, access_code]], columns=["username", "password", "score", "certified", "attempts", "access_code"])
                user_df = pd.concat([user_df, new_row], ignore_index=True)
                save_users_sheet(user_df)
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

    if st.session_state["username"]:
        st.sidebar.markdown("---")
        st.sidebar.success(f"Logged in as: {st.session_state['username']}")
        if st.sidebar.button("Logout"):
            st.session_state["username"] = ""
            st.rerun()

        if st.session_state["username"] == "admin":
            st.subheader("Admin Panel")
            uploaded_file = st.file_uploader("Upload New Candidate List (Excel)", type=["xlsx"])
            if uploaded_file:
                new_df = pd.read_excel(uploaded_file, sheet_name="Certification candidate list")
                update_candidate_list(new_df)
                st.success("Candidate list updated.")
        else:
            st.subheader("🧪 STEM Quiz")
            questions = load_questions_sheet()
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
                    df = load_users_sheet()
                    user_row = df[df["username"] == st.session_state["username"]].index[0]
                    attempts = int(df.loc[user_row, "attempts"])

                    if attempts >= 3:
                        st.error("You have used all 3 attempts. Contact admin for further help.")
                    else:
                        score = calculate_score(answers, questions)
                        st.success(f"Your score: {score}%")
                        df.loc[user_row, "score"] = score
                        df.loc[user_row, "certified"] = int(score >= 70)
                        if score < 70:
                            df.loc[user_row, "attempts"] = attempts + 1
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
