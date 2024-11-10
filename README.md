conda create --name main-ds python=3.9
conda activate main-ds
pip install -r dashboard/requirements.txt

streamlit run dashboard/ecommerce_dashboard.py
 
