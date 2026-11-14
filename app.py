import pandas as pd
import streamlit as st
from supabase import Client, create_client

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Inventory Management System", page_icon="📦", layout="wide"
)


# --- SUPABASE CONNECTION ---
# Uses Streamlit Secrets so your API keys stay safe when uploaded to GitHub
@st.cache_resource
def init_connection():
  url = st.secrets["SUPABASE_URL"]
  key = st.secrets["SUPABASE_KEY"]
  return create_client(url, key)


supabase: Client = init_connection()


# --- DATABASE FUNCTIONS ---
def get_inventory():
  response = supabase.table("inventory").select("*").order("id").execute()
  return pd.DataFrame(response.data)


def add_item(sku, name, category, quantity, price, reorder_level):
  data = {
      "sku": sku,
      "name": name,
      "category": category,
      "quantity": quantity,
      "price": price,
      "reorder_level": reorder_level,
  }
  supabase.table("inventory").insert(data).execute()


def update_stock(item_id, new_quantity):
  supabase.table("inventory").update({"quantity": new_quantity}).eq(
      "id", item_id
  ).execute()


def delete_item(item_id):
  supabase.table("inventory").delete().eq("id", item_id).execute()


# --- DASHBOARD UI ---
st.title("📦 Inventory Management Dashboard")
st.markdown("Real-time cloud inventory tracker powered by Python & Supabase.")

# Fetch Data
df = get_inventory()

# --- TOP KPI METRICS ---
if not df.empty:
  total_items = len(df)
  total_stock = int(df["quantity"].sum())
  total_value = (df["quantity"] * df["price"]).sum()
  low_stock_count = len(df[df["quantity"] <= df["reorder_level"]])
else:
  total_items, total_stock, total_value, low_stock_count = 0, 0, 0.0, 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Unique SKUs", total_items)
col2.metric("Total Units in Stock", total_stock)
col3.metric("Total Inventory Value", f"₱{total_value:,.2f}")
col4.metric("Low Stock Alerts", low_stock_count, delta_color="inverse")

st.divider()

# --- SIDEBAR: ADD NEW ITEM ---
with st.sidebar:
  st.header("➕ Add New Product")
  with st.form("add_item_form", clear_on_submit=True):
    sku = st.text_input("SKU Code (e.g., ITM-001)")
    name = st.text_input("Product Name")
    category = st.selectbox(
        "Category",
        ["Electronics", "Hardware", "Peripherals", "Office Supplies", "Other"],
    )
    quantity = st.number_input("Initial Quantity", min_value=0, step=1)
    price = st.number_input("Unit Price (₱)", min_value=0.0, step=10.0)
    reorder_level = st.number_input(
        "Low Stock Alert Threshold", min_value=1, value=5, step=1
    )

    submitted = st.form_submit_button(
        "Add to Inventory", use_container_width=True
    )
    if submitted:
      clean_sku = sku.strip().upper()
      clean_name = name.strip()
      if not clean_sku or not clean_name:
        st.error("SKU and Product Name are required.")
      elif (
          not df.empty and clean_sku in df["sku"].str.strip().str.upper().values
      ):
        st.warning(
            f"SKU '{clean_sku}' already exists! Use the 'Update / Delete Stock'"
            " tab to add more stock."
        )
      else:
        try:
          add_item(
              clean_sku, clean_name, category, quantity, price, reorder_level
          )
          st.success(f"Added {clean_name} ({clean_sku})!")
          st.rerun()
        except Exception as e:
          st.error(f"Database error: {e}")

# --- MAIN AREA: INVENTORY TABLE & ACTIONS ---
tab1, tab2 = st.tabs(["📋 Live Inventory List", "⚙️ Update / Delete Stock"])

with tab1:
  if df.empty:
    st.info(
        "Your inventory is currently empty. Use the sidebar on the left to add"
        " your first item!"
    )
  else:
    # Search & Filter
    search_col, cat_col = st.columns([2, 1])
    search_query = search_col.text_input("🔍 Search by Product Name or SKU")
    selected_cat = cat_col.selectbox(
        "Filter by Category", ["All"] + list(df["category"].unique())
    )

    filtered_df = df.copy()
    if search_query:
      filtered_df = filtered_df[
          filtered_df["name"].str.contains(search_query, case=False, na=False)
          | filtered_df["sku"].str.contains(search_query, case=False, na=False)
      ]
    if selected_cat != "All":
      filtered_df = filtered_df[filtered_df["category"] == selected_cat]

    # Highlight low stock rows
    def highlight_low_stock(row):
      if row["quantity"] <= row["reorder_level"]:
        return ["background-color: #ffcccc; color: #900000"] * len(row)
      return [""] * len(row)

    st.dataframe(
        filtered_df.style.apply(highlight_low_stock, axis=1),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
  if df.empty:
    st.warning("No items available to modify.")
  else:
    st.subheader("Adjust Stock or Remove Product")
    item_options = {
        f"{row['sku']} - {row['name']} (Current: {row['quantity']})": row
        for _, row in df.iterrows()
    }
    selected_label = st.selectbox("Select Item", list(item_options.keys()))
    selected_item = item_options[selected_label]

    c1, c2 = st.columns(2)
    with c1:
      new_qty = st.number_input(
          "New Stock Quantity",
          min_value=0,
          value=int(selected_item["quantity"]),
          step=1,
      )
      if st.button("Update Stock", type="primary"):
        update_stock(selected_item["id"], new_qty)
        st.success("Stock updated!")
        st.rerun()
    with c2:
      st.write("")
      st.write("")
      if st.button("🗑️ Delete Item Permanently"):
        delete_item(selected_item["id"])
        st.warning("Item deleted.")
        st.rerun()
