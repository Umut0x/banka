import streamlit as st
import pandas as pd
import json
import time
import os
import hashlib
import uuid
import io
from datetime import datetime

from bank_config import (
    load_bank_formats, save_bank_formats, add_bank_format,
    update_bank_format, delete_bank_format, get_bank_format
)
from database import clean_old_statements, get_statement_stats, purge_database, get_recent_bank_statements, get_bank_statement

# Şifre güvenliği için sabit bir salt değeri oluştur
SALT = "banka_ekstresi_donusturucu_2024"

# Varsayılan admin şifresi
DEFAULT_ADMIN_PASSWORD = "admin123"  # Hash'lenmiş değil, ilk kurulumda hash'lenecek

# Özelleştirilebilir dosya yolu
CONFIG_DIR = "config"
ADMIN_CONFIG_FILE = os.path.join(CONFIG_DIR, "admin_config.json")

def get_admin_config():
    """
    Yönetici yapılandırmasını yükle
    """
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    if not os.path.exists(ADMIN_CONFIG_FILE):
        # Varsayılan şifreyi hash'le ve kaydet
        hashed_password = hash_password(DEFAULT_ADMIN_PASSWORD)
        default_config = {
            "admin_password": hashed_password,
            "file_retention_days": 90,
            "max_upload_size_mb": 10,
            "last_settings_update": datetime.now().isoformat()
        }
        
        with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        
        return default_config
    
    try:
        with open(ADMIN_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Yönetici yapılandırması yüklenirken hata: {str(e)}")
        # Varsayılan ayarları döndür
        return {
            "admin_password": hash_password(DEFAULT_ADMIN_PASSWORD),
            "file_retention_days": 90,
            "max_upload_size_mb": 10,
            "last_settings_update": datetime.now().isoformat()
        }

def save_admin_config(config):
    """
    Yönetici yapılandırmasını kaydet
    """
    try:
        config["last_settings_update"] = datetime.now().isoformat()
        
        with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        st.error(f"Yönetici yapılandırması kaydedilirken hata: {str(e)}")
        return False

def hash_password(password):
    """
    Şifreyi güvenli bir şekilde hash'leme
    """
    # Salt ile birleştir ve hash'le
    salted_password = password + SALT
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    return hashed

def verify_password(input_password, hashed_password):
    """
    Girilen şifreyi hash'lenmiş değerle karşılaştır
    """
    input_hashed = hash_password(input_password)
    return input_hashed == hashed_password

def admin_panel():
    """
    Admin panel için ana fonksiyon
    """
    st.title("Admin Panel")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Banka Formatları", "Geçmiş İşlemler", "Veritabanı Yönetimi", "Sistem Ayarları"])
    
    with tab1:
        bank_format_management()
    
    with tab2:
        past_transactions()
    
    with tab3:
        database_management()
    
    with tab4:
        system_settings()


def bank_format_management():
    """
    Banka formatları yönetim arayüzü
    """
    st.header("Banka Formatları Yönetimi")
    
    formats = load_bank_formats()
    
    # Mevcut formatları göster
    if formats:
        st.subheader("Mevcut Banka Formatları")
        
        # DataFrame'e çevir
        format_data = []
        for f in formats:
            format_data.append({
                "ID": f["id"],
                "Banka Adı": f["name"],
                "Aktif": "✅" if f.get("active", True) else "❌",
                "Oluşturulma Tarihi": f.get("created_at", "")
            })
        
        format_df = pd.DataFrame(format_data)
        st.dataframe(format_df, use_container_width=True)
        
        # Format düzenleme veya silme
        st.subheader("Format Düzenle veya Sil")
        
        format_id = st.selectbox(
            "Düzenlenecek formatı seçin:",
            options=[f["id"] for f in formats],
            format_func=lambda x: next((f["name"] for f in formats if f["id"] == x), x)
        )
        
        if format_id:
            selected_format = get_bank_format(format_id)
            
            if selected_format:
                with st.form("edit_format_form"):
                    st.write(f"**{selected_format['name']}** Formatını Düzenle")
                    
                    name = st.text_input("Banka Adı", value=selected_format["name"])
                    
                    # Header bilgileri için virgülle ayrılmış liste kabul et
                    header_str = ", ".join(selected_format.get("header_identifier", []))
                    header_input = st.text_input("Başlık Tanımlayıcıları (virgülle ayırın)", value=header_str)
                    
                    date_col = st.text_input("Tarih Sütunu", value=selected_format.get("date_col", ""))
                    desc_col = st.text_input("Açıklama Sütunu", value=selected_format.get("description_col", ""))
                    
                    # Borç/Alacak veya Tutar modeli seçimi
                    model_type = "amount"
                    if "debit_col" in selected_format and "credit_col" in selected_format:
                        model_type = "debit_credit"
                    
                    model_selection = st.radio(
                        "Tutar Modeli",
                        options=["amount", "debit_credit"],
                        format_func=lambda x: "Tek Tutar Sütunu" if x == "amount" else "Ayrı Borç/Alacak Sütunları",
                        index=0 if model_type == "amount" else 1
                    )
                    
                    if model_selection == "amount":
                        amount_col = st.text_input(
                            "Tutar Sütunu", 
                            value=selected_format.get("amount_col", "")
                        )
                        debit_col = ""
                        credit_col = ""
                    else:
                        amount_col = ""
                        debit_col = st.text_input(
                            "Borç Sütunu", 
                            value=selected_format.get("debit_col", "")
                        )
                        credit_col = st.text_input(
                            "Alacak Sütunu", 
                            value=selected_format.get("credit_col", "")
                        )
                    
                    balance_col = st.text_input(
                        "Bakiye Sütunu (opsiyonel)", 
                        value=selected_format.get("balance_col", "")
                    )
                    
                    doc_no_col = st.text_input(
                        "Dekont No Sütunu (opsiyonel)", 
                        value=selected_format.get("document_no_col", "")
                    )
                    
                    skip_rows = st.number_input(
                        "Atlanacak Satır Sayısı", 
                        min_value=0,
                        value=int(selected_format.get("skip_rows", 0))
                    )
                    
                    active = st.checkbox(
                        "Aktif", 
                        value=selected_format.get("active", True)
                    )
                    
                    update_col, delete_col = st.columns(2)
                    
                    with update_col:
                        submit_button = st.form_submit_button("Güncelle", use_container_width=True)
                    
                    with delete_col:
                        delete_button = st.form_submit_button("Sil", type="secondary", use_container_width=True)
                    
                    if submit_button:
                        updated_format = {
                            "id": format_id,
                            "name": name,
                            "header_identifier": [s.strip() for s in header_input.split(",") if s.strip()],
                            "date_col": date_col,
                            "description_col": desc_col,
                            "skip_rows": skip_rows,
                            "active": active
                        }
                        
                        if model_selection == "amount":
                            updated_format["amount_col"] = amount_col
                        else:
                            updated_format["debit_col"] = debit_col
                            updated_format["credit_col"] = credit_col
                        
                        if balance_col:
                            updated_format["balance_col"] = balance_col
                        
                        if doc_no_col:
                            updated_format["document_no_col"] = doc_no_col
                        
                        success, message = update_bank_format(format_id, updated_format)
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    
                    if delete_button:
                        # Silme işlemi için onay iste
                        confirm_key = f"confirm_delete_{uuid.uuid4()}"
                        if st.checkbox(f"'{selected_format['name']}' formatını silmek istediğinizden emin misiniz?", key=confirm_key):
                            success, message = delete_bank_format(format_id)
                            
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
    
    # Yeni format ekleme
    st.subheader("Yeni Banka Formatı Ekle")
    
    with st.form("add_format_form"):
        st.write("Yeni Banka Formatı Bilgileri")
        
        id = st.text_input("Format ID (benzersiz, Latin harfler, rakamlar ve alt çizgi kullanın)")
        name = st.text_input("Banka Adı")
        
        header_input = st.text_input("Başlık Tanımlayıcıları (virgülle ayırın)")
        
        date_col = st.text_input("Tarih Sütunu")
        desc_col = st.text_input("Açıklama Sütunu")
        
        model_selection = st.radio(
            "Tutar Modeli",
            options=["amount", "debit_credit"],
            format_func=lambda x: "Tek Tutar Sütunu" if x == "amount" else "Ayrı Borç/Alacak Sütunları"
        )
        
        if model_selection == "amount":
            amount_col = st.text_input("Tutar Sütunu")
            debit_col = ""
            credit_col = ""
        else:
            amount_col = ""
            debit_col = st.text_input("Borç Sütunu")
            credit_col = st.text_input("Alacak Sütunu")
        
        balance_col = st.text_input("Bakiye Sütunu (opsiyonel)")
        doc_no_col = st.text_input("Dekont No Sütunu (opsiyonel)")
        
        skip_rows = st.number_input("Atlanacak Satır Sayısı", min_value=0, value=0)
        
        active = st.checkbox("Aktif", value=True)
        
        submit_button = st.form_submit_button("Ekle", use_container_width=True)
        
        if submit_button:
            # Form validasyonu
            if not id or not name or not header_input or not date_col or not desc_col:
                st.error("Lütfen en azından ID, Banka Adı, Başlık Tanımlayıcıları, Tarih ve Açıklama sütunlarını doldurun.")
            elif model_selection == "amount" and not amount_col:
                st.error("Tutar sütunu belirtmelisiniz.")
            elif model_selection == "debit_credit" and (not debit_col or not credit_col):
                st.error("Borç ve Alacak sütunlarını belirtmelisiniz.")
            else:
                new_format = {
                    "id": id,
                    "name": name,
                    "header_identifier": [s.strip() for s in header_input.split(",") if s.strip()],
                    "date_col": date_col,
                    "description_col": desc_col,
                    "skip_rows": skip_rows,
                    "active": active
                }
                
                if model_selection == "amount":
                    new_format["amount_col"] = amount_col
                else:
                    new_format["debit_col"] = debit_col
                    new_format["credit_col"] = credit_col
                
                if balance_col:
                    new_format["balance_col"] = balance_col
                
                if doc_no_col:
                    new_format["document_no_col"] = doc_no_col
                
                success, message = add_bank_format(new_format)
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def past_transactions():
    """
    Geçmiş işlemler arayüzü
    """
    st.header("Geçmiş İşlemler")
    
    try:
        # Geçmiş işlemleri getir (daha fazla göster)
        recent_statements = get_recent_bank_statements(30)
        
        if not recent_statements:
            st.info("Henüz kaydedilmiş işlem bulunmamaktadır.")
        else:
            # Son işlemleri tabloda göster
            statements_df = pd.DataFrame(recent_statements)
            statements_df.columns = ["ID", "Yükleme Tarihi", "Dosya Adı", "Banka Tipi"]
            
            # Tarih filtresi
            st.subheader("Filtreleme Seçenekleri")
            col1, col2 = st.columns(2)
            
            with col1:
                bank_types = sorted(list(set([s["bank_type"] for s in recent_statements])))
                selected_bank = st.multiselect(
                    "Banka Tipine Göre Filtrele:",
                    options=["Tümü"] + bank_types,
                    default=["Tümü"]
                )
            
            with col2:
                sort_order = st.radio(
                    "Sıralama:",
                    options=["En Yeniler", "En Eskiler"],
                    horizontal=True
                )
            
            # Filtreleme
            filtered_df = statements_df.copy()
            if selected_bank and "Tümü" not in selected_bank:
                filtered_df = filtered_df[filtered_df["Banka Tipi"].isin(selected_bank)]
            
            # Sıralama
            if sort_order == "En Eskiler":
                filtered_df = filtered_df.sort_values(by="Yükleme Tarihi")
            else:
                filtered_df = filtered_df.sort_values(by="Yükleme Tarihi", ascending=False)
            
            # Tablo başlığı
            st.subheader(f"İşlem Listesi ({len(filtered_df)} kayıt)")
            st.dataframe(filtered_df, use_container_width=True)
            
            # Seçilen kaydı göster
            st.subheader("İşlem Detayları")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_id = st.selectbox(
                    "İşlem detaylarını görüntülemek için bir kayıt seçin:", 
                    filtered_df["ID"].tolist(),
                    format_func=lambda x: f"ID: {x} - {filtered_df[filtered_df['ID'] == x].iloc[0]['Dosya Adı']}"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                refresh_button = st.button("Yenile", use_container_width=True)
            
            if selected_id:
                with st.spinner("Kayıt yükleniyor..."):
                    statement_data = get_bank_statement(selected_id)
                    
                    if statement_data:
                        st.info(f"**Dosya:** {statement_data['file_name']} | **Banka Tipi:** {statement_data['bank_type']} | **Yükleme Tarihi:** {statement_data['upload_date']}")
                        
                        tab1, tab2 = st.tabs(["İşlenmiş Veri", "Ham Veri"])
                        
                        with tab1:
                            # İşlenmiş veriyi göster
                            
                            # Kırmızı renkle gösterme özelliğini uygula
                            def highlight_negative(s):
                                # Borç sütununda değerler varsa kırmızı göster, diğer sütunlar normal kalsın
                                styles = ['color: red' if (c == 'Borç' and x != '') else '' for c, x in zip(s.index, s.values)]
                                return styles
                            
                            # Stil uygulayarak dataframe'i göster
                            styled_df = statement_data['processed_df'].style.apply(highlight_negative, axis=1)
                            st.dataframe(styled_df, use_container_width=True, height=400)
                            
                            # İndirme seçenekleri
                            col1, col2 = st.columns(2)
                            
                            # Create download buttons for different formats
                            excel_buffer = io.BytesIO()
                            statement_data['processed_df'].to_excel(excel_buffer, index=False, engine='openpyxl')
                            excel_buffer.seek(0)
                            
                            csv_buffer = io.BytesIO()
                            statement_data['processed_df'].to_csv(csv_buffer, index=False, encoding='utf-8-sig', sep=';')
                            csv_buffer.seek(0)
                            
                            with col1:
                                st.download_button(
                                    label="Excel Olarak İndir",
                                    data=excel_buffer,
                                    file_name=f"islenmis_banka_ekstresi_{selected_id}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="excel_archive_admin",
                                    use_container_width=True
                                )
                            
                            with col2:
                                st.download_button(
                                    label="CSV Olarak İndir",
                                    data=csv_buffer,
                                    file_name=f"islenmis_banka_ekstresi_{selected_id}.csv",
                                    mime="text/csv",
                                    key="csv_archive_admin",
                                    use_container_width=True
                                )
                                
                        with tab2:
                            # Ham veriyi göster
                            st.dataframe(statement_data['original_df'], use_container_width=True, height=400)
                    else:
                        st.error("Kayıt bulunamadı.")
    
    except Exception as e:
        st.error(f"Geçmiş işlemler yüklenirken bir hata oluştu: {str(e)}")


def database_management():
    """
    Veritabanı yönetim arayüzü
    """
    st.header("Veritabanı Yönetimi")
    
    try:
        # Veritabanı istatistiklerini göster
        stats = get_statement_stats()
        
        if stats:
            # Görsel tasarım için metrikler
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Toplam Kayıt Sayısı", stats["total_statements"])
            
            with col2:
                st.metric("Toplam Dönüştürme", stats["total_conversions"])
            
            with col3:
                st.metric("Son 30 Gün İçindeki Kayıtlar", stats["recent_statements"])
            
            # İstatistik bilgilerini grafikle göster
            if stats["total_statements"] > 0:
                st.subheader("Veritabanı İstatistikleri")
                chart_data = pd.DataFrame({
                    'Kategori': ['Toplam Kayıt', 'Toplam Dönüştürme', 'Son 30 Gün'],
                    'Değer': [stats["total_statements"], stats["total_conversions"], stats["recent_statements"]]
                })
                st.bar_chart(chart_data, x='Kategori', y='Değer', use_container_width=True)
        
        # Eski kayıtları temizleme
        st.subheader("Eski Kayıtları Temizle")
        
        with st.form("clean_old_records_form"):
            days_to_keep = st.number_input(
                "Kaç günden eski kayıtlar silinsin?",
                min_value=1,
                value=90
            )
            
            st.warning("Bu işlem belirtilen süreden eski kayıtları kalıcı olarak silecektir.")
            
            submit_button = st.form_submit_button("Eski Kayıtları Temizle", use_container_width=True)
            
            if submit_button:
                confirm_key = f"confirm_clean_{uuid.uuid4()}"
                if st.checkbox("Bu işlemi gerçekleştirmek istediğinizden emin misiniz? Bu işlem geri alınamaz.", key=confirm_key):
                    with st.spinner("Eski kayıtlar temizleniyor..."):
                        deleted_count = clean_old_statements(days_to_keep)
                        st.success(f"{deleted_count} adet eski kayıt başarıyla silindi.")
                        time.sleep(2)  # Kullanıcının mesajı görmesi için kısa bir bekleme
                        st.rerun()
        
        # Veritabanını tamamen temizleme
        st.subheader("Veritabanını Sıfırla")
        
        with st.form("purge_database_form"):
            st.warning("Bu işlem veritabanındaki TÜM kayıtları silecektir. Bu işlem geri alınamaz!")
            
            confirmation_text = st.text_input("Onaylamak için 'VERITABANINI_SIFIRLA' yazın.")
            
            submit_button = st.form_submit_button("Veritabanını Sıfırla", type="secondary", use_container_width=True)
            
            if submit_button:
                if confirmation_text == "VERITABANINI_SIFIRLA":
                    with st.spinner("Veritabanı sıfırlanıyor..."):
                        success = purge_database()
                        
                        if success:
                            st.success("Veritabanı başarıyla sıfırlandı.")
                            time.sleep(2)  # Kullanıcının mesajı görmesi için kısa bir bekleme
                            st.rerun()
                        else:
                            st.error("Veritabanı sıfırlanırken bir hata oluştu.")
                else:
                    st.error("Onay metni doğru değil. İşlem iptal edildi.")
    
    except Exception as e:
        st.error(f"Veritabanı yönetim işlemleri sırasında bir hata oluştu: {str(e)}")


def system_settings():
    """
    Sistem ayarları arayüzü
    """
    st.header("Sistem Ayarları")
    
    # Yönetici ayarlarını yükle
    admin_config = get_admin_config()
    
    # Dosya yolu ayarları
    st.subheader("Dosya Saklama Ayarları")
    
    with st.form("file_settings_form"):
        st.write("Bu ayarlar, dosyaların nasıl saklanacağını belirler.")
        
        retention_days = st.number_input(
            "Dosya Saklama Süresi (gün)",
            min_value=1,
            value=admin_config.get("file_retention_days", 90)
        )
        
        max_upload_mb = st.number_input(
            "Maksimum Dosya Boyutu (MB)",
            min_value=1,
            value=admin_config.get("max_upload_size_mb", 10)
        )
        
        submit_button = st.form_submit_button("Ayarları Kaydet", use_container_width=True)
        
        if submit_button:
            # Ayarları kaydet
            admin_config["file_retention_days"] = retention_days
            admin_config["max_upload_size_mb"] = max_upload_mb
            
            if save_admin_config(admin_config):
                st.success("Sistem ayarları başarıyla kaydedildi.")
            else:
                st.error("Sistem ayarları kaydedilirken bir hata oluştu.")
    
    # Kullanıcı ayarları
    st.subheader("Admin Şifresini Değiştir")
    
    with st.form("admin_password_form"):
        current_password = st.text_input("Mevcut Şifre", type="password")
        new_password = st.text_input("Yeni Şifre", type="password")
        confirm_password = st.text_input("Yeni Şifre (Tekrar)", type="password")
        
        submit_button = st.form_submit_button("Şifreyi Değiştir", use_container_width=True)
        
        if submit_button:
            if not current_password or not new_password or not confirm_password:
                st.error("Lütfen tüm alanları doldurun.")
            elif new_password != confirm_password:
                st.error("Yeni şifreler eşleşmiyor.")
            elif not verify_password(current_password, admin_config.get("admin_password", "")):
                st.error("Mevcut şifre yanlış.")
            else:
                # Şifreyi değiştir
                admin_config["admin_password"] = hash_password(new_password)
                
                if save_admin_config(admin_config):
                    st.success("Admin şifresi başarıyla değiştirildi.")
                else:
                    st.error("Şifre değiştirilirken bir hata oluştu.")
    
    # Sistem durumu
    st.subheader("Sistem Durumu")
    
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        st.info("**Son Ayar Güncellemesi:** " + 
                datetime.fromisoformat(admin_config.get("last_settings_update", datetime.now().isoformat()))
                .strftime('%d.%m.%Y %H:%M'))
    
    with status_col2:
        if st.button("Ayarları Sıfırla", use_container_width=True):
            confirm_key = f"confirm_reset_{uuid.uuid4()}"
            if st.checkbox("Tüm sistem ayarlarını varsayılana sıfırlamak istediğinizden emin misiniz?", key=confirm_key):
                # Dosyayı sil
                if os.path.exists(ADMIN_CONFIG_FILE):
                    os.remove(ADMIN_CONFIG_FILE)
                
                # Varsayılan ayarları getir
                get_admin_config()
                st.success("Sistem ayarları varsayılana döndürüldü.")
                time.sleep(2)
                st.rerun()


def is_admin():
    """
    Kullanıcının admin olup olmadığını kontrol et
    """
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    return st.session_state.admin_authenticated