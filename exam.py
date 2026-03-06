import streamlit as st
import pandas as pd
import time
import datetime
import os

# Set page configuration
st.set_page_config(page_title="Exam Interface", layout="wide", initial_sidebar_state="expanded")

# Initialize Session State Variables
if "exam_started" not in st.session_state:
    st.session_state.exam_started = False
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "responses" not in st.session_state:
    st.session_state.responses = {} # Maps question index (0 to N-1) to selected option (A, B, C, D)
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "df" not in st.session_state:
    st.session_state.df = None
if "time_limit_mins" not in st.session_state:
    st.session_state.time_limit_mins = 0
if "exam_name" not in st.session_state:
    st.session_state.exam_name = "My Exam"
if "total_marks" not in st.session_state:
    st.session_state.total_marks = 100.0
if "negative_marking" not in st.session_state:
    st.session_state.negative_marking = 0.0

def submit_exam():
    """Handles the exam submission and generates the responses.csv"""
    st.session_state.exam_submitted = True
    
    # Compile results
    results = []
    num_questions = len(st.session_state.df)
    for i in range(num_questions):
        results.append({
            "Question Number": i + 1,
            "Response Marked": st.session_state.responses.get(i, "Unanswered")
        })
    
    # Create DataFrame and save locally
    results_df = pd.DataFrame(results)
    results_df.to_csv("responses.csv", index=False)
    st.session_state.results_df = results_df

@st.dialog("Confirm Submission")
def confirm_submit_dialog():
    """Shows a confirmation popup before final submission."""
    st.write("Are you sure you want to submit your exam?")
    
    # Show a warning if there are unanswered questions
    total_q = len(st.session_state.df)
    answered_q = len(st.session_state.responses)
    unanswered = total_q - answered_q
    
    if unanswered > 0:
        st.warning(f"⚠️ You still have {unanswered} unanswered question(s)!")
        
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Submit", type="primary", use_container_width=True):
            submit_exam()
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

def main():
    # Show custom exam name if the exam has started
    if st.session_state.exam_started and not st.session_state.exam_submitted:
        st.title(f"📝 {st.session_state.exam_name}")
    else:
        st.title("📝 Interactive Exam Application")

    # ----------------------------------------------------------------------
    # Setup Screen (Before Exam Starts)
    # ----------------------------------------------------------------------
    if not st.session_state.exam_started:
        st.write("### Exam Configuration")
        
        exam_name_input = st.text_input("Enter Exam Name", value="My Exam")
        uploaded_file = st.file_uploader("Upload your Questions CSV file", type=["csv"])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            time_limit = st.number_input("Set Exam Time Limit (in minutes)", min_value=1, value=30, step=1)
        with col2:
            total_marks_input = st.number_input("Total Marks for the Exam", min_value=1.0, value=100.0, step=1.0)
        with col3:
            negative_marking_input = st.number_input("Negative Marks per Incorrect Answer", min_value=0.0, value=0.0, step=0.25)
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                # Check for required columns
                required_cols = ['Question', 'Option A', 'Option B', 'Option C', 'Option D']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"CSV must contain the following columns: {', '.join(required_cols)}")
                else:
                    st.success(f"Successfully loaded {len(df)} questions!")
                    
                    if st.button("Start Exam", type="primary"):
                        st.session_state.df = df
                        st.session_state.exam_name = exam_name_input
                        st.session_state.time_limit_mins = time_limit
                        st.session_state.total_marks = total_marks_input
                        st.session_state.negative_marking = negative_marking_input
                        st.session_state.start_time = time.time()
                        st.session_state.exam_started = True
                        st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")
                
    # ----------------------------------------------------------------------
    # Post-Submission Screen (After Exam Ends)
    # ----------------------------------------------------------------------
    elif st.session_state.exam_submitted:
        st.success(f"✅ {st.session_state.exam_name} Submitted Successfully!")
        st.write("Your responses have been saved to `responses.csv`.")
        
        # Provide a download button for the generated CSV
        csv_data = st.session_state.results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Responses CSV",
            data=csv_data,
            file_name="responses.csv",
            mime="text/csv"
        )
        
        st.divider()
        st.write("### Evaluate Your Results")
        st.write("Upload the official Answer Key CSV to calculate your score based on the defined marking scheme.")
        
        answer_key_file = st.file_uploader("Upload Answer Key CSV", type=["csv"], key="answer_key_upload")
        
        if answer_key_file is not None:
            try:
                ak_df = pd.read_csv(answer_key_file)
                # Check if answer key has the expected columns
                if 'Question Number' in ak_df.columns and 'Correct Answer' in ak_df.columns:
                    # Merge the user's results with the answer key based on Question Number
                    eval_df = pd.merge(st.session_state.results_df, ak_df, on="Question Number", how="left")
                    
                    # Determine statuses
                    eval_df['Is Unanswered'] = eval_df['Response Marked'] == "Unanswered"
                    eval_df['Is Correct'] = eval_df['Response Marked'] == eval_df['Correct Answer']
                    eval_df['Is Incorrect'] = (~eval_df['Is Correct']) & (~eval_df['Is Unanswered'])
                    
                    # Replace True/False with visually appealing emojis/text
                    def get_status(row):
                        if row['Is Unanswered']: return "⚪ Unanswered"
                        if row['Is Correct']: return "✅ Correct"
                        return "❌ Incorrect"
                    
                    eval_df['Status'] = eval_df.apply(get_status, axis=1)
                    
                    # Calculate Scores
                    total_q = len(eval_df)
                    marks_per_q = st.session_state.total_marks / total_q
                    
                    correct_count = eval_df['Is Correct'].sum()
                    incorrect_count = eval_df['Is Incorrect'].sum()
                    unanswered_count = eval_df['Is Unanswered'].sum()
                    
                    final_score = (correct_count * marks_per_q) - (incorrect_count * st.session_state.negative_marking)
                    max_possible_score = st.session_state.total_marks
                    
                    # Display Metrics
                    score_col1, score_col2, score_col3, score_col4 = st.columns(4)
                    score_col1.metric(label="🏆 Final Score", value=f"{final_score:.2f} / {max_possible_score:.2f}", delta=f"{(final_score/max_possible_score)*100:.2f}%")
                    score_col2.metric(label="✅ Correct Answers", value=f"{correct_count}", delta=f"+{correct_count * marks_per_q:.2f} marks")
                    score_col3.metric(label="❌ Incorrect Answers", value=f"{incorrect_count}", delta=f"-{incorrect_count * st.session_state.negative_marking:.2f} marks")
                    score_col4.metric(label="⚪ Unanswered", value=f"{unanswered_count}")
                    
                    st.write(f"*Note: Each correct answer awards **{marks_per_q:.2f}** marks. Each incorrect answer deducts **{st.session_state.negative_marking:.2f}** marks.*")
                    
                    # Display the evaluated DataFrame
                    st.dataframe(eval_df[['Question Number', 'Response Marked', 'Correct Answer', 'Status']], use_container_width=True)
                else:
                    st.error("The Answer Key CSV must contain 'Question Number' and 'Correct Answer' columns.")
                    st.dataframe(st.session_state.results_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error evaluating answer key: {e}")
                st.dataframe(st.session_state.results_df, use_container_width=True)
        else:
            # Display just the raw responses if no answer key is uploaded yet
            st.dataframe(st.session_state.results_df, use_container_width=True)
        
        st.divider()
        if st.button("Start New Exam"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ----------------------------------------------------------------------
    # Exam Interface Screen
    # ----------------------------------------------------------------------
    else:
        df = st.session_state.df
        total_q = len(df)
        
        @st.fragment(run_every=1)
        def live_timer():
            elapsed_seconds = time.time() - st.session_state.start_time
            remaining_seconds = (st.session_state.time_limit_mins * 60) - elapsed_seconds
            
            # Note: Auto-submit skips the confirmation dialog
            if remaining_seconds <= 0:
                st.warning("⏳ Time is up! Auto-submitting your exam...")
                time.sleep(1)
                submit_exam()
                st.rerun()
            else:
                mins, secs = divmod(int(remaining_seconds), 60)
                st.subheader(f"{mins:02d}:{secs:02d} remaining")
                progress_val = max(0.0, min(1.0, remaining_seconds / (st.session_state.time_limit_mins * 60)))
                st.progress(progress_val)
        
        # --- Collapsible Sidebar (Navigation) ---
        with st.sidebar:
            st.header("⏱️ Timer")
            live_timer()
            
            st.divider()
            st.header("📊 Marking Scheme")
            marks_per_q = st.session_state.total_marks / total_q
            st.write(f"**Total Marks:** {st.session_state.total_marks:.2f}")
            st.write(f"**Correct Answer:** +{marks_per_q:.2f}")
            st.write(f"**Incorrect Answer:** -{st.session_state.negative_marking:.2f}")
            
            st.divider()
            st.header("📍 Navigation")
            st.write("Jump to a specific question:")
            
            # Create a grid of buttons for quick navigation
            cols_per_row = 4
            nav_cols = st.columns(cols_per_row)
            for i in range(total_q):
                col_idx = i % cols_per_row
                # Highlight answered questions with a different style or mark
                is_answered = i in st.session_state.responses
                btn_label = f"Q{i+1}" if not is_answered else f"✅ {i+1}"
                
                with nav_cols[col_idx]:
                    if st.button(btn_label, key=f"nav_{i}", help=f"Go to Question {i+1}"):
                        st.session_state.current_q = i
                        st.rerun()
                        
            st.divider()
            if st.button("Submit Exam Early", type="primary", use_container_width=True):
                confirm_submit_dialog()

        # --- Main Question Area ---
        current_idx = st.session_state.current_q
        row = df.iloc[current_idx]
        
        st.subheader(f"Question {current_idx + 1} of {total_q}")
        st.write(f"**{row['Question']}**")
        
        # Setup Options
        options_map = {
            "A": row['Option A'],
            "B": row['Option B'],
            "C": row['Option C'],
            "D": row['Option D']
        }
        
        # Determine current selection index for radio button
        selected_letter = st.session_state.responses.get(current_idx, None)
        index = 0
        if selected_letter == "A": index = 0
        elif selected_letter == "B": index = 1
        elif selected_letter == "C": index = 2
        elif selected_letter == "D": index = 3
        else: index = None  # None means unselected in recent Streamlit versions
        
        # Display Radio Buttons
        choice = st.radio(
            "Select your answer:",
            options=["A", "B", "C", "D"],
            format_func=lambda x: f"{x}. {options_map[x]}",
            index=index,
            key=f"radio_{current_idx}"
        )
        
        # Save selection to state
        if choice:
            st.session_state.responses[current_idx] = choice

        st.divider()
        
        # --- Footer: Next / Previous Controls ---
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if current_idx > 0:
                if st.button("⬅️ Previous"):
                    st.session_state.current_q -= 1
                    st.rerun()
        
        with col3:
            if current_idx < total_q - 1:
                if st.button("Next ➡️"):
                    st.session_state.current_q += 1
                    st.rerun()
            else:
                if st.button("Submit Exam", type="primary"):
                    confirm_submit_dialog()

if __name__ == "__main__":
    main()