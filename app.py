import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# Path to cost data CSV
COST_DATA_FILE = "cost_data.csv"

# Load or initialize cost data
def load_cost_data():
    if os.path.exists(COST_DATA_FILE):
        return pd.read_csv(COST_DATA_FILE)
    else:
        return pd.DataFrame(columns=["Resource", "Category", "Internal Cost", "Billing Price"])

# Save cost data
def save_cost_data(df):
    df.to_csv(COST_DATA_FILE, index=False)

st.title("Cost Data Management")
cost_data = load_cost_data()

client_name = st.text_input("Enter Client's Name", value="Client")
project_name = st.text_input("Enter Project Name", value="Project")

st.subheader("Current Cost Data")
st.dataframe(cost_data, use_container_width=True)

# Add new entry
st.subheader("Add New Entry")
with st.form("add_entry_form"):
    resource = st.text_input("Resource")
    category = st.selectbox("Category", ["Course Creation", "Studio", "Talent", "Animation"])
    internal_cost = st.number_input("Internal Cost", min_value=0.0, step=10.0)
    billing_price = st.number_input("Billing Price", min_value=0.0, step=10.0)
    submitted = st.form_submit_button("Add Entry")
    if submitted and resource:
        new_row = pd.DataFrame([[resource, category, internal_cost, billing_price]],
                               columns=["Resource", "Category", "Internal Cost", "Billing Price"])
        cost_data = pd.concat([cost_data, new_row], ignore_index=True)
        save_cost_data(cost_data)
        st.success(f"Added {resource} to cost data.")

# Edit or delete entries
st.subheader("Edit or Delete Entries")
if not cost_data.empty:
    selected_index = st.selectbox("Select entry to edit/delete", cost_data.index)
    selected_row = cost_data.loc[selected_index]

    with st.form("edit_entry_form"):
        edited_resource = st.text_input("Resource", selected_row["Resource"])
        edited_category = st.selectbox("Category", ["Course Creation", "Studio", "Talent", "Animation"],
                                       index=["Course Creation", "Studio", "Talent", "Animation"].index(selected_row["Category"]))
        edited_internal_cost = st.number_input("Internal Cost", value=float(selected_row["Internal Cost"]))
        edited_billing_price = st.number_input("Billing Price", value=float(selected_row["Billing Price"]))
        update = st.form_submit_button("Update Entry")
        delete = st.form_submit_button("Delete Entry")

        if update:
            cost_data.at[selected_index, "Resource"] = edited_resource
            cost_data.at[selected_index, "Category"] = edited_category
            cost_data.at[selected_index, "Internal Cost"] = edited_internal_cost
            cost_data.at[selected_index, "Billing Price"] = edited_billing_price
            save_cost_data(cost_data)
            st.success("Entry updated.")

        if delete:
            cost_data = cost_data.drop(index=selected_index).reset_index(drop=True)
            save_cost_data(cost_data)
            st.success("Entry deleted.")

# Live Cost Estimator
st.subheader("Live Cost Estimator")
estimate_data = []
if not cost_data.empty:
    estimator_category = st.selectbox("Select Category for Estimation", cost_data["Category"].unique())
    filtered_resources = cost_data[cost_data["Category"] == estimator_category]
    estimator_resource = st.selectbox("Select Resource", filtered_resources["Resource"].unique())
    quantity = st.number_input("Enter Units / Hours", min_value=0, step=1)

    selected_row = filtered_resources[filtered_resources["Resource"] == estimator_resource].iloc[0]
    selected_rate = selected_row["Billing Price"]
    total_estimate = selected_rate * quantity

    st.markdown(f"**Billing Rate:** ${selected_rate:.2f}")
    st.markdown(f"**Total Estimated Cost:** ${total_estimate:.2f}")

    estimate_data.append({
        "Resource": estimator_resource,
        "Category": estimator_category,
        "Units": quantity,
        "Billing Rate": selected_rate,
        "Total Estimated Cost": total_estimate
    })

# Internal Cost Breakdown
st.subheader("Internal Cost Breakdown")
if not cost_data.empty:
    st.markdown("### Estimated Costs Per Resource")

    units_map = {
        "SME": st.number_input("Number of Courses (SME)", min_value=0, value=1),
        "PM": st.number_input("Number of Courses (PM)", min_value=0, value=1),
        "Research & LO": st.number_input("Number of Courses (Research & LO)", min_value=0, value=1),
        "Coursewriting": st.number_input("Number of Courses (Coursewriting)", min_value=0, value=1),
        "Scripts": st.number_input("Number of Courses (Scriptwriting)", min_value=0, value=1),
        "Graphic Design": st.number_input("Number of Courses (Graphic Design)", min_value=0, value=1),
        "Studio Hire": st.number_input("Number of Filming Days (Studio Hire)", min_value=0, value=1),
        "Talent": st.number_input("Talent Days per Person (Total)", min_value=0, value=1),
        "Animation": st.number_input("Seconds of Animation", min_value=0, value=1)
    }

    breakdown_rows = []

    for resource in cost_data["Resource"].unique():
        row = cost_data[cost_data["Resource"] == resource].iloc[0]
        internal_rate = row["Internal Cost"]
        billing_rate = row["Billing Price"]
        category = row["Category"]

        if category == "Course Creation" and resource in units_map:
            units = units_map[resource]
        elif category == "Studio" and resource == "Studio Hire":
            units = units_map["Studio Hire"]
        elif category == "Talent":
            units = units_map["Talent"]
        elif category == "Animation":
            units = units_map["Animation"]
        else:
            continue

        total_internal = internal_rate * units
        breakdown_rows.append({
            "Resource": resource,
            "Internal Cost": internal_rate,
            "Units / Hours": units,
            "Total Internal Cost": total_internal,
            "Billing Price": billing_rate
        })

    internal_df = pd.DataFrame(breakdown_rows)
    st.dataframe(internal_df, use_container_width=True)

    # Export to Excel
    towrite = BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        internal_df.to_excel(writer, index=False, sheet_name='Cost Breakdown')
        if estimate_data:
            estimate_df = pd.DataFrame(estimate_data)
            estimate_df.to_excel(writer, index=False, sheet_name='Live Estimate')
        writer.save()

    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{client_name.replace(' ', '_')}_{project_name.replace(' ', '_')}_estimate_{today_str}.xlsx"
    st.download_button(
        label="📥 Download Breakdown as Excel",
        data=towrite.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
