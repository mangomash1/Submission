import pandas as pd
import streamlit as st
import plotly.express as px

# Read CSV files
customers = pd.read_csv("dashboard/customers_dataset.csv")
orders = pd.read_csv("dashboard/orders_dataset.csv")
products = pd.read_csv("dashboard/products_dataset.csv")
categories_translation = pd.read_csv("dashboard/product_category_name_translation.csv")
order_items = pd.read_csv("dashboard/order_items_dataset.csv")
payments = pd.read_csv("dashboard/order_payments_dataset.csv")

# Convert datetime columns in orders DataFrame
orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'], format='%Y-%m-%d %H:%M:%S')
orders['order_approved_at'] = pd.to_datetime(orders['order_approved_at'], format='%Y-%m-%d %H:%M:%S')
orders['order_delivered_carrier_date'] = pd.to_datetime(orders['order_delivered_carrier_date'], format='%Y-%m-%d %H:%M:%S')
orders['order_delivered_customer_date'] = pd.to_datetime(orders['order_delivered_customer_date'], format='%Y-%m-%d %H:%M:%S')
orders['order_estimated_delivery_date'] = pd.to_datetime(orders['order_estimated_delivery_date'], format='%Y-%m-%d %H:%M:%S')

st.set_page_config(
    page_title="E-Commerce Performance Dashboard",
    page_icon=":money:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit app
st.title("Sales and Product Category Analysis Dashboard")

# Sidebar filters
st.sidebar.header("Filters")
st.sidebar.subheader("Purchase Date")
start_date = st.sidebar.date_input('Start date', min_value=orders['order_purchase_timestamp'].min().date(), value=orders['order_purchase_timestamp'].min().date())
end_date = st.sidebar.date_input('End date', min_value=orders['order_purchase_timestamp'].min().date(), value=orders['order_purchase_timestamp'].max().date())

order_status = st.sidebar.multiselect('Order Status', orders['order_status'].unique(), default=orders['order_status'].unique())
product_category = st.sidebar.multiselect('Product Category', categories_translation['product_category_name_english'].unique(), default=categories_translation['product_category_name_english'].unique())
customer_city = st.sidebar.multiselect('Customer City', customers['customer_city'].unique(), default=customers['customer_city'].unique())
customer_state = st.sidebar.multiselect('Customer State', customers['customer_state'].unique(), default=customers['customer_state'].unique())

start_datetime = pd.to_datetime(start_date.strftime('%Y-%m-%d 00:00:00'))
end_datetime = pd.to_datetime(end_date.strftime('%Y-%m-%d 23:59:59'))

# Filter orders by date range, status, and customer location
filtered_orders = orders[(orders['order_purchase_timestamp'] >= start_datetime) & 
                         (orders['order_purchase_timestamp'] <= end_datetime) & 
                         (orders['order_status'].isin(order_status))]

filtered_customers = customers[(customers['customer_city'].isin(customer_city)) & 
                               (customers['customer_state'].isin(customer_state))]

filtered_orders = filtered_orders[filtered_orders['customer_id'].isin(filtered_customers['customer_id'])]

# Filter products by product category (global filter)
filtered_products = products[products['product_category_name'].isin(product_category)]
filtered_order_items = order_items[order_items['product_id'].isin(filtered_products['product_id'])]

# Filter merged data based on global product category filter
merged_data = filtered_order_items.merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
merged_data = merged_data.merge(categories_translation[['product_category_name', 'product_category_name_english']], on='product_category_name', how='left')
filtered_merged_data = merged_data[merged_data['product_category_name_english'].isin(product_category)]

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["Sales and Revenue", "Product Category", "Top States per Product Category"])

# Tab 1: Sales and Revenue Analysis
with tab1:
    st.header('Sales and Revenue')

    # Filter orders based on the global date filter
    daily_transaction_data = []
    for date, group in filtered_orders.groupby(filtered_orders['order_purchase_timestamp'].dt.date):
        daily_orders = group['order_id']
        daily_payment = payments[payments['order_id'].isin(daily_orders)]
        daily_total_amount = daily_payment['payment_value'].sum()
        daily_transaction_count = len(daily_orders)
        daily_transaction_data.append({
            'date': date,
            'total_amount': daily_total_amount,
            'transaction_count': daily_transaction_count
        })

    # Convert to DataFrame
    daily_transaction_df = pd.DataFrame(daily_transaction_data).sort_values(by='date')

    # Calculate daily deltas and other metrics
    transaction_amounts = daily_transaction_df['total_amount'].to_list()
    mean_transaction = sum(transaction_amounts) / len(transaction_amounts)
    min_transaction = min(transaction_amounts)
    max_transaction = max(transaction_amounts)

    daily_transaction_df['amount_delta'] = daily_transaction_df['total_amount'].pct_change() * 100
    daily_transaction_df['transaction_count_delta'] = daily_transaction_df['transaction_count'].pct_change() * 100
    daily_transaction_df.replace([float('inf'), float('-inf')], float('nan'), inplace=True)
    mean_amount_delta = daily_transaction_df['amount_delta'].mean()
    mean_transaction_count_delta = daily_transaction_df['transaction_count_delta'].mean()

    # Visualize sales and revenue data
    st.subheader('Sales and Revenue Growth')
    st.dataframe(daily_transaction_df[['date', 'total_amount', 'amount_delta', 'transaction_count', 'transaction_count_delta']])
    
    st.subheader('Visualizations')
    st.line_chart(daily_transaction_df[['date', 'transaction_count']].set_index('date'))
    st.line_chart(daily_transaction_df[['date', 'total_amount']].set_index('date'))

# Tab 2: Product Category Analysis
with tab2:
    st.header('Product Category Analysis')
    
    # Apply product category filter on merged data
    category_counts = filtered_merged_data['product_category_name_english'].value_counts()
    sorted_category_counts = category_counts.sort_values(ascending=False)
    
    most_bought_category = sorted_category_counts.idxmax()
    most_bought_category_count = sorted_category_counts.max()
    least_bought_category = sorted_category_counts.idxmin()
    least_bought_category_count = sorted_category_counts.min()

    # Metrics for product categories
    st.write(f"The most bought product category is '{most_bought_category}' with {most_bought_category_count} purchases.")
    st.write(f"The least bought product category is '{least_bought_category}' with {least_bought_category_count} purchases.")
    
    # Visualizations
    st.subheader('Visualizations')
    st.bar_chart(sorted_category_counts)

# Tab 3: Top 5 States per Product Category (Stacked Bar Chart)
with tab3:
    st.header("Top 5 States for Each Product Category (Stacked Bar Chart)")

    # Filter the merged data for top 5 states per product category
    category_state_counts = (filtered_merged_data
                             .groupby(['product_category_name_english', 'customer_state'])
                             .size()
                             .reset_index(name='order_count'))

    top_states_per_category = category_state_counts.groupby('product_category_name_english').apply(
        lambda x: x.nlargest(5, 'order_count')).reset_index(drop=True)

    # Calculate total transactions per product category for percentage calculation
    category_totals = top_states_per_category.groupby('product_category_name_english')['order_count'].transform('sum')
    top_states_per_category['percentage'] = top_states_per_category['order_count'] / category_totals * 100

    # Plot horizontal stacked bar chart
    fig = px.bar(
        top_states_per_category,
        x='percentage',
        y='product_category_name_english',
        color='customer_state',
        orientation='h',
        title='Top 5 States for Each Product Category',
        labels={'product_category_name_english': 'Product Category', 'percentage': 'Percentage of Total Transactions'},
        height=800,
        hover_data=['customer_state', 'order_count', 'percentage']
    )

    fig.update_layout(barmode='stack', xaxis_title="Percentage of Total Transactions")
    st.plotly_chart(fig, use_container_width=True)

    # Display matrix table of product category vs state (transaction counts)
    st.subheader("Metrics Table: Transaction Counts by State and Product Category")
    matrix_table = category_state_counts.pivot(index='customer_state', columns='product_category_name_english', values='order_count').fillna(0)
    st.dataframe(matrix_table)
