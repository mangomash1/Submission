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

product_category = st.sidebar.multiselect('Product Category', categories_translation['product_category_name_english'].unique(), default=categories_translation['product_category_name_english'].unique())

start_datetime = pd.to_datetime(start_date.strftime('%Y-%m-%d 00:00:00'))
end_datetime = pd.to_datetime(end_date.strftime('%Y-%m-%d 23:59:59'))

# Filter orders by date range
filtered_orders = orders[(orders['order_purchase_timestamp'] >= start_datetime) & 
                         (orders['order_purchase_timestamp'] <= end_datetime)]

filtered_order_ids = filtered_orders['order_id'].to_list()

# Calculate daily transaction amount and transaction count
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

# Calculate mean, min, and max transaction amounts in the date range
transaction_amounts = daily_transaction_df['total_amount'].to_list()
mean_transaction = sum(transaction_amounts) / len(transaction_amounts)
min_transaction = min(transaction_amounts)
max_transaction = max(transaction_amounts)

# Calculate delta for total amount and transaction count
daily_transaction_df['amount_delta'] = daily_transaction_df['total_amount'].pct_change() * 100
daily_transaction_df['transaction_count_delta'] = daily_transaction_df['transaction_count'].pct_change() * 100

# Remove infinite values from deltas
daily_transaction_df.replace([float('inf'), float('-inf')], float('nan'), inplace=True)

# Calculate average delta for total amount and transaction count over the range
mean_amount_delta = daily_transaction_df['amount_delta'].mean()
mean_transaction_count_delta = daily_transaction_df['transaction_count_delta'].mean()

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["Sales and Revenue", "Product Category", "Top States for Product Categories"])

with tab1:
    st.header('Sales and Revenue')
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(label="Total Transactions", value=len(filtered_order_ids), delta=f'{mean_transaction_count_delta:.2f}%')
    with col2:
        st.metric(label="Total Transaction Amount", value=f'{sum(transaction_amounts):,.2f}', delta=f'{mean_amount_delta:.2f}%')
    
    # Display daily changes
    st.subheader("Sales and Revenue Growth")
    st.dataframe(daily_transaction_df[['date', 'total_amount', 'amount_delta', 'transaction_count', 'transaction_count_delta']])
    
    # Visualizations
    st.subheader('Visualizations')
    st.line_chart(daily_transaction_df[['date', 'transaction_count']].set_index('date'))
    st.line_chart(daily_transaction_df[['date', 'total_amount']].set_index('date'))

with tab2:
    st.header('Product Category Analysis')
    
    # Filter order_items to include only filtered order IDs
    filtered_order_items = order_items[order_items['order_id'].isin(filtered_order_ids)]
    
    # Merge order_items with products on 'product_id' to get 'product_category_name'
    merged_data = filtered_order_items.merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
    
    # Merge with categories_translation to get 'product_category_name_english'
    merged_data = merged_data.merge(categories_translation[['product_category_name', 'product_category_name_english']], on='product_category_name', how='left')
    
    # Apply product category filter
    filtered_merged_data = merged_data[merged_data['product_category_name_english'].isin(product_category)]
    
    # Calculate purchase counts for each product category in English
    category_counts = filtered_merged_data['product_category_name_english'].value_counts()
    
    # Sort category counts in descending order
    sorted_category_counts = category_counts.sort_values(ascending=False)

    # Metrics for product categories
    st.write(f"The most bought product category is '{sorted_category_counts.idxmax()}' with {sorted_category_counts.max()} purchases.")
    st.write(f"The least bought product category is '{sorted_category_counts.idxmin()}' with {sorted_category_counts.min()} purchases.")
    
    # Visualizations
    st.subheader('Visualizations')
    st.bar_chart(sorted_category_counts)

with tab3:
    st.header("Top 5 States for Each Product Category")

    # Merge orders with customers to get state information
    orders_customers = orders.merge(customers[['customer_id', 'customer_state']], on='customer_id', how='left')

    # Merge orders with order_items and products to get product category information
    orders_products = (orders_customers
                       .merge(order_items[['order_id', 'product_id']], on='order_id', how='left')
                       .merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
                       .merge(categories_translation, on='product_category_name', how='left'))

    # Filter data based on selected date range
    filtered_orders_products = orders_products[(orders_products['order_purchase_timestamp'] >= start_datetime) &
                                               (orders_products['order_purchase_timestamp'] <= end_datetime)]

    # Group by product category and state, then count the number of orders for each combination
    category_state_counts = (filtered_orders_products
                             .groupby(['product_category_name_english', 'customer_state'])
                             .size()
                             .reset_index(name='order_count'))

    # Sort by product category and order count to get the top 5 states for each product category
    top_states_per_category = category_state_counts.groupby('product_category_name_english').apply(
        lambda x: x.nlargest(5, 'order_count')).reset_index(drop=True)

    # Calculate total transactions per product category for percentage calculation
    category_totals = top_states_per_category.groupby('product_category_name_english')['order_count'].transform('sum')

    # Calculate percentage of total transactions for each state and product category
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
        height=1200,
        hover_data=['customer_state', 'order_count', 'percentage']
    )

    fig.update_layout(barmode='stack', xaxis_title="Percentage of Total Transactions")
    st.plotly_chart(fig, use_container_width=True)

    # Display matrix table of product category vs state (transaction counts)
    st.subheader("Metrics Table: Transaction Counts by State and Product Category")
    matrix_table = category_state_counts.pivot(index='customer_state', columns='product_category_name_english', values='order_count').fillna(0)
    st.dataframe(matrix_table)
