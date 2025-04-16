import pandas as pd
import numpy as np
from utils import clean_description, format_date

def process_data(df):
    """
    Process a generic bank statement when the specific format is not recognized
    This is a fallback processor that tries to identify key columns based on common patterns
    """
    # Try to identify key columns by name patterns
    date_columns = [col for col in df.columns if any(key in str(col).lower() for key in ['tarih', 'date', 'datum'])]
    description_columns = [col for col in df.columns if any(key in str(col).lower() for key in ['açıklama', 'aciklama', 'description', 'detail', 'detay'])]
    amount_columns = [col for col in df.columns if any(key in str(col).lower() for key in ['tutar', 'amount', 'betrag', 'miktar'])]
    
    # Create a new dataframe
    processed_df = pd.DataFrame()
    
    # Process date column
    if date_columns:
        # Use the first identified date column
        processed_df['Tarih'] = df[date_columns[0]].apply(format_date)
    else:
        # Try to find a column that looks like a date
        for col in df.columns:
            if df[col].dtype == 'object' and pd.to_datetime(df[col], errors='coerce').notna().sum() > 0.5 * len(df):
                processed_df['Tarih'] = pd.to_datetime(df[col], errors='coerce').apply(lambda x: x.strftime('%d.%m.%Y') if not pd.isna(x) else '')
                break
        else:
            processed_df['Tarih'] = ""
    
    # Process description column
    if description_columns:
        # Use the first identified description column
        processed_df['Açıklama'] = df[description_columns[0]].apply(clean_description)
    else:
        # Try to find text-heavy columns
        text_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':
                avg_len = df[col].astype(str).str.len().mean()
                if avg_len > 15:  # Longer texts are likely descriptions
                    text_columns.append((col, avg_len))
        
        if text_columns:
            # Use the column with the longest average text
            text_columns.sort(key=lambda x: x[1], reverse=True)
            processed_df['Açıklama'] = df[text_columns[0][0]].apply(clean_description)
        else:
            processed_df['Açıklama'] = ""
    
    # Process amount column
    if amount_columns:
        # Use the first identified amount column
        amount_col = amount_columns[0]
        processed_df['Tutar'] = pd.to_numeric(df[amount_col].astype(str).str.replace(',', '.').str.replace('[^0-9.-]', '', regex=True), errors='coerce')
    else:
        # Try to find numeric columns that could be amounts
        numeric_columns = []
        for col in df.columns:
            try:
                # Convert to string, replace comma with dot, and remove currency symbols or spaces
                values = df[col].astype(str).str.replace(',', '.').str.replace('[^0-9.-]', '', regex=True)
                numeric_values = pd.to_numeric(values, errors='coerce')
                # If most values are valid numbers and have decent variance, it might be an amount column
                if numeric_values.notna().sum() > 0.5 * len(df) and numeric_values.var() > 0:
                    numeric_columns.append(col)
            except:
                continue
        
        if numeric_columns:
            # Use the first identified numeric column
            amount_col = numeric_columns[0]
            processed_df['Tutar'] = pd.to_numeric(df[amount_col].astype(str).str.replace(',', '.').str.replace('[^0-9.-]', '', regex=True), errors='coerce')
        else:
            processed_df['Tutar'] = 0
    
    # Set a default Dekont No (document number)
    processed_df['Dekont No'] = ""
    for col in df.columns:
        if any(key in str(col).lower() for key in ['dekont', 'belge', 'document', 'no', 'numara', 'number']):
            processed_df['Dekont No'] = df[col].astype(str)
            break
    
    # Calculate Borç and Alacak based on Tutar
    processed_df['Borç'] = processed_df['Tutar'].apply(lambda x: abs(x) if x < 0 else 0)
    processed_df['Alacak'] = processed_df['Tutar'].apply(lambda x: x if x > 0 else 0)
    
    return processed_df
