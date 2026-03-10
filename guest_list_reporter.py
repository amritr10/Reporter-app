import streamlit as st
import pandas as pd
import io

# Set page configuration
st.set_page_config(page_title="Guest List Reporter", page_icon="\U0001F4CB", layout="wide")

# Set page configuration
st.set_page_config(page_title="Guest List Reporter", page_icon="\U0001F4CB", layout="wide")

st.title("\U0001F4CB Wedding Guest List Reporter")

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
            st.header("\U0001F4CA RSVP Summary & Tracking")

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
                    st.write(f"\U0001F465 **Expected:** {expected}")
                    st.write(f"\u2705 Accepted: {accepted}")
                    st.write(f"\u274C Declined: {declined}")
                    st.write(f"\u2753 Unanswered: {unanswered}")
            # --- Shuttle Bus Count ---
            st.markdown("---")
            sb_mask = df['tags'].str.contains("Shuttle Bus", case=False, na=False)
            sb_count = len(df[sb_mask])
            st.metric("\U0001F68C Shuttle Bus Requests", sb_count)

            # --- Party-Based Shuttle Transport Report ---
            transport_col = "would you like transportation to our wedding? (please note this event will be alcohol-free)"
            if transport_col in df.columns and 'party' in df.columns:
                shuttle_df = df.copy()
                shuttle_df['_transport_response'] = shuttle_df[transport_col].fillna("").astype(str).str.strip()
                shuttle_df['_transport_lower'] = shuttle_df['_transport_response'].str.lower()
                shuttle_df['_is_yes'] = shuttle_df['_transport_lower'].str.contains("yes", na=False)
                shuttle_df['_is_no'] = shuttle_df['_transport_lower'].str.contains("no", na=False)
                shuttle_df['_is_shuttle_tagged'] = shuttle_df['tags'].str.contains("Shuttle Bus", case=False, na=False)

                party_ids = shuttle_df['party'].fillna("").astype(str).str.strip()
                shuttle_df['_party_group'] = party_ids.where(
                    party_ids != "",
                    "unassigned_row_" + shuttle_df.index.astype(str)
                )
                shuttle_df['_party_display'] = party_ids.where(
                    party_ids != "",
                    "(No party ID)"
                )
                shuttle_df['_party_has_no'] = shuttle_df.groupby('_party_group')['_is_no'].transform('any')

                first_names = shuttle_df['first name'].fillna("").astype(str).str.strip() if 'first name' in shuttle_df.columns else pd.Series([""] * len(shuttle_df), index=shuttle_df.index)
                last_names = shuttle_df['last name'].fillna("").astype(str).str.strip() if 'last name' in shuttle_df.columns else pd.Series([""] * len(shuttle_df), index=shuttle_df.index)
                full_names = (first_names + " " + last_names).str.strip()
                shuttle_df['_member_name'] = full_names.where(full_names != "", "Unknown Guest")

                party_summary = (
                    shuttle_df
                    .groupby('_party_group', as_index=False)
                    .agg(
                        party_id=('_party_display', 'first'),
                        party_size=('_party_group', 'size'),
                        has_yes=('_is_yes', 'any'),
                        has_no=('_is_no', 'any'),
                        members=('_member_name', lambda s: ", ".join(s.astype(str).tolist())),
                        transport_responses=(
                            '_transport_response',
                            lambda s: " | ".join(
                                sorted({v for v in s.astype(str).tolist() if v.strip() != ""})
                            ) if any(v.strip() != "" for v in s.astype(str).tolist()) else "(blank)"
                        )
                    )
                )

                yes_parties = party_summary[party_summary['has_yes']].copy()
                yes_parties['counted_shuttle_people'] = yes_parties['party_size']
                party_based_total = int(yes_parties['counted_shuttle_people'].sum())
                st.metric("Shuttle Transport Needed (Party-Based)", party_based_total)

                if 'wedding rsvp' in shuttle_df.columns:
                    shuttle_df['_wedding_rsvp'] = shuttle_df['wedding rsvp'].fillna("").astype(str).str.lower().str.strip()
                    shuttle_df['_is_wedding_accepted'] = shuttle_df['_wedding_rsvp'].str.contains("accept", na=False)

                    expected_mask = (
                        shuttle_df['_is_shuttle_tagged']
                        & shuttle_df['_is_wedding_accepted']
                        & (shuttle_df['_is_yes'] | (shuttle_df['_transport_response'] == ""))
                        & ~shuttle_df['_party_has_no']
                    )
                    expected_shuttle_count = int(expected_mask.sum())
                    st.metric(
                        "Expected Shuttle Bus Count",
                        expected_shuttle_count,
                        help=(
                            "Count guest if Shuttle-tagged + Wedding Accepted + (Transport Yes or Blank), "
                            "then exclude the entire party if any member answered No."
                        )
                    )
                    expected_rows = shuttle_df[expected_mask].copy()
                    party_totals = (
                        shuttle_df
                        .groupby('_party_group', as_index=False)
                        .agg(
                            party_id=('_party_display', 'first'),
                            all_party_members=('_member_name', lambda s: ", ".join(s.astype(str).tolist()))
                        )
                    )
                    expected_parties = (
                        expected_rows
                        .groupby('_party_group', as_index=False)
                        .agg(
                            counted_shuttle_people=('_party_group', 'size'),
                            members=('_member_name', lambda s: ", ".join(s.astype(str).tolist()))
                        )
                    )
                    tagged_rows = shuttle_df[shuttle_df['_is_shuttle_tagged']].copy()
                    tagged_parties = (
                        tagged_rows
                        .groupby('_party_group', as_index=False)
                        .agg(
                            party_id=('_party_display', 'first'),
                            party_size=('_party_group', 'size'),
                            transport_responses=(
                                '_transport_response',
                                lambda s: " | ".join(
                                    sorted({v for v in s.astype(str).tolist() if v.strip() != ""})
                                ) if any(v.strip() != "" for v in s.astype(str).tolist()) else "(blank)"
                            )
                        )
                    )
                    shuttle_table_parties = (
                        tagged_parties
                        .merge(
                            party_totals[['_party_group', 'all_party_members']],
                            on='_party_group',
                            how='left'
                        )
                        .merge(
                            expected_parties[['_party_group', 'counted_shuttle_people', 'members']],
                            on='_party_group',
                            how='left'
                        )
                    )
                    shuttle_table_parties['counted_shuttle_people'] = (
                        shuttle_table_parties['counted_shuttle_people'].fillna(0).astype(int)
                    )
                    shuttle_table_parties['members'] = shuttle_table_parties['members'].fillna("(none)")
                    st.caption(
                        f"Included rows (sum of table Counted Shuttle People): {expected_shuttle_count}"
                    )
                else:
                    st.warning(
                        "Expected Shuttle Bus Count skipped. Missing required column(s): wedding rsvp"
                    )
                    tagged_rows = shuttle_df[shuttle_df['_is_shuttle_tagged']].copy()
                    shuttle_table_parties = (
                        tagged_rows
                        .groupby('_party_group', as_index=False)
                        .agg(
                            party_id=('_party_display', 'first'),
                            party_size=('_party_group', 'size'),
                            counted_shuttle_people=('_party_group', 'size'),
                            all_party_members=('_member_name', lambda s: ", ".join(s.astype(str).tolist())),
                            members=('_member_name', lambda s: ", ".join(s.astype(str).tolist())),
                            transport_responses=(
                                '_transport_response',
                                lambda s: " | ".join(
                                    sorted({v for v in s.astype(str).tolist() if v.strip() != ""})
                                ) if any(v.strip() != "" for v in s.astype(str).tolist()) else "(blank)"
                            )
                        )
                    )

                st.subheader("Shuttle Transport - Counted Parties")
                if shuttle_table_parties.empty:
                    st.info("No shuttle-tagged parties found.")
                else:
                    st.dataframe(
                        shuttle_table_parties[
                            ['party_id', 'party_size', 'counted_shuttle_people', 'all_party_members', 'members', 'transport_responses']
                        ].rename(
                            columns={
                                'party_id': 'Party',
                                'party_size': 'Party Size',
                                'counted_shuttle_people': 'Counted Shuttle People',
                                'all_party_members': 'All Party Members',
                                'members': 'Members',
                                'transport_responses': 'Transport Responses'
                            }
                        )
                    )

                in_question = party_summary[party_summary['has_yes'] & party_summary['has_no']].copy()
                st.subheader("Shuttle Transport - Parties In Question (Yes + No)")
                if in_question.empty:
                    st.success("No conflicting parties found (no party has both yes and no responses).")
                else:
                    st.dataframe(
                        in_question[
                            ['party_id', 'party_size', 'members', 'transport_responses']
                        ].rename(
                            columns={
                                'party_id': 'Party',
                                'party_size': 'Party Size',
                                'members': 'Members',
                                'transport_responses': 'Transport Responses'
                            }
                        )
                    )
            else:
                missing_cols = []
                if transport_col not in df.columns:
                    missing_cols.append(transport_col)
                if 'party' not in df.columns:
                    missing_cols.append('party')
                st.warning(
                    "Party-based shuttle report skipped. Missing required column(s): "
                    + ", ".join(missing_cols)
                )

            # --- Interactive Table ---
            st.markdown("---")
            st.subheader("Guest List Filter")
            
            # Multiselects
            selected_events = st.multiselect("Filter by Event Invitation", list(events_config.keys()))
            selected_statuses = st.multiselect("Filter by Response Status", ["Accepted", "Declined", "Unanswered"])
            
            # Filtering Logic
            filtered_df = df.copy()
            
            if selected_events or selected_statuses:
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
                
                # If user selects NOTHING, show everything? Yes.
                # If user selects Wedding, show Invited to Wedding.
                # If user selects Wedding + Accepted, show Invited to Wedding + Accepted Wedding.
                
                filtered_df = df[final_mask]

            st.dataframe(filtered_df)

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please upload a CSV file to begin.")

