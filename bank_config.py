import json
import os
import pandas as pd
import streamlit as st
from datetime import datetime

# Banka formatları için veritabanı tablosu oluşturmak yerine, önce dosya tabanlı bir çözüm kullanacağız
# Daha sonra tam veritabanı entegrasyonu eklenebilir

CONFIG_DIR = "bank_configs"
CONFIG_FILE = os.path.join(CONFIG_DIR, "bank_formats.json")

# Varsayılan banka formatları
DEFAULT_BANK_FORMATS = [
    {
        "id": "garanti",
        "name": "Garanti Bankası",
        "header_identifier": ["Tarih", "Açıklama", "Tutar", "Bakiye"],
        "date_col": "Tarih",
        "description_col": "Açıklama",
        "amount_col": "Tutar",
        "balance_col": "Bakiye",
        "columns": ["Tarih", "Açıklama", "Tutar", "Bakiye"],
        "skip_rows": 0,
        "active": True,
        "content_indicators": ["GARANTİ", "BBVA", "BONUS", "PARAMATIK", "BNK", "G.BANKASI"],
        "created_at": datetime.now().isoformat()
    },
    {
        "id": "is_bankasi",
        "name": "İş Bankası",
        "header_identifier": ["İşlem Tarihi", "Açıklama", "Tutar", "Bakiye"],
        "date_col": "İşlem Tarihi",
        "description_col": "Açıklama",
        "amount_col": "Tutar",
        "balance_col": "Bakiye",
        "columns": ["İşlem Tarihi", "Açıklama", "Tutar", "Bakiye"],
        "skip_rows": 0,
        "active": True,
        "content_indicators": ["İŞ BANKASI", "İŞCEP", "MAXIPARA", "MXP", "TÜRKİYE İŞ BANKASI"],
        "created_at": datetime.now().isoformat()
    },
    {
        "id": "akbank",
        "name": "Akbank",
        "header_identifier": ["TARİH", "AÇIKLAMA", "TUTAR", "BAKİYE"],
        "date_col": "TARİH",
        "description_col": "AÇIKLAMA",
        "amount_col": "TUTAR",
        "balance_col": "BAKİYE",
        "columns": ["TARİH", "AÇIKLAMA", "TUTAR", "BAKİYE"],
        "skip_rows": 0,
        "active": True,
        "content_indicators": ["AKBANK", "AXESS", "AKSİGORTA", "AKODE", "AK BANK"],
        "created_at": datetime.now().isoformat()
    },
    {
        "id": "ziraat",
        "name": "Ziraat Bankası",
        "header_identifier": ["Tarih", "Açıklama", "Borç", "Alacak", "Bakiye"],
        "date_col": "Tarih",
        "description_col": "Açıklama",
        "debit_col": "Borç",
        "credit_col": "Alacak",
        "balance_col": "Bakiye",
        "columns": ["Tarih", "Açıklama", "Borç", "Alacak", "Bakiye"],
        "skip_rows": 0,
        "active": True,
        "content_indicators": ["ZİRAAT", "TC ZİRAAT", "ZİRAAT BANKASI", "ZİRAATKART"],
        "created_at": datetime.now().isoformat()
    }
]

def init_config():
    """
    Eğer config dizini ve dosyası yoksa oluştur
    """
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_BANK_FORMATS, f, ensure_ascii=False, indent=4)

def load_bank_formats():
    """
    Banka formatlarını yükle
    """
    init_config()
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Banka formatları yüklenirken hata oluştu: {str(e)}")
        return DEFAULT_BANK_FORMATS

def save_bank_formats(formats):
    """
    Banka formatlarını kaydet
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(formats, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Banka formatları kaydedilirken hata oluştu: {str(e)}")
        return False

def add_bank_format(format_data):
    """
    Yeni banka formatı ekle
    """
    formats = load_bank_formats()
    
    # Aynı ID'ye sahip başka bir format var mı kontrol et
    existing_ids = [f["id"] for f in formats]
    if format_data["id"] in existing_ids:
        return False, "Bu ID'ye sahip bir banka formatı zaten var."
    
    # Yeni format için oluşturulma zamanı ekle
    format_data["created_at"] = datetime.now().isoformat()
    
    formats.append(format_data)
    success = save_bank_formats(formats)
    
    if success:
        return True, "Banka formatı başarıyla eklendi."
    else:
        return False, "Banka formatı eklenirken bir hata oluştu."

def update_bank_format(format_id, format_data):
    """
    Banka formatını güncelle
    """
    formats = load_bank_formats()
    
    for i, format in enumerate(formats):
        if format["id"] == format_id:
            # Oluşturulma zamanını koru
            format_data["created_at"] = format["created_at"]
            formats[i] = format_data
            success = save_bank_formats(formats)
            
            if success:
                return True, "Banka formatı başarıyla güncellendi."
            else:
                return False, "Banka formatı güncellenirken bir hata oluştu."
    
    return False, "Belirtilen ID'ye sahip banka formatı bulunamadı."

def delete_bank_format(format_id):
    """
    Banka formatını sil
    """
    formats = load_bank_formats()
    
    for i, format in enumerate(formats):
        if format["id"] == format_id:
            del formats[i]
            success = save_bank_formats(formats)
            
            if success:
                return True, "Banka formatı başarıyla silindi."
            else:
                return False, "Banka formatı silinirken bir hata oluştu."
    
    return False, "Belirtilen ID'ye sahip banka formatı bulunamadı."

def get_bank_format(format_id):
    """
    Belirli bir banka formatını getir
    """
    formats = load_bank_formats()
    
    for format in formats:
        if format["id"] == format_id:
            return format
    
    return None

def find_header_row(df, header_identifiers):
    """
    Banka ekstresindeki başlık satırını bul
    Başlık satırını bulamadıysa -1 döndürür
    """
    # DataFrame'i string formatına çevir
    str_df = df.astype(str)
    
    # Her bir satır için kontrol et
    for i in range(min(20, len(df))):  # İlk 20 satıra bak (varsa)
        row_values = [val.lower() for val in str_df.iloc[i].values if not pd.isna(val)]
        # Tüm tanımlayıcıların satırda olup olmadığını kontrol et
        if all(any(identifier.lower() in val for val in row_values) for identifier in header_identifiers):
            return i
    
    return -1

def identify_bank_format(df):
    """
    DataFrame'den banka formatını tanımla ve gerekirse başlık satırını belirle
    Ultra gelişmiş çok katmanlı analiz sistemi kullanarak banka tipini tanımlar
    """
    formats = load_bank_formats()
    active_formats = [f for f in formats if f.get("active", True)]
    
    # DataFrame'in geçerli olup olmadığını kontrol et
    if df is None or len(df) == 0 or len(df.columns) == 0:
        print("HATA: Analiz için geçerli bir DataFrame yok!")
        return None
    
    print(f"Banka formatı analizi başlatıldı. DataFrame boyutu: {df.shape}")
    print(f"DataFrame sütunları: {df.columns.tolist()}")
    
    # Tüm formatlara puan verebilmek için detaylı analiz sistemi
    bank_scores = {f["id"]: {
        "format": f,
        "total_score": 0,
        "detection_methods": [],
        "header_row": -1,
        "processed_df": None
    } for f in active_formats}
    
    # ====================== İÇERİK ANALİZİ BÖLÜMÜ ======================
    
    # 1. AŞAMA: DOSYA İÇERİĞİNDEKİ LOGO METNİNİ / BÜYÜK BAŞLIKLARI ARA
    # Çoğu banka ekstrelerinin üstünde banka adı büyük harflerle yazılıdır
    for i in range(min(10, len(df))):  # İlk 10 satıra bak
        row_content = " ".join([str(val).upper() for val in df.iloc[i].values if not pd.isna(val)])
        
        # Her banka için kontrol et
        for bank_id, bank_data in bank_scores.items():
            bank_format = bank_data["format"]
            bank_name = bank_format["name"].upper()
            
            # Tam banka adı kontrolü
            if bank_name in row_content:
                # Tam isim eşleşmesi büyük puan kazandırır
                bank_data["total_score"] += 10.0
                bank_data["detection_methods"].append(f"Dosya içeriğinde tam banka adı '{bank_name}' bulundu (+10.0)")
            
            # Banka adının parçaları kontrolü
            bank_name_parts = bank_name.split()
            for part in bank_name_parts:
                if len(part) >= 3 and part in row_content:  # Anlamlı kelimeler (3+ harf)
                    bank_data["total_score"] += 3.0
                    bank_data["detection_methods"].append(f"Dosya içeriğinde banka adı parçası '{part}' bulundu (+3.0)")
    
    # 2. AŞAMA: BAŞLIK SATIRI VE SÜTUN ANALİZİ
    # Sütun başlıklarını kontrol et - bu önemli bir göstergedir
    
    # Tüm sütun isimlerini küçük harfe çevir
    df_columns = [str(col).lower() for col in df.columns]
    
    for bank_id, bank_data in bank_scores.items():
        bank_format = bank_data["format"]
        header_identifiers = bank_format.get("header_identifier", [])
        
        if not header_identifiers:
            continue
        
        # Sütun başlıkları eşleşme kontrolü
        exact_matches = sum(1 for identifier in header_identifiers if identifier.lower() in df_columns)
        partial_matches = sum(1 for identifier in header_identifiers 
                             if any(identifier.lower() in col for col in df_columns))
        
        # Skor hesapla
        if exact_matches > 0:
            column_score = exact_matches * 2.0  # Her tam sütun eşleşmesi 2 puan
            bank_data["total_score"] += column_score
            bank_data["detection_methods"].append(f"{exact_matches} sütun başlığı tam eşleşti (+{column_score:.1f})")
        
        if partial_matches > 0:
            partial_score = partial_matches * 0.5  # Her kısmi eşleşme 0.5 puan
            bank_data["total_score"] += partial_score
            bank_data["detection_methods"].append(f"{partial_matches} sütun başlığı kısmen eşleşti (+{partial_score:.1f})")
    
    # 3. AŞAMA: BAŞLIK SATIRI BULMA VE İŞLEME
    # Her banka formatı için başlık satırını bulmaya çalış
    for bank_id, bank_data in bank_scores.items():
        bank_format = bank_data["format"]
        header_identifiers = bank_format.get("header_identifier", [])
        
        if not header_identifiers:
            continue
        
        # Başlık satırını bul
        header_row = find_header_row(df, header_identifiers)
        
        if header_row >= 0:
            # Başlık satırı bulundu!
            bank_data["header_row"] = header_row
            
            # İşlenmiş DataFrame'i oluştur
            new_headers = df.iloc[header_row]
            new_df = df.iloc[header_row+1:].reset_index(drop=True)
            new_df.columns = new_headers
            bank_data["processed_df"] = new_df
            
            # Başlık satırı tespiti büyük puan kazandırır
            bank_data["total_score"] += 8.0
            bank_data["detection_methods"].append(f"Başlık satırı bulundu (satır: {header_row+1}) (+8.0)")
    
    # 4. AŞAMA: BANKA ÖZEL İŞLEMLERİNİ VE SÖZDİZİMİNİ TANI
    # Her bankanın kendine özel işlem açıklamaları ve kodları vardır
    
    # Bankalar için karakteristik terimler ve ifade kalıpları
    bank_fingerprints = {
        "is_bankasi": ["İŞ BANKASI", "İŞCEP", "MXP", "MAXIPARA", "TRX", "SÖZLEŞME", "YATIRIM", "3D", "KART", "KRD", "KMH"],
        "garanti": ["GARANTİ", "BBVA", "BNK", "BONUS", "PARAMATIK", "BANKAMATIK", "GİB", "PARA ÇIKIŞI", "PARA GİRİŞİ", "G.BANKASI"],
        "akbank": ["AKBANK", "AXESS", "AKSİGORTA", "AKODE", "KARTTAN", "AK"],
        "ziraat": ["ZİRAAT", "ZTK", "ZBK", "TC ZİRAAT", "ZİRAATKART", "BANKKART", "ZB"],
        # Diğer bankalar için parmak izleri
    }
    
    # İşlem açıklamalarını kontrol et
    for bank_id, bank_data in bank_scores.items():
        # Bu banka için parmak izi var mı?
        if bank_id in bank_fingerprints:
            fingerprints = bank_fingerprints[bank_id]
            
            # Eğer işlenmiş DataFrame varsa önce onu kullan
            target_df = bank_data["processed_df"] if bank_data["processed_df"] is not None else df
            
            # Açıklama sütunlarında ara
            desc_columns = []
            
            # Potansiyel açıklama sütunlarını belirle
            for col in target_df.columns:
                col_str = str(col).lower()
                if "açıklama" in col_str or "aciklama" in col_str or "description" in col_str:
                    desc_columns.append(col)
            
            # Eğer açıklama sütunu yoksa, tüm string sütunlarını kontrol et
            if not desc_columns:
                desc_columns = target_df.select_dtypes(include=['object']).columns
            
            # Her açıklama sütununda parmak izlerini ara
            fingerprint_matches = 0
            matched_fp = []
            
            for col in desc_columns:
                for val in target_df[col].astype(str):
                    val_upper = val.upper()
                    for fp in fingerprints:
                        if fp in val_upper:
                            fingerprint_matches += 1
                            if fp not in matched_fp:
                                matched_fp.append(fp)
            
            # Skor hesapla - farklı parmak izleri daha önemli
            if fingerprint_matches > 0:
                unique_fps = len(matched_fp)
                fp_score = unique_fps * 2.0 + min(3.0, (fingerprint_matches - unique_fps) * 0.1)
                bank_data["total_score"] += fp_score
                bank_data["detection_methods"].append(f"Banka parmak izleri: '{', '.join(matched_fp)}' ({fingerprint_matches} kez) (+{fp_score:.1f})")
    
    # 5. AŞAMA: HEM DOSYA İÇERİĞİNİ HEM ÇIKTI BİÇİMİNİ KONTROL ET
    # Tarihlerin formatı, para birimleri, sayı formatları, vb.
    
    # Tarih formatı kontrolü
    for bank_id, bank_data in bank_scores.items():
        # İşlenmiş DataFrame varsa kullan
        target_df = bank_data["processed_df"] if bank_data["processed_df"] is not None else df
        
        # Tarih sütunlarını tanımlamaya çalış
        date_cols = []
        for col in target_df.columns:
            col_str = str(col).lower()
            if "tarih" in col_str or "date" in col_str or "trh" in col_str:
                date_cols.append(col)
        
        # Eğer tarih sütunu bulunduysa, formata bak
        if date_cols:
            date_patterns = {
                "is_bankasi": ["/", "."],  # İş Bankası genelde DD.MM.YYYY kullanır
                "garanti": ["/", "."],     # Garanti de DD.MM.YYYY kullanır
                "akbank": ["/", "."],      # Akbank da genelde noktayla ayırır
                "ziraat": ["/", "."],      # Ziraat de benzer
                # Diğer bankalar...
            }
            
            # Banka için tarih desenleri varsa
            if bank_id in date_patterns:
                bank_patterns = date_patterns[bank_id]
                pattern_matches = 0
                
                # Her tarih sütununda ilk 10 veriyi kontrol et
                for col in date_cols:
                    sample_size = min(10, len(target_df))
                    samples = target_df[col].astype(str).head(sample_size)
                    
                    for sample in samples:
                        for pattern in bank_patterns:
                            if pattern in sample:
                                pattern_matches += 1
                                break
                
                # Tarih formatı puanı
                if pattern_matches > 0:
                    date_score = min(3.0, pattern_matches * 0.3)
                    bank_data["total_score"] += date_score
                    bank_data["detection_methods"].append(f"Tarih formatı kontrolü: {pattern_matches} eşleşme (+{date_score:.1f})")
    
    # ================= SONUÇLARI DEĞERLENDİR ===================
    
    # Skorları göster (debugging için)
    for bank_id, bank_data in bank_scores.items():
        print(f"BANKA SKORU: {bank_data['format']['name']} - Toplam: {bank_data['total_score']:.2f}")
        for method in bank_data["detection_methods"]:
            print(f"  - {method}")
    
    # En yüksek puanlı bankayı bul
    best_bank_id = None
    best_score = 0
    
    for bank_id, bank_data in bank_scores.items():
        if bank_data["total_score"] > best_score:
            best_score = bank_data["total_score"]
            best_bank_id = bank_id
    
    # Puanı yeterince yüksek bankanın formatını döndür
    if best_bank_id and best_score >= 2.0:  # En az 2 puan olmalı
        best_bank = bank_scores[best_bank_id]
        result = best_bank["format"].copy()
        
        # Başlık satırı ve işlenmiş DataFrame bilgisini ekle
        if best_bank["header_row"] != -1:
            result["header_row"] = best_bank["header_row"]
        if best_bank["processed_df"] is not None:
            result["processed_df"] = best_bank["processed_df"]
        
        print(f"Ultra Gelişmiş Analiz: Banka formatı tanımlandı: {result['name']} (Skor: {best_score:.2f})")
        return result
    
    # Hiçbir format için yeterli skor bulunamadıysa, başlık satırı kontrolünü tekrar yap
    # Her format için başlık satırı kontrolü (son bir şans)
    for format in active_formats:
        header_identifiers = format.get("header_identifier", [])
        if not header_identifiers:
            continue
        
        header_row = find_header_row(df, header_identifiers)
        if header_row >= 0:
            # Başlık satırı bulundu, yeni bir DataFrame oluştur
            new_headers = df.iloc[header_row]
            new_df = df.iloc[header_row+1:].reset_index(drop=True)
            new_df.columns = new_headers
            
            # Format bilgisiyle birlikte döndür
            format_with_header = format.copy()
            format_with_header["header_row"] = header_row
            format_with_header["processed_df"] = new_df
            print(f"Son Şans Kontrolü: Banka formatı başlık analizinden sonra tanımlandı: {format['name']}")
            return format_with_header
    
    # Hiçbir format eşleşmedi
    print("Ultra Gelişmiş Analiz: Banka formatı tanımlanamadı")
    return None

def standardize_dataframe(df, bank_format):
    """
    DataFrame'i standart formata dönüştür
    """
    print(f"Standardizasyon başlıyor. DataFrame boyutu: {df.shape}")
    print(f"DataFrame sütunları: {list(df.columns)}")
    print(f"Banka format bilgisi: {bank_format.get('name')}")
    
    # Gelen verileri analiz et
    print("İlk 5 satırın içeriği:")
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        print(f"  Satır {i}: {list(row.values)[:5]}...")  # İlk 5 değeri göster
    
    standardized_df = pd.DataFrame()
    
    # Başlık satırı var mı diye kontrol et
    print("Başlık satırı aranıyor...")
    header_row = -1
    
    # Olası başlık satırlarını belirle
    for i in range(min(20, len(df))):
        row_str = ' '.join([str(val).lower() for val in df.iloc[i].values if not pd.isna(val)])
        # Tarih, Açıklama, Tutar gibi başlık terimleri var mı diye kontrol et
        if ('tarih' in row_str and 'açıklama' in row_str and ('tutar' in row_str or 'borç' in row_str or 'alacak' in row_str)):
            header_row = i
            print(f"Potansiyel başlık satırı bulundu, satır {i}: {row_str[:100]}...")
            break
    
    # Başlık satırı bulunduysa, veriyi yeniden düzenle
    if header_row >= 0:
        print(f"Başlık satırı {header_row} kullanılarak veri yeniden düzenleniyor")
        headers = df.iloc[header_row]
        data = df.iloc[header_row+1:].reset_index(drop=True)
        data.columns = headers
        df = data
        print(f"Yeni sütun başlıkları: {list(df.columns)}")
    
    # Sütun isimleri analizi ve eşleştirme
    date_col = None
    desc_col = None
    amount_col = None
    debit_col = None
    credit_col = None
    balance_col = None
    
    for col in df.columns:
        col_lower = str(col).lower()
        # Tarih sütununu bul
        if 'tarih' in col_lower or 'date' in col_lower:
            date_col = col
            print(f"Tarih sütunu tespit edildi: {col}")
        # Açıklama sütununu bul
        elif 'açıklama' in col_lower or 'aciklama' in col_lower or 'explain' in col_lower or 'desc' in col_lower:
            desc_col = col
            print(f"Açıklama sütunu tespit edildi: {col}")
        # Tutar sütununu bul
        elif 'tutar' in col_lower or 'amount' in col_lower:
            amount_col = col
            print(f"Tutar sütunu tespit edildi: {col}")
        # Borç sütununu bul
        elif 'borç' in col_lower or 'borc' in col_lower or 'debit' in col_lower:
            debit_col = col
            print(f"Borç sütunu tespit edildi: {col}")
        # Alacak sütununu bul
        elif 'alacak' in col_lower or 'credit' in col_lower:
            credit_col = col
            print(f"Alacak sütunu tespit edildi: {col}")
        # Bakiye sütununu bul
        elif 'bakiye' in col_lower or 'balance' in col_lower:
            balance_col = col
            print(f"Bakiye sütunu tespit edildi: {col}")
    
    # Standardize edilmiş DataFrame'i oluştur
    
    # Tarih sütununu standardize et
    if date_col:
        standardized_df["Tarih"] = df[date_col]
        print(f"Tarih sütunu kullanılıyor: {date_col}")
    elif "date_col" in bank_format and bank_format["date_col"] in df.columns:
        standardized_df["Tarih"] = df[bank_format["date_col"]]
        print(f"Banka formatından Tarih sütunu kullanılıyor: {bank_format['date_col']}")
    else:
        standardized_df["Tarih"] = ""
        print("Tarih sütunu bulunamadı")
    
    # Açıklama sütununu standardize et
    if desc_col:
        standardized_df["Açıklama"] = df[desc_col]
        print(f"Açıklama sütunu kullanılıyor: {desc_col}")
    elif "description_col" in bank_format and bank_format["description_col"] in df.columns:
        standardized_df["Açıklama"] = df[bank_format["description_col"]]
        print(f"Banka formatından Açıklama sütunu kullanılıyor: {bank_format['description_col']}")
    else:
        standardized_df["Açıklama"] = ""
        print("Açıklama sütunu bulunamadı")
    
    # Tutar sütununu standardize et
    if debit_col and credit_col:
        standardized_df["Tutar"] = df[credit_col].fillna(0).astype(float) - df[debit_col].fillna(0).astype(float)
        print(f"Borç ve Alacak sütunları birleştiriliyor: {debit_col} ve {credit_col}")
    elif amount_col:
        standardized_df["Tutar"] = df[amount_col]
        print(f"Tutar sütunu kullanılıyor: {amount_col}")
    elif "amount_col" in bank_format and bank_format["amount_col"] in df.columns:
        standardized_df["Tutar"] = df[bank_format["amount_col"]]
        print(f"Banka formatından Tutar sütunu kullanılıyor: {bank_format['amount_col']}")
    else:
        standardized_df["Tutar"] = 0
        print("Tutar sütunu bulunamadı")
    
    # Bakiye sütununu standardize et (opsiyonel)
    if balance_col:
        standardized_df["Bakiye"] = df[balance_col]
        print(f"Bakiye sütunu kullanılıyor: {balance_col}")
    elif "balance_col" in bank_format and bank_format["balance_col"] in df.columns:
        standardized_df["Bakiye"] = df[bank_format["balance_col"]]
        print(f"Banka formatından Bakiye sütunu kullanılıyor: {bank_format['balance_col']}")
    
    # Bazı işlemler başarısız olmuş olabilir, boş kayıtları temizle
    if len(standardized_df) > 0:
        print(f"Standardizasyon tamamlandı. Sonuç DataFrame boyutu: {standardized_df.shape}")
        return standardized_df
    
    # Eğer hiçbir sütun eşleşmediyse, basit bir çözüm dene (ilk 4 sütunu al)
    print("Hiçbir sütun uygun şekilde eşleşmedi, basit bir çözüm deneniyor...")
    if len(df.columns) >= 3:
        numeric_cols = df.select_dtypes(include=['number']).columns
        string_cols = df.select_dtypes(include=['object']).columns
        
        # En azından bir tarih, bir açıklama ve bir tutar sütunu oluştur
        standardized_df["Tarih"] = df.iloc[:, 0] if len(df.columns) > 0 else ""
        standardized_df["Açıklama"] = df.iloc[:, 1] if len(df.columns) > 1 else ""
        
        # Sayısal bir sütun varsa onu tutar olarak kullan
        if len(numeric_cols) > 0:
            standardized_df["Tutar"] = df[numeric_cols[0]]
        else:
            standardized_df["Tutar"] = df.iloc[:, 2] if len(df.columns) > 2 else 0
    
    print(f"Alternatif standardizasyon tamamlandı. Sonuç DataFrame boyutu: {standardized_df.shape}")
    return standardized_df

def parse_bank_statement(df, file_name=None, bank_format=None):
    """
    Banka ekstresini ayrıştır
    """
    print(f"Banka ekstresi ayrıştırılıyor... Dosya adı: {file_name}")
    print(f"Gelen DataFrame boyutu: {df.shape}")
    
    # Önce dosya adından banka tipini tespit etmeye çalış (yeni eklenen fonksiyon)
    if bank_format is None and file_name is not None:
        bank_format = identify_bank_from_filename(file_name)
        if bank_format:
            print(f"Dosya adından banka formatı algılandı: {bank_format['name']}")
    
    # Eğer dosya adından tespit edilemediyse, içerik analizi yap
    if bank_format is None:
        print("Dosya adından format algılanamadı, içerik analizine geçiliyor...")
        bank_format = identify_bank_format(df)
    
    if bank_format:
        print(f"Banka formatı algılandı: {bank_format['name']}")
        
        # Format bilgilerini yazdır
        for key, value in bank_format.items():
            if key not in ["processed_df", "content_indicators"] and value is not None:
                print(f"   - {key}: {value}")
        
        # Eğer başlık satırı bulunup işlenmişse, işlenmiş DataFrame'i kullan
        if "processed_df" in bank_format and bank_format["processed_df"] is not None:
            df_to_standardize = bank_format["processed_df"]
            print(f"İşlenmiş DataFrame kullanılıyor. Boyut: {df_to_standardize.shape}")
        else:
            df_to_standardize = df
            print("Orijinal DataFrame kullanılıyor")
        
        # Sütunları yazdır
        print(f"Kullanılacak DataFrame sütunları: {list(df_to_standardize.columns)}")
        
        # DataFrame'i standart formata dönüştür
        return standardize_dataframe(df_to_standardize, bank_format), bank_format["id"]
    else:
        print("Hiçbir banka formatı tanımlanamadı! Genel işlem yapılacak.")
        # Hiçbir format eşleşmediyse, genel bir yaklaşım dene
        return None, "unknown"

def identify_bank_from_filename(file_name):
    """
    Dosya adına bakarak banka tipini belirle - doğal dil anlayışı ile
    """
    if file_name is None:
        return None
    
    # Dosya adını küçük harfe çevir ve uzantısını kaldır
    file_name_lower = file_name.lower()
    file_name_without_ext = file_name_lower
    if '.' in file_name_without_ext:
        file_name_without_ext = file_name_without_ext.rsplit('.', 1)[0]
    
    # Aktif banka formatlarını yükle
    formats = load_bank_formats()
    active_formats = [f for f in formats if f.get("active", True)]
    
    # Yaygın banka adı alternatiflerini tanımla (kısaltmalar, yaygın yazım hataları, vb.)
    bank_alternatives = {
        "is_bankasi": ["iş", "is bank", "isbank", "turkiye is", "türkiye iş", "isbankası", "işbankası"],
        "garanti": ["garanti", "gbankasi", "gbbankasi", "garantibbva", "gbbva", "gb", "garantibankasi"],
        "akbank": ["akbank", "akb", "ak bank", "ak_bank", "akbnk"],
        "ziraat": ["ziraat", "tc ziraat", "tczbankasi", "türkiye cumhuriyeti ziraat", "ziraatbank", "zrt"],
        "yapi_kredi": ["yapı kredi", "yapi kredi", "ykb", "yapi_kredi", "yapıkredi", "yapikredi"],
        "vakifbank": ["vakıfbank", "vakifbank", "vkf", "vakif", "vakıf", "tvakifbank", "türkiye vakıflar", "vakıflar"],
        "halkbank": ["halkbank", "halk bank", "halk bankası", "thb", "türkiye halk"],
        "teb": ["teb", "türk ekonomi", "turk ekonomi", "turkiye ekonomi", "türkiye ekonomi"],
        "finans": ["finansbank", "qnb", "qnb finans", "finansb", "finans bankası", "qnbfinans", "qnbf"],
        "ing": ["ing", "ing bank", "ing bankası", "ing turkey", "ing türkiye"],
        "hsbc": ["hsbc", "hsbc bank", "hsbc türkiye", "hsbc turkey"],
        "denizbank": ["denizbank", "deniz", "dnz", "deniz bank", "dnz bank"],
        "kuveyt_turk": ["kuveyt türk", "kuveyt turk", "kuveytturk", "ktbank", "kt bank", "kuveyt_turk"],
        "albaraka": ["albaraka", "albaraka türk", "alb", "alb turk", "albaraka bankası"]
    }
    
    # Banka adı eşleşmeleri için puanlama yap
    best_match = None
    highest_score = 0
    match_reason = ""
    
    for bank_format in active_formats:
        bank_id = bank_format["id"].lower()
        bank_name = bank_format["name"].lower()
        
        # Dosya adında banka adı veya id'si geçiyorsa puan ver
        score = 0
        current_reason = []
        
        # 1. Tam banka adı eşleşmesi
        if bank_name in file_name_lower:
            score += 1.0
            current_reason.append(f"Tam banka adı '{bank_name}' bulundu")
        
        # 2. Banka ID doğrudan eşleşmesi
        if bank_id in file_name_lower:
            score += 0.8
            current_reason.append(f"Banka ID '{bank_id}' bulundu")
        
        # 3. Alternatif adlar ve kısaltmalar kontrolü
        if bank_id in bank_alternatives:
            for alternative in bank_alternatives[bank_id]:
                # Tam kelime kontrolü (kelime sınırları ile)
                if f" {alternative} " in f" {file_name_without_ext} ":
                    score += 0.9
                    current_reason.append(f"Tam alternatif isim '{alternative}' bulundu")
                # Dosya adında geçiyor mu
                elif alternative in file_name_without_ext:
                    score += 0.7
                    current_reason.append(f"Alternatif isim '{alternative}' bulundu")
        
        # 4. Banka adı kelimelerinin ayrı ayrı kontrolü - her bir kelimeyi kontrol et
        bank_name_parts = bank_name.split()
        for part in bank_name_parts:
            if len(part) >= 3:  # En az 3 karakter uzunluğundaki anlamlı kelimeleri kontrol et
                # Tam kelime kontrolü
                if f" {part} " in f" {file_name_without_ext} ":
                    score += 0.6
                    current_reason.append(f"Tam kelime '{part}' bulundu")
                # İçinde geçiyor mu
                elif part in file_name_without_ext:
                    # Kelime uzunluğuna göre puanı ayarla (daha uzun kelimeler daha güvenilir)
                    word_score = min(0.4, 0.1 + (len(part) / 20))
                    score += word_score
                    current_reason.append(f"Kelime '{part}' bulundu ({word_score:.2f} puan)")
        
        # 5. "Bankası", "Bank", "Ekstrem" gibi kelimelerin varlığını kontrol et
        # Bu kelimeler varsa ve önceki puanlar da bir miktar yüksekse, güvenilirliği artır
        if score > 0.2:
            banking_terms = ["banka", "bank", "ekstre", "hesap", "ekstresi", "rapor", "ozet", "dekont"]
            for term in banking_terms:
                if term in file_name_without_ext:
                    score += 0.1
                    current_reason.append(f"Bankacılık terimi '{term}' ile puan artırıldı")
        
        # En yüksek puanlı eşleşmeyi tut
        if score > highest_score:
            highest_score = score
            best_match = bank_format
            match_reason = ", ".join(current_reason)
    
    # Puanı düşük olsa bile, gerçekten bir banka ismi içeriyorsa kabul et
    # Eşik değerini düşük tut çünkü kısa banka isimleri (TEB, ING gibi) daha az puan alabilir
    if highest_score >= 0.2 and best_match is not None:
        print(f"Dosya adından banka formatı tanımlandı: {best_match['name']} (skor: {highest_score:.2f}, neden: {match_reason})")
        # Kesin olarak banka tipini belirledik, formatı güncelle
        if "processed_df" not in best_match:
            best_match["processed_df"] = None
        return best_match
    
    # Yeterince güvenilir bir eşleşme bulunamadı
    print(f"Dosya adından banka formatı tanımlanamadı: '{file_name}' (en yüksek skor: {highest_score:.2f})")
    return None