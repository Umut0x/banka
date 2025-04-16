import re
import pandas as pd
from datetime import datetime

def clean_description(description):
    """
    Clean description text by removing unnecessary punctuation and special characters
    """
    if pd.isna(description):
        return ""
    
    # Convert to string if it's not already
    description = str(description)
    
    # Türkçe karakterleri koruyarak tüm özel karakterleri ve noktalama işaretlerini kaldır
    turkish_chars = 'çÇğĞıİöÖşŞüÜ'
    # Sadece harfleri, rakamları ve Türkçe karakterleri tut, diğerlerini boşluğa çevir
    pattern = f'[^a-zA-Z0-9{turkish_chars} ]'
    description = re.sub(pattern, ' ', description)
    
    # Gereksiz boşlukları temizle (birden fazla boşluğu tek boşluğa dönüştür)
    description = re.sub(r'\s+', ' ', description)
    
    # Başlangıç ve sondaki boşlukları kaldır
    description = description.strip()
    
    return description

def format_date(date_str, for_grouping=False):
    """
    Format date strings to DD.MM.YYYY format
    If for_grouping is True, days will be grouped: 1-10 as 10, 11-20 as 20, 21-31 as 31
    """
    if pd.isna(date_str):
        return ""
    
    # Convert to string if it's not already
    if isinstance(date_str, datetime):
        date_obj = date_str
    else:
        # Eğer tarih ve saat birlikte geliyorsa, sadece tarih kısmını al
        # Örnek: 15/06/2025-14:36:26 -> 15/06/2025
        date_str = str(date_str).strip()
        
        # Tarih-saat ayırıcıları: tire (-), boşluk ( ), noktalı virgül (;)
        # İlk boşluk, tire veya noktalı virgül'e kadar olan kısmı al (tarih kısmı)
        for separator in ['-', ' ', ';']:
            if separator in date_str:
                date_parts = date_str.split(separator)
                date_str = date_parts[0].strip()
                # Örnek: Eğer 15/06/2025-14:36:26 gelirse, date_str şimdi 15/06/2025 olacak
                break
        
        # Saat bilgisi ':' içeriyorsa ve tarih kısmında ':' yoksa temizlik yapalım
        if ':' in date_str:
            # ":" işaretinden önceki kısmı al (muhtemelen tarih kısmı)
            date_str = date_str.split(':')[0]
        
        print(f"Temizlenmiş tarih: {date_str}")
        
        # Try different date formats
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d',
            '%d.%m.%Y', '%m/%d/%Y', '%d/%m/%y', '%Y%m%d',
            '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y'
        ]
        
        date_obj = None
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if date_obj is None:
            # If we can't parse the date, try to extract just the date part using regex
            import re
            date_match = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', date_str)
            if date_match:
                day, month, year = date_match.groups()
                # Yıl iki haneliyse 2000 ekle
                if len(year) == 2:
                    year = "20" + year
                
                try:
                    date_obj = datetime(int(year), int(month), int(day))
                except ValueError:
                    # Yine de başarısız olursa, olduğu gibi geri döndür
                    return date_str
            else:
                # Hiçbir şekilde tarih bulunamadıysa, olduğu gibi geri döndür
                return date_str
    
    # Eğer gruplama istenmiyorsa normal formatta dön
    if not for_grouping:
        return date_obj.strftime('%d.%m.%Y')
    
    # Gruplandırma için günü değiştir
    day = date_obj.day
    
    if 1 <= day <= 10:
        grouped_day = 10
    elif 11 <= day <= 20:
        grouped_day = 20
    else:  # 21-31
        grouped_day = 31
    
    # Yeni tarih oluştur (sadece gün değişti)
    return f"{grouped_day:02d}.{date_obj.month:02d}.{date_obj.year}"

def format_turkish_currency(amount):
    """
    Sayısal değeri Türk Lirası formatında biçimlendirir (1.000,00 TL)
    """
    if pd.isna(amount) or amount == 0:
        return ""
    
    # Noktadan sonra 2 basamak, binlik ayracı olarak nokta kullan
    formatted = "{:,.2f}".format(amount)
    
    # İngilizce formatından (1,234.56) Türkçe formatına (1.234,56) dönüştür
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    
    return formatted

def convert_to_target_format(df):
    """
    Convert the processed dataframe to the target format:
    Fiş Tarihi | Fiş Açıklama | Hesap Kodu | Evrak Tarihi | Detay Açıklama | Borç | Alacak | Miktar | Belge Türü | Para Birimi | Kur | Döviz Tutar
    
    Artık çıktı, bir sarı ayırıcı çizgi ile üst ve alt bölüme ayrılır.
    - Üst bölümde: Pozitif değerler Borç'a, negatif değerler Alacak'a yazılır (kırmızı rakamlar Alacak'ta)
    - Alt bölümde: Pozitif değerler Alacak'a, negatif değerler Borç'a yazılır (kırmızı rakamlar Borç'ta)
    """
    # Create the output dataframe with all required columns
    output_df = pd.DataFrame(columns=[
        'Fiş No', 'Fiş Tarihi', 'Fiş Açıklama', 'Hesap Kodu', 'Evrak No', 'Evrak Tarihi',
        'Detay Açıklama', 'Borç', 'Alacak', 'Miktar', 'Belge Türü', 'Para Birimi', 'Kur', 'Döviz Tutar',
        'is_separator'  # Bu sütun gösterilmeyecek, sadece sarı ayırıcı satırı belirlemek için
    ])
    
    # ÜST BÖLÜM - İlk geçiş
    # Fill the output dataframe with data from the processed dataframe (Upper section)
    for index, row in df.iterrows():
        # Tutar varsa ve sayısal bir değerse işle
        borc_formatted = ""
        alacak_formatted = ""
        
        if 'Tutar' in row and pd.notna(row['Tutar']):
            tutar = row['Tutar']
            if tutar < 0:
                # Negatif değerler Alacak'a yazılır, mutlak değer alınır
                alacak_formatted = format_turkish_currency(abs(tutar))
            else:
                # Pozitif değerler Borç'a yazılır
                borc_formatted = format_turkish_currency(tutar)
        
        # Orijinal tarih ve gruplandırılmış tarih
        original_date = row.get('Tarih', '')
        grouped_date = format_date(original_date, for_grouping=True)
        
        # Açıklamayı temizle - özel karakterler ve noktalama işaretlerini kaldır
        aciklama = row.get('Açıklama', '')
        temiz_aciklama = clean_description(aciklama)
        
        new_row = {
            'Fiş No': '',  # Boş bırak, ancak sütun kalsın
            'Fiş Tarihi': grouped_date,  # Gruplandırılmış tarih (1-10, 11-20, 21-31)
            'Fiş Açıklama': '',  # Boş bırakılacak
            'Hesap Kodu': '',  # This would be assigned by the accounting system
            'Evrak No': '',  # Boş bırak, ancak sütun kalsın
            'Evrak Tarihi': format_date(original_date),  # Orijinal tarih (değişmeyecek)
            'Detay Açıklama': temiz_aciklama,  # Temizlenmiş açıklama
            'Borç': borc_formatted,  # Türk Lirası formatında borç (negatif değer)
            'Alacak': alacak_formatted,  # Türk Lirası formatında alacak (pozitif değer)
            'Miktar': '',  # Boş bırakılacak
            'Belge Türü': '',  # Boş bırakılacak
            'Para Birimi': '',  # Boş bırakılacak
            'Kur': '',  # Boş bırakılacak
            'Döviz Tutar': '',  # Boş bırakılacak
            'is_separator': False  # Normal satır
        }
        
        output_df = pd.concat([output_df, pd.DataFrame([new_row])], ignore_index=True)
    
    # SARI AYIRICI SATIR - Tüm değerleri boş bir sarı satır eklenecek
    separator_row = {
        'Fiş No': '',  # Boş bırakıyoruz
        'Fiş Tarihi': '', # Boş bırakıyoruz
        'Fiş Açıklama': '',  # Boş bırakıyoruz
        'Hesap Kodu': '', 
        'Evrak No': '',  # Boş bırakıyoruz
        'Evrak Tarihi': '',  # Boş bırakıyoruz
        'Detay Açıklama': '*** SARI AYIRICI ÇIZGI ***',  # Sarı çizgi için tek açıklama
        'Borç': '',
        'Alacak': '',
        'Miktar': '',
        'Belge Türü': '',
        'Para Birimi': '',
        'Kur': '',
        'Döviz Tutar': '',
        'is_separator': True  # Bu bir ayırıcı satır
    }
    
    output_df = pd.concat([output_df, pd.DataFrame([separator_row])], ignore_index=True)
    
    # ALT BÖLÜM - İkinci geçiş
    # İşlemlerin zıttı olarak ikinci bir set ekle (tersine çevrilmiş borç/alacak)
    for index, row in df.iterrows():
        # Tutar varsa ve sayısal bir değerse işle
        borc_formatted = ""
        alacak_formatted = ""
        
        if 'Tutar' in row and pd.notna(row['Tutar']):
            tutar = row['Tutar']
            if tutar < 0:
                # Negatif değerler ALT BÖLÜMDE Borç'a yazılır
                borc_formatted = format_turkish_currency(abs(tutar))
            else:
                # Pozitif değerler ALT BÖLÜMDE Alacak'a yazılır
                alacak_formatted = format_turkish_currency(tutar)
        
        # Orijinal tarih ve gruplandırılmış tarih
        original_date = row.get('Tarih', '')
        grouped_date = format_date(original_date, for_grouping=True)
        
        # Açıklamayı temizle - özel karakterler ve noktalama işaretlerini kaldır
        aciklama = row.get('Açıklama', '')
        temiz_aciklama = clean_description(aciklama)
        
        new_row = {
            'Fiş No': '',  # Boş bırak, ancak sütun kalsın  
            'Fiş Tarihi': grouped_date,
            'Fiş Açıklama': '',
            'Hesap Kodu': '',
            'Evrak No': '',  # Boş bırak, ancak sütun kalsın
            'Evrak Tarihi': format_date(original_date),
            'Detay Açıklama': temiz_aciklama,
            'Borç': borc_formatted,  # ÖNEMLİ: Burada tersine çevirdik
            'Alacak': alacak_formatted,  # ÖNEMLİ: Burada tersine çevirdik
            'Miktar': '',
            'Belge Türü': '',
            'Para Birimi': '',
            'Kur': '',
            'Döviz Tutar': '',
            'is_separator': False
        }
        
        output_df = pd.concat([output_df, pd.DataFrame([new_row])], ignore_index=True)
    
    # İndirirken çıkarılacak sütunları belirt (CSV için)
    output_df.attrs['export_columns_to_remove'] = ['is_separator']
        
    return output_df
