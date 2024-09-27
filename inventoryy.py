import streamlit as st
import pandas as pd
import openai
from datetime import datetime
import json
import uuid

# OpenAI API Key
#OPEN_API_KEY = "s-proj-thQ5-8EiGewCXd2h0Iyx5ueJoS3xMHlrdEaCx1p0rXrmID_vsUTSIIBfb8fLgiu8ALk_y2IpuYT3BlbkFJy0lX_tVr9ZASgYYuQFOe7K8feFWYJSE7trupHDGcCBw3yWr1vrJ7MQEabNmhglsPdE5mRFAewA"
openai.api_key = OPEN_API_KEY

# Generate a unique session ID for each session
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())  # Generate a unique UUID for the session

session_id = st.session_state["session_id"]

# File path for conversation history specific to this session
conversation_file = f"conversation_history_{session_id}.json"

# Load dataset from a CSV file
@st.cache_data
def load_data(file):
    return pd.read_csv(file)

# Save inventory to CSV
def save_inventory(inventory, filename="updated_medicine_inventory.csv"):
    inventory.to_csv(filename, index=False)
    st.success(f"Inventory saved to {filename}")

# Save conversation for the current session to a JSON file
def save_conversation(messages, filename=conversation_file):
    with open(filename, "w") as f:
        json.dump(messages, f)
    st.success(f"Conversation saved to {filename}")

# Load conversation history for the current session
def load_conversation(filename=conversation_file):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"role": "assistant", "content": "How can I assist you with your medicine inventory?"}]

# Function to check for expired medicines
def check_expired_medicines(inventory):
    today = datetime.today().strftime('%Y-%m-%d')
    expired_meds = inventory[inventory["Expiration Date"] < today]
    return expired_meds

# Function to add a new medicine to the inventory
def add_medicine(inventory, name, batch, expiration_date, quantity, dosage, prescription_required, price):
    new_medicine = pd.DataFrame({
        "Medicine Name": [name],
        "Batch Number": [batch],
        "Expiration Date": [expiration_date],
        "Quantity": [quantity],
        "Dosage": [dosage],
        "Prescription Required": [prescription_required],
        "Price": [price]
    })
    return pd.concat([inventory, new_medicine], ignore_index=True)

# Function to handle user queries for specific medicines
def handle_medicine_query(inventory, query):
    for medicine_name in inventory["Medicine Name"].unique():
        if medicine_name.lower() in query.lower():
            med_info = inventory[inventory["Medicine Name"].str.lower() == medicine_name.lower()]
            medicine_details = med_info.to_dict(orient='records')[0]
            return f"""
            Here are the details for {medicine_name}:
            - Dosage: {medicine_details['Dosage']}
            - Quantity: {medicine_details['Quantity']}
            - Expiration Date: {medicine_details['Expiration Date']}
            - Prescription Required: {medicine_details['Prescription Required']}
            - Price: {medicine_details['Price']}
            """
    return None

# Function to analyze customer purchase history and provide recommendations
def analyze_customer_purchases(customer_name, purchase_history):
    customer_data = purchase_history[purchase_history["Customer Name"].str.lower() == customer_name.lower()]
    if customer_data.empty:
        return f"No purchase history found for {customer_name}."
    
    frequent_purchases = customer_data["Medicine Name"].value_counts().head(5)
    return f"Top purchases for {customer_name}: \n" + "\n".join(f"{item}: {count} times" for item, count in frequent_purchases.items())

# Streamlit title
st.title("AI Inventory Management System")

# File uploader for the medicine inventory CSV
uploaded_file = st.file_uploader("Upload your medicine inventory CSV", type=["csv"])

# If a CSV file is uploaded, load the data into the session state
if uploaded_file is not None:
    st.session_state.inventory = load_data(uploaded_file)
    st.success("File uploaded successfully!")

    # Display the inventory as a DataFrame
    st.header("Current Medicine Inventory")
    if not st.session_state.inventory.empty:
        st.dataframe(st.session_state.inventory)

        # Check for expired medicines
        st.header("Expired Medicines")
        expired_meds = check_expired_medicines(st.session_state.inventory)
        if not expired_meds.empty:
            st.write("The following medicines have expired:")
            st.dataframe(expired_meds)
        else:
            st.write("No expired medicines.")

# Upload customer purchase history CSV
customer_file = st.file_uploader("Upload Customer Purchase History CSV", type=["csv"])

if customer_file is not None:
    st.session_state.purchase_history = load_data(customer_file)
    st.success("Customer purchase history uploaded successfully!")
    
    # Display customer purchase data
    st.header("Customer Purchase History Data")
    st.dataframe(st.session_state.purchase_history)  # Show the purchase history as a table

# Section for chatbot to handle customer purchase analysis
st.header("Customer Purchase Insights")
customer_name = st.text_input("Enter the customer's name:")
if st.button("Analyze Customer Purchases"):
    if "purchase_history" in st.session_state:
        analysis = analyze_customer_purchases(customer_name, st.session_state.purchase_history)
        st.write(analysis)
    else:
        st.write("Please upload the customer purchase history file first.")

# --- AI Chatbot ---
st.title("💬 Medicine Chatbot")

# Load conversation history for the current session
if "messages" not in st.session_state:
    st.session_state["messages"] = load_conversation()

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about medicine, prescriptions, or inventory"):
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # Chatbot checks the inventory for relevant information
    inventory_data = st.session_state.get("inventory")
    if inventory_data is not None:
        response_text = handle_medicine_query(inventory_data, prompt)
        if response_text is None:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=st.session_state["messages"]
            )
            response_text = response.choices[0].message["content"]

        st.session_state["messages"].append({"role": "assistant", "content": response_text})
    else:
        # No inventory data, fallback to OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=st.session_state["messages"]
        )
        reply = response.choices[0].message["content"]
        st.session_state["messages"].append({"role": "assistant", "content": reply})

    # Display reply
    with st.chat_message("assistant"):
        st.write(st.session_state["messages"][-1]["content"])

    # Save conversation for the current session
    save_conversation(st.session_state["messages"])
