import streamlit as st
import pandas as pd
import io

# Set page configuration
st.set_page_config(page_title="Guest List Reporter", page_icon="📋", layout="wide")

# Set page configuration
st.set_page_config(page_title="Guest List Reporter", page_icon="📋", layout="wide")

st.title("📋 Wedding Guest List Reporter")

# --- Sidebar Navigation & Upload ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Data Checks", "RSVP Summary"])

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Upload your Guest List CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # Load CSV
        df = pd.read_csv(uploaded_file)
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Ensure 'tags' column exists for logic, fill NA with empty string
        if 'tags' not in df.columns:
            df['tags'] = ""
        df['tags'] = df['tags'].fillna("").astype(str)

        st.sidebar.success("File uploaded successfully!")

        # --- PAGE 1: Data Checks ---
        if page == "Data Checks":
            st.markdown("""
            This section analyzes your wedding guest list CSV to find:
            1.  **Duplicate Guests** (based on First and Last Name)
            2.  **Missing RSVPs** (Guests who have not responded to ANY of the 4 events)
            """)
            
            # Display raw data preview
            with st.expander("Preview Raw Data"):
                st.dataframe(df.head())

            # --- 1. Duplicate Detection ---
            st.header("1. Duplicate Guests")
            
            required_name_cols = ['first name', 'last name']
            if all(col in df.columns for col in required_name_cols):
                duplicates = df[df.duplicated(subset=required_name_cols, keep=False)]
                
                if not duplicates.empty:
                    st.error(f"Found {len(duplicates)} duplicate entries (same First and Last Name).")
                    st.dataframe(duplicates)
                else:
                    st.info("No duplicates found based on First and Last Name.")
            else:
                st.warning(f"Could not check for duplicates. Missing columns: {set(required_name_cols) - set(df.columns)}")

            # --- 2. Missing RSVP Detection ---
            st.header("2. Missing RSVPs")
            
            rsvp_columns = ['wedding rsvp', 'reception rsvp', 'haldi rsvp', 'mehndi rsvp']
            existing_rsvp_cols = [col for col in rsvp_columns if col in df.columns]
            
            if len(existing_rsvp_cols) == 4:
                rsvp_df = df[existing_rsvp_cols].copy()
                rsvp_df = rsvp_df.replace(r'^\s*$', pd.NA, regex=True)
                
                # Missing from ALL events
                missing_rsvp_mask = rsvp_df.isna().all(axis=1)
                missing_rsvp_guests = df[missing_rsvp_mask].copy()
                
                count_missing = len(missing_rsvp_guests)
                
                st.metric("Guests yet to RSVP to ANY event", count_missing)
                
                if count_missing > 0:
                    st.subheader("List of guests to follow up with:")
                    
                    # Helper Functions
                    def clean_tags(tag_str):
                        if not isinstance(tag_str, str):
                            return ""
                        keywords = ["Ceremony", "Reception", "Mehndi", "Mehendi", "Haldi", "Shuttle Bus"]
                        found_tags = []
                        lower_tag = tag_str.lower()
                        for k in keywords:
                            if k.lower() in lower_tag:
                                # Normalize spelling for display
                                display_k = k
                                if k.lower() == "mehendi": display_k = "Mehndi" 
                                if display_k not in found_tags:
                                    found_tags.append(display_k)
                        return " | ".join(found_tags)

                    def create_whatsapp_msg(row):
                        first_name = str(row['first name']).strip() if pd.notna(row['first name']) else "Guest"
                        msg = (
                            f"Hello {first_name}, how are you? "
                            f"Could you please click the RSVP link https://withjoy.com/amrit-and-srilekha/rsvp "
                            f"and enter the password 'sriamrit2026'? "
                            f"Please enter your First and Last Name to unlock the RSVP form for you and/or your family. "
                            f"This will help us finalise numbers with our vendors. Thank you!"
                        )
                        return msg

                    # Apply enhancements
                    if 'tags' in missing_rsvp_guests.columns:
                        missing_rsvp_guests['Cleaned Tags'] = missing_rsvp_guests['tags'].apply(clean_tags)
                    
                    missing_rsvp_guests['WhatsApp Message'] = missing_rsvp_guests.apply(create_whatsapp_msg, axis=1)

                    # Select display columns
                    display_cols = ['first name', 'last name', 'phone number', 'WhatsApp Message']
                    if 'Cleaned Tags' in missing_rsvp_guests.columns:
                        display_cols.append('Cleaned Tags')
                    if 'email' in missing_rsvp_guests.columns:
                        display_cols.insert(3, 'email')

                    st.dataframe(missing_rsvp_guests[display_cols])
                else:
                    st.balloons()
                    st.success("Great news! Everyone has responded to at least one event.")
            else:
                st.error("Missing required RSVP columns for analysis.")

        # --- PAGE 2: RSVP Summary ---
        elif page == "RSVP Summary":
            st.header("📊 RSVP Summary & Tracking")

            # --- Logic Definitions ---
            events_config = {
                "Wedding": {
                    "rsvp_col": "wedding rsvp",
                    "tag_keywords": ["Wedding Party", "Ceremony"] 
                },
                "Reception": {
                    "rsvp_col": "reception rsvp",
                    "tag_keywords": ["Wedding Party", "Reception"]
                },
                "Haldi": {
                    "rsvp_col": "haldi rsvp",
                    "tag_keywords": ["Wedding Party", "Haldi"]
                },
                "Mehendi": {
                    "rsvp_col": "mehndi rsvp", # File has 'mehndi rsvp'
                    "tag_keywords": ["Wedding Party", "Mehendi", "Mehndi"] # Handle both spellings
                }
            }
            
            # --- Metrics Section ---
            cols = st.columns(4)
            for idx, (event_name, config) in enumerate(events_config.items()):
                with cols[idx]:
                    st.subheader(event_name)
                    
                    # 1. Calculate Total Invited (based on Tags)
                    # Pattern: match ANY keyword
                    tag_pattern = '|'.join([k for k in config['tag_keywords']])
                    invited_mask = df['tags'].str.contains(tag_pattern, case=False, na=False)
                    invited_df = df[invited_mask]
                    total_invited = len(invited_df)
                    
                    # 2. Calculate Responses based on Invited people only
                    if config['rsvp_col'] in df.columns:
                        # Clean column data
                        responses = invited_df[config['rsvp_col']].fillna("").str.lower().str.strip()
                        
                        accepted = responses[responses.str.contains("accept")].count()
                        declined = responses[responses.str.contains("decline")].count()
                        # Unanswered: anything that is NOT accept/decline or is empty
                        # Actually strict unanswered is empty.
                        # "Not answered with a value" -> Empty/Null
                        unanswered = responses[responses == ""].count()
                    else:
                        accepted = declined = unanswered = 0
                        st.warning(f"Col {config['rsvp_col']} missing")

                    # Expected = Total Invited - Declined
                    # (This assumes everyone else might come, including unanswered)
                    expected = total_invited - declined

                    st.write(f"**Total Invited:** {total_invited}")
                    st.write(f"👥 **Expected:** {expected}")
                    st.write(f"✅ Accepted: {accepted}")
                    st.write(f"❌ Declined: {declined}")
                    st.write(f"❓ Unanswered: {unanswered}")

            # --- Shuttle Bus Count ---
            st.markdown("---")
            sb_cols = st.columns(2)
            with sb_cols[0]:
                sb_mask = df['tags'].str.contains("Shuttle Bus", case=False, na=False)
                sb_count = len(df[sb_mask])
                st.metric("🚌 Shuttle Bus Tagged", sb_count)

            with sb_cols[1]:
                transport_col = (
                    "would you like transportation to our wedding? "
                    "(please note this event will be alcohol-free)"
                )
                party_col = "party"

                if transport_col in df.columns and party_col in df.columns:
                    transport_yes = df[transport_col].fillna("").str.lower().str.strip()
                    transport_yes_mask = transport_yes.str.contains("^yes", regex=True)

                    party_series = df[party_col]
                    party_key = party_series.where(party_series.notna(), other=df.index.astype(str))

                    temp_df = df[[party_col]].copy()
                    temp_df["party_key"] = party_key
                    temp_df["transport_yes"] = transport_yes_mask

                    party_yes = temp_df.groupby("party_key")["transport_yes"].any()
                    potential_individuals = temp_df["party_key"].map(party_yes)
                    potential_count = int(potential_individuals.sum())

                    st.metric("🚌 Shuttle Bus Potential Individuals", potential_count)
                else:
                    missing_cols = [
                        col for col in [transport_col, party_col] if col not in df.columns
                    ]
                    st.warning(f"Missing columns for shuttle bus potential count: {missing_cols}")

            # --- Interactive Table ---
            st.markdown("---")
            st.subheader("Guest List Filter")
            
            # Multiselects
            selected_events = st.multiselect("Filter by Event Invitation", list(events_config.keys()))
            selected_statuses = st.multiselect("Filter by Response Status", ["Accepted", "Declined", "Unanswered"])
            show_shuttle_potential = st.checkbox("Only potential shuttle bus individuals")
            
            # Filtering Logic
            filtered_df = df.copy()
            
            if selected_events or selected_statuses or show_shuttle_potential:
                # We need to filter rows based on OR logic within categories, but usually AND between categories?
                # User said: "OR type filtering where I can click on any event or by responses"
                # If I select Wedding and Reception -> Invited to Wedding OR Reception?
                # If I select Accepted -> Accepted (for that event?)
                
                # Let's build a mask for events
                event_mask = pd.Series([False] * len(df))
                if selected_events:
                    for e in selected_events:
                        keywords = events_config[e]['tag_keywords']
                        patt = '|'.join(keywords)
                        event_mask |= df['tags'].str.contains(patt, case=False, na=False)
                else:
                    event_mask = pd.Series([True] * len(df)) # If no event selected, assume all valid for status check?
                                                             # Or show all? Let's show all if nothing selected.

                # Mask for statuses
                # This is tricky because status is dependent on Event. 
                # If I select "Accepted", checking "Accepted" for WHICH event?
                # Interpretation: If an Event is selected (e.g. Wedding), show people who Accepted Wedding.
                # If Multiple events (Wedding, Haldi), show people who Accepted Wedding OR Accepted Haldi?
                # Use Global 'OR' logic across everything seems to be the request "OR type filtering".
                # But "Invited to Wedding" and "Accepted" are different dimensions.
                # Let's try: Guest is included if (Invited to Selected Events) AND (Has Selected Status in those events).
                
                status_mask = pd.Series([False] * len(df))
                
                if selected_statuses:
                    # Check status only for the selected events (or all events if none selected)
                    events_to_check = selected_events if selected_events else list(events_config.keys())
                    
                    for e in events_to_check:
                        col = events_config[e]['rsvp_col']
                        if col in df.columns:
                            col_vals = df[col].fillna("").str.lower().str.strip()
                            
                            if "Accepted" in selected_statuses:
                                status_mask |= col_vals.str.contains("accept")
                            if "Declined" in selected_statuses:
                                status_mask |= col_vals.str.contains("decline")
                            if "Unanswered" in selected_statuses:
                                status_mask |= (col_vals == "")
                else:
                    status_mask = pd.Series([True] * len(df))

                # Combine: If events selected, must matches event invitation AND status (if status selected)
                # If status not selected, just Event Invitation.
                # If event not selected, just Status (across any event).
                
                final_mask = pd.Series([True] * len(df))
                
                if selected_events:
                    final_mask &= event_mask
                if selected_statuses:
                    final_mask &= status_mask

                if show_shuttle_potential:
                    transport_col = (
                        "would you like transportation to our wedding? "
                        "(please note this event will be alcohol-free)"
                    )
                    party_col = "party"

                    if transport_col in df.columns and party_col in df.columns:
                        transport_yes = df[transport_col].fillna("").str.lower().str.strip()
                        transport_yes_mask = transport_yes.str.contains("^yes", regex=True)

                        party_series = df[party_col]
                        party_key = party_series.where(party_series.notna(), other=df.index.astype(str))

                        temp_df = df[[party_col]].copy()
                        temp_df["party_key"] = party_key
                        temp_df["transport_yes"] = transport_yes_mask

                        party_yes = temp_df.groupby("party_key")["transport_yes"].any()
                        if "wedding rsvp" in df.columns:
                            wedding_rsvp = df["wedding rsvp"].fillna("").str.lower().str.strip()
                            declined_mask = wedding_rsvp.str.contains("regretfully decline")
                        else:
                            declined_mask = pd.Series([False] * len(df))

                        shuttle_mask = temp_df["party_key"].map(party_yes) & ~declined_mask

                        final_mask &= shuttle_mask
                    else:
                        missing_cols = [
                            col for col in [transport_col, party_col] if col not in df.columns
                        ]
                        st.warning(
                            f"Missing columns for shuttle bus potential filter: {missing_cols}"
                        )
                
                # If user selects NOTHING, show everything? Yes.
                # If user selects Wedding, show Invited to Wedding.
                # If user selects Wedding + Accepted, show Invited to Wedding + Accepted Wedding.
                
                filtered_df = df[final_mask]

            st.dataframe(filtered_df)

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please upload a CSV file to begin.")
