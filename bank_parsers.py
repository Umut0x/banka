import pandas as pd
import numpy as np
import re
from utils import clean_description, format_date

def identify_bank_type(df):
    """
    Identify the bank type based on the dataframe structure
    """
    print("Banka tipini belirleme işlemi başladı...")
    print(f"DataFrame boyutu: {df.shape}")
    
    # İlk 10 satırı inceleyelim
    for i in range(min(10, len(df))):
        row_str = ' '.join([str(val) for val in df.iloc[i].values])
        print(f"Satır {i}: {row_str[:100]}...")
    
    # İlk olarak veri içeriğinde İş Bankası'na özel bir imza arayalım
    for i in range(min(10, len(df))):
        row_str = ' '.join([str(val).lower() for val in df.iloc[i].values])
        if 'iş bankası' in row_str or 'işbank' in row_str:
            print(f"İş Bankası imzası bulundu: {row_str[:50]}...")
            return "is_bankasi", i  # İmzanın bulunduğu satırı header_row olarak döndür
    
    # Banka türünü belirlemek için farklı desenleri kontrol et
    is_bankasi_headers = ['işlem tarihi', 'İşlem Tarihi', 'açıklama', 'Açıklama', 'tutar', 'Tutar', 'bakiye', 'Bakiye']
    garanti_headers = ['tarih', 'Tarih', 'açıklama', 'Açıklama', 'tutar', 'Tutar', 'bakiye', 'Bakiye']
    akbank_headers = ['TARİH', 'AÇIKLAMA', 'TUTAR', 'BAKİYE']
    ziraat_headers = ['tarih', 'Tarih', 'açıklama', 'Açıklama', 'borç', 'Borç', 'alacak', 'Alacak']
    
    # Önce doğrudan sütun isimlerini kontrol et
    is_match = 0
    garanti_match = 0
    akbank_match = 0
    ziraat_match = 0
    
    for col in df.columns:
        col_str = str(col).lower()
        # İş Bankası kontrolü
        if any(header.lower() in col_str for header in is_bankasi_headers):
            is_match += 1
        # Garanti kontrolü
        if any(header.lower() in col_str for header in garanti_headers):
            garanti_match += 1
        # Akbank kontrolü
        if any(header.lower() in col_str for header in akbank_headers):
            akbank_match += 1
        # Ziraat kontrolü
        if any(header.lower() in col_str for header in ziraat_headers):
            ziraat_match += 1
    
    # İşlem tarihi -> İş Bankası için özel bir kontrol
    if any('işlem' in str(col).lower() for col in df.columns):
        is_match += 2
    
    print(f"Sütun eşleşmeleri: İş Bankası = {is_match}, Garanti = {garanti_match}, Akbank = {akbank_match}, Ziraat = {ziraat_match}")
    
    # Eğer header yok ise içerikten bulmaya çalış
    if is_match == 0 and garanti_match == 0 and akbank_match == 0 and ziraat_match == 0:
        # Veri içerisinde header satırını bulmaya çalış
        for i in range(min(15, len(df))):
            row = df.iloc[i]
            row_str = ' '.join([str(val).lower() for val in row.values])
            
            # İş Bankası için kontrol
            is_bank_match = sum(1 for header in is_bankasi_headers if header.lower() in row_str)
            if is_bank_match >= 3:
                print(f"İş Bankası başlık satırı bulundu, satır: {i}")
                return "is_bankasi", i
            
            # Garanti için kontrol
            garanti_match = sum(1 for header in garanti_headers if header.lower() in row_str)
            if garanti_match >= 3:
                print(f"Garanti Bankası başlık satırı bulundu, satır: {i}")
                return "garanti", i
            
            # Akbank için kontrol
            akbank_match = sum(1 for header in akbank_headers if header.lower() in row_str)
            if akbank_match >= 3:
                print(f"Akbank başlık satırı bulundu, satır: {i}")
                return "akbank", i
            
            # Ziraat için kontrol
            ziraat_match = sum(1 for header in ziraat_headers if header.lower() in row_str)
            if ziraat_match >= 3:
                print(f"Ziraat Bankası başlık satırı bulundu, satır: {i}")
                return "ziraat", i
    
    # Eğer özel "İşlem Tarihi" sütunu varsa, bu İş Bankası için güçlü bir gösterge
    if any('işlem tarihi' in str(col).lower() for col in df.columns):
        print(f"'İşlem Tarihi' sütunu bulundu, İş Bankası olarak tanımlandı.")
        return "is_bankasi", -1
    
    # En çok eşleşen banka tipini döndür
    if is_match > garanti_match and is_match > akbank_match and is_match > ziraat_match:
        print(f"İş Bankası olarak tanımlandı. (Eşleşme: {is_match})")
        return "is_bankasi", -1
    elif garanti_match > is_match and garanti_match > akbank_match and garanti_match > ziraat_match:
        print(f"Garanti Bankası olarak tanımlandı. (Eşleşme: {garanti_match})")
        return "garanti", -1
    elif akbank_match > is_match and akbank_match > garanti_match and akbank_match > ziraat_match:
        print(f"Akbank olarak tanımlandı. (Eşleşme: {akbank_match})")
        return "akbank", -1
    elif ziraat_match > is_match and ziraat_match > garanti_match and ziraat_match > akbank_match:
        print(f"Ziraat Bankası olarak tanımlandı. (Eşleşme: {ziraat_match})")
        return "ziraat", -1
    else:
        # Eşitlik durumunda İş Bankası tercih et
        if is_match >= 2:
            print(f"Eşitlik durumunda İş Bankası tercih edildi.")
            return "is_bankasi", -1
    
    # Hiçbir banka tipi tanımlanamadı
    print("Hiçbir banka tipi tanımlanamadı.")
    return "unknown", -1

def parse_is_bankasi(df, header_row=-1):
    """
    Parse İş Bankası statement format
    Expected columns: İşlem Tarihi | Açıklama | Tutar | Bakiye
    """
    print(f"İş Bankası parser başlatıldı. Header row: {header_row}")
    
    # Header satırı varsa, veriyi düzenle
    if header_row > 0:
        print(f"Header satırı {header_row} kullanılıyor.")
        # Header satırını sütun isimleri olarak kullan
        new_headers = df.iloc[header_row].astype(str)
        # Header'dan sonraki verileri al
        df = df.iloc[header_row+1:].reset_index(drop=True)
        # Yeni sütun isimleri ata
        df.columns = new_headers
    
    # Sütun isimlerini standartlaştır
    column_mapping = {}
    expected_columns = ['işlem tarihi', 'açıklama', 'tutar', 'bakiye', 'işlem no']
    
    for col in df.columns:
        col_str = str(col).lower()
        for expected_col in expected_columns:
            if expected_col in col_str:
                column_mapping[col] = expected_col.title()
                break
            # İşlem Tarihi için özel kontrol
            elif 'işlem' in col_str and 'tarih' in col_str:
                column_mapping[col] = 'İşlem Tarihi'
                break
    
    print(f"Bulunan sütun eşleştirmeleri: {column_mapping}")
    
    # Yeterli sütun bulunamadıysa
    required_columns = ['işlem tarihi', 'açıklama', 'tutar']
    missing_columns = [col for col in required_columns if not any(col in str(mapped_col).lower() for mapped_col in column_mapping.values())]
    
    if missing_columns:
        print(f"Gerekli sütunlar bulunamadı: {missing_columns}")
        if len(df.columns) >= 4:
            print("Zorunlu sütun isimleri bulunamadı, ancak en az 4 sütun var. Varsayılan sütun sıralaması kullanılacak.")
            # Varsayılan sırayla atama yap: İşlem Tarihi, Açıklama, Tutar, Bakiye
            if len(df.columns) >= 4 and not column_mapping:
                column_names = list(df.columns)
                # İlk 4 sütunu kullan
                column_mapping = {
                    column_names[0]: 'İşlem Tarihi',
                    column_names[1]: 'Açıklama',
                    column_names[2]: 'Tutar',
                    column_names[3]: 'Bakiye'
                }
                print(f"Varsayılan sütun eşleştirmeleri: {column_mapping}")
        else:
            raise ValueError(f"İş Bankası formatı için gerekli sütunlar bulunamadı: {', '.join(missing_columns)}")
    
    # Sütunları yeniden isimlendir
    df_renamed = df.rename(columns=column_mapping)
    
    # Gerekli sütunları çıkar
    tarih_col = next((col for col in df_renamed.columns if 'işlem tarihi' in str(col).lower() or 'tarih' in str(col).lower()), None)
    aciklama_col = next((col for col in df_renamed.columns if 'açıklama' in str(col).lower() or 'aciklama' in str(col).lower()), None)
    tutar_col = next((col for col in df_renamed.columns if 'tutar' in str(col).lower()), None)
    bakiye_col = next((col for col in df_renamed.columns if 'bakiye' in str(col).lower()), None)
    islem_no_col = next((col for col in df_renamed.columns if 'işlem no' in str(col).lower() or 'islem no' in str(col).lower()), None)
    
    print(f"Çıkarılan sütunlar: Tarih={tarih_col}, Açıklama={aciklama_col}, Tutar={tutar_col}, Bakiye={bakiye_col}, İşlem No={islem_no_col}")
    
    # Yeni DataFrame oluştur
    processed_df = pd.DataFrame()
    
    # Tarih sütununu ekle
    if tarih_col:
        processed_df['Tarih'] = df_renamed[tarih_col].apply(format_date)
    else:
        processed_df['Tarih'] = ""
    
    # Açıklama sütununu ekle
    if aciklama_col:
        processed_df['Açıklama'] = df_renamed[aciklama_col].apply(clean_description)
    else:
        processed_df['Açıklama'] = ""
    
    # Tutar sütununu ekle
    if tutar_col:
        # Sayısal formata çevir
        clean_amounts = df_renamed[tutar_col].astype(str).str.replace('TL', '').str.replace(' ', '')
        # Virgülü nokta ile değiştir
        clean_amounts = clean_amounts.str.replace(',', '.')
        # Sayısal değere dönüştür
        processed_df['Tutar'] = pd.to_numeric(clean_amounts, errors='coerce')
    else:
        processed_df['Tutar'] = 0
    
    # Bakiye sütununu ekle
    if bakiye_col:
        clean_bakiye = df_renamed[bakiye_col].astype(str).str.replace('TL', '').str.replace(' ', '')
        clean_bakiye = clean_bakiye.str.replace(',', '.')
        processed_df['Bakiye'] = pd.to_numeric(clean_bakiye, errors='coerce')
    
    # İşlem No sütununu ekle (varsa)
    if islem_no_col:
        processed_df['İşlem No'] = df_renamed[islem_no_col]
    
    # Borç ve Alacak sütunlarını hesapla
    processed_df['Borç'] = processed_df['Tutar'].apply(lambda x: abs(x) if x < 0 else 0)
    processed_df['Alacak'] = processed_df['Tutar'].apply(lambda x: x if x > 0 else 0)
    
    # Tarih sütununa göre sırala
    if 'Tarih' in processed_df.columns and not processed_df['Tarih'].isna().all():
        try:
            processed_df = processed_df.sort_values('Tarih')
        except:
            print("Tarih sütununa göre sıralama yapılamadı.")
    
    return processed_df

def parse_garanti_bank(df, header_row=-1):
    """
    Parse Garanti Bank statement format
    Expected columns: Tarih | Açıklama | Tutar | Bakiye
    """
    print(f"Garanti Bankası parser başlatıldı. Header row: {header_row}")
    
    # Eğer bir header satırı bulunmuşsa, o satırı kullanarak veriyi yeniden düzenle
    if header_row > 0:
        print(f"Header satırı {header_row} kullanılıyor.")
        # Önce header satırını sütun başlıkları olarak al
        new_headers = df.iloc[header_row].astype(str)
        
        # Başlık satırının altındaki veriyi al
        df = df.iloc[header_row+1:].reset_index(drop=True)
        
        # Yeni sütun başlıklarını ata
        df.columns = new_headers
    
    # Standardize column names (case insensitive matching)
    column_mapping = {}
    expected_columns = ['tarih', 'açıklama', 'tutar', 'bakiye', 'dekont no']
    
    for col in df.columns:
        for expected_col in expected_columns:
            if expected_col.lower() in str(col).lower():
                column_mapping[col] = expected_col.title()
                break
    
    print(f"Bulunan sütun eşleştirmeleri: {column_mapping}")
    
    # If we couldn't find all expected columns, try our best with what we have
    required_columns = ['tarih', 'açıklama', 'tutar']
    missing_columns = [col for col in required_columns if not any(col in str(mapped_col).lower() for mapped_col in column_mapping.values())]
    
    if missing_columns:
        print(f"Gerekli sütunlar bulunamadı: {missing_columns}")
        if len(df.columns) >= 4:
            print("Zorunlu sütun isimleri bulunamadı, ancak en az 4 sütun var. Varsayılan sütun sıralaması kullanılacak.")
            # Varsayılan sırayla atama yap: Tarih, Açıklama, Tutar, Bakiye
            if len(df.columns) >= 4 and not column_mapping:
                column_names = list(df.columns)
                # İlk 4 sütunu kullan
                column_mapping = {
                    column_names[0]: 'Tarih',
                    column_names[1]: 'Açıklama',
                    column_names[2]: 'Tutar',
                    column_names[3]: 'Bakiye'
                }
                print(f"Varsayılan sütun eşleştirmeleri: {column_mapping}")
        else:
            raise ValueError(f"Garanti Bankası formatına uyan sütunlar bulunamadı: {', '.join(missing_columns)}")
    
    # Rename columns to standardized names
    df_renamed = df.rename(columns=column_mapping)
    
    # Extract required columns, use empty strings for missing columns
    tarih_col = next((col for col in df_renamed.columns if 'tarih' in str(col).lower()), None)
    aciklama_col = next((col for col in df_renamed.columns if 'açıklama' in str(col).lower() or 'aciklama' in str(col).lower()), None)
    tutar_col = next((col for col in df_renamed.columns if 'tutar' in str(col).lower()), None)
    dekont_col = next((col for col in df_renamed.columns if 'dekont' in str(col).lower()), None)
    
    print(f"Çıkarılan sütunlar: Tarih={tarih_col}, Açıklama={aciklama_col}, Tutar={tutar_col}, Dekont No={dekont_col}")
    
    # Create a new dataframe with the required columns
    processed_df = pd.DataFrame()
    
    if tarih_col:
        processed_df['Tarih'] = df_renamed[tarih_col].apply(format_date)
    else:
        processed_df['Tarih'] = ""
        
    if aciklama_col:
        processed_df['Açıklama'] = df_renamed[aciklama_col].apply(clean_description)
    else:
        processed_df['Açıklama'] = ""
        
    if tutar_col:
        # Convert amount column to numeric, handling potential formatting issues
        # İlk önce TL, +, - ve boşluk gibi karakterleri temizle
        clean_amounts = df_renamed[tutar_col].astype(str).str.replace('TL', '').str.replace(' ', '')
        
        # Virgülleri nokta ile değiştir (Türkçe ondalık ayırıcıyı İngilizce formatına çevir)
        clean_amounts = clean_amounts.str.replace(',', '.')
        
        # Sayısal değere dönüştür
        processed_df['Tutar'] = pd.to_numeric(clean_amounts, errors='coerce')
    else:
        processed_df['Tutar'] = 0
        
    if dekont_col:
        processed_df['Dekont No'] = df_renamed[dekont_col]
    else:
        processed_df['Dekont No'] = ""
    
    # Calculate Borç and Alacak based on Tutar
    processed_df['Borç'] = processed_df['Tutar'].apply(lambda x: abs(x) if x < 0 else 0)
    processed_df['Alacak'] = processed_df['Tutar'].apply(lambda x: x if x > 0 else 0)
    
    return processed_df

def parse_akbank(df, header_row=-1):
    """
    Parse Akbank statement format
    Expected columns: TARİH | AÇIKLAMA | TUTAR | BAKİYE
    """
    print(f"Akbank parser başlatıldı. Header row: {header_row}")
    # Bu fonksiyon Garanti ile aynı mantıkla çalışır (sütun isimleri farklı olsa da)
    return parse_garanti_bank(df, header_row)

def parse_ziraat(df, header_row=-1):
    """
    Parse Ziraat Bank statement format
    Expected columns: Tarih | Açıklama | Borç | Alacak | Bakiye
    """
    print(f"Ziraat Bankası parser başlatıldı. Header row: {header_row}")
    
    # Header satırı varsa veriyi düzenle
    if header_row > 0:
        new_headers = df.iloc[header_row].astype(str)
        df = df.iloc[header_row+1:].reset_index(drop=True)
        df.columns = new_headers
    
    # Sütun isimlerini standartlaştır
    column_mapping = {}
    expected_columns = ['tarih', 'açıklama', 'borç', 'alacak', 'bakiye', 'işlem no']
    
    for col in df.columns:
        for expected_col in expected_columns:
            if expected_col.lower() in str(col).lower():
                column_mapping[col] = expected_col.title()
                break
    
    # Gerekli sütunlar yoksa varsayılan sıralamayı dene
    required_columns = ['tarih', 'açıklama', 'borç', 'alacak']
    missing_columns = [col for col in required_columns if not any(col in str(mapped_col).lower() for mapped_col in column_mapping.values())]
    
    if missing_columns:
        print(f"Gerekli sütunlar bulunamadı: {missing_columns}")
        if len(df.columns) >= 5:
            # Varsayılan sırayla atama yap: Tarih, Açıklama, Borç, Alacak, Bakiye
            column_names = list(df.columns)
            column_mapping = {
                column_names[0]: 'Tarih',
                column_names[1]: 'Açıklama',
                column_names[2]: 'Borç',
                column_names[3]: 'Alacak',
                column_names[4]: 'Bakiye'
            }
        else:
            raise ValueError(f"Ziraat Bankası formatı için gerekli sütunlar bulunamadı: {', '.join(missing_columns)}")
    
    # Sütunları yeniden isimlendir
    df_renamed = df.rename(columns=column_mapping)
    
    # Gerekli sütunları çıkar
    tarih_col = next((col for col in df_renamed.columns if 'tarih' in str(col).lower()), None)
    aciklama_col = next((col for col in df_renamed.columns if 'açıklama' in str(col).lower() or 'aciklama' in str(col).lower()), None)
    borc_col = next((col for col in df_renamed.columns if 'borç' in str(col).lower() or 'borc' in str(col).lower()), None)
    alacak_col = next((col for col in df_renamed.columns if 'alacak' in str(col).lower()), None)
    bakiye_col = next((col for col in df_renamed.columns if 'bakiye' in str(col).lower()), None)
    
    # Yeni DataFrame oluştur
    processed_df = pd.DataFrame()
    
    if tarih_col:
        processed_df['Tarih'] = df_renamed[tarih_col].apply(format_date)
    else:
        processed_df['Tarih'] = ""
    
    if aciklama_col:
        processed_df['Açıklama'] = df_renamed[aciklama_col].apply(clean_description)
    else:
        processed_df['Açıklama'] = ""
    
    # Borç sütunu
    if borc_col:
        clean_borc = df_renamed[borc_col].astype(str).str.replace('TL', '').str.replace(' ', '')
        clean_borc = clean_borc.str.replace(',', '.')
        processed_df['Borç'] = pd.to_numeric(clean_borc, errors='coerce').fillna(0)
    else:
        processed_df['Borç'] = 0
    
    # Alacak sütunu
    if alacak_col:
        clean_alacak = df_renamed[alacak_col].astype(str).str.replace('TL', '').str.replace(' ', '')
        clean_alacak = clean_alacak.str.replace(',', '.')
        processed_df['Alacak'] = pd.to_numeric(clean_alacak, errors='coerce').fillna(0)
    else:
        processed_df['Alacak'] = 0
    
    # Bakiye sütunu (opsiyonel)
    if bakiye_col:
        clean_bakiye = df_renamed[bakiye_col].astype(str).str.replace('TL', '').str.replace(' ', '')
        clean_bakiye = clean_bakiye.str.replace(',', '.')
        processed_df['Bakiye'] = pd.to_numeric(clean_bakiye, errors='coerce')
    
    # Tutar hesapla: Alacak - Borç
    processed_df['Tutar'] = processed_df['Alacak'] - processed_df['Borç']
    
    return processed_df
