import streamlit as st
import pandas as pd
import io
import os
import traceback
from bank_config import identify_bank_format, standardize_dataframe, parse_bank_statement, identify_bank_from_filename
from data_processor import process_data
from utils import clean_description, format_date, convert_to_target_format
from admin import admin_panel, is_admin, get_admin_config, verify_password

# Veritabanı bağlantısı varsa import et, yoksa alternatif kullan
try:
    from database import save_bank_statement, save_conversion, get_recent_bank_statements, get_bank_statement, db_available
except Exception as e:
    print(f"Veritabanı hatası: {str(e)}")
    traceback.print_exc()
    db_available = False
    
    # Dummy fonksiyonlar (veritabanı olmadığında çalışan sürüm için)
    def save_bank_statement(file_name, bank_type, original_df, processed_df):
        return None
        
    def save_conversion(statement_id, conversion_format, settings=None):
        pass
        
    def get_recent_bank_statements(limit=10):
        return []
        
    def get_bank_statement(statement_id):
        return None

st.set_page_config(
    page_title="Banka Ekstresi Dönüştürücü",
    page_icon="💰",
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': """
        ### Banka Ekstresi Dönüştürücü
        Banka ekstrelerini standart muhasebe formatına dönüştüren uygulama.
        
        #### Admin Paneli Girişi:
        Sağ üst taraftaki metin kutusuna "admin" yazıp Enter tuşuna basarak admin paneline erişebilirsiniz.
        """
    }
)

# Set up title and description
st.title("Banka Ekstresi Dönüştürücü")
st.write("Bu uygulama banka ekstrelerini standart muhasebe formatına dönüştürür.")

# File upload section
st.header("Banka Ekstresi Yükle")
uploaded_file = st.file_uploader("Lütfen bir banka ekstresi seçin (CSV veya Excel formatı)", 
                                type=["csv", "xlsx", "xls"])

# Main processing function
def process_bank_statement(file):
    try:
        # Read the file based on its extension
        file_extension = file.name.split('.')[-1].lower()
        file_name = file.name  # Dosya adını al - banka tipini tespit için kullanacağız
        
        if file_extension == 'csv':
            # Try different encodings
            try:
                df = pd.read_csv(file)
            except UnicodeDecodeError:
                df = pd.read_csv(file, encoding='latin1')
        elif file_extension in ['xlsx', 'xls']:
            try:
                # Önce openpyxl ile deneyelim
                df = pd.read_excel(file, engine='openpyxl')
            except Exception as excel_error:
                try:
                    # Eğer openpyxl başarısız olursa, xlrd ile deneyelim (eski xls dosyaları için)
                    if file_extension == 'xls':
                        df = pd.read_excel(file, engine='xlrd')
                    else:
                        # Başka bir yöntem deneyelim - dosyayı bir kez daha okumak
                        file.seek(0)  # Dosya işaretçisini başa al
                        df = pd.read_excel(file)
                except Exception as second_error:
                    # Hala başarısız olursa, daha detaylı bir hata mesajı göster
                    st.error(f"Excel dosyası açılamadı: {str(excel_error)}. Alternatif yöntemlerle de denendi: {str(second_error)}")
                    return None, None, None
        else:
            st.error("Desteklenmeyen dosya formatı. Lütfen CSV veya Excel dosyası yükleyin.")
            return None, None, None
        
        # Önce dosya adını kullanarak banka tipini tespit etmeye çalış
        # Eğer bulunamazsa içerik analizine geç
        bank_format = None
        
        # Dosya adından banka formatını tanımlamaya çalış (yeni eklediğimiz fonksiyon)
        bank_format = identify_bank_from_filename(file_name)
        
        # Eğer dosya adından tanımlayamazsak, içerik analizine geç
        if bank_format is None:
            bank_format = identify_bank_format(df)
        
        if bank_format:
            # Başlık satırı bulunduysa bilgi ver
            if "header_row" in bank_format:
                st.info(f"Başlık satırı dosyanın {bank_format['header_row']+1}. satırında bulundu ve veriler buna göre düzenlendi.")
            
            # Banka formatını kullanarak standart formata dönüştür
            processed_df, bank_type = parse_bank_statement(df, file_name=file_name, bank_format=bank_format)
            st.success(f"{bank_format['name']} ekstresi başarıyla tanımlandı ve işlendi.")
        else:
            # Format tanımlanamadı, genel bir işleme dene
            st.warning("Tanımlanamayan banka ekstresi formatı. Genel işleme uygulanıyor.")
            processed_df = process_data(df)
            bank_type = "unknown"
        
        # Convert to target format
        result_df = convert_to_target_format(processed_df)
        
        # Önemli sütunları kontrol et
        if 'Fiş Tarihi' not in result_df.columns or 'Detay Açıklama' not in result_df.columns or 'Borç' not in result_df.columns or 'Alacak' not in result_df.columns:
            st.error("Hedef format oluşturulurken bir hata oluştu. Gereken tüm sütunlar bulunamadı.")
            return None, None, None
        
        # İşlem başarılı mesajı
        st.success(f"Toplam {len(result_df)} işlem başarıyla işlendi.")
        
        return result_df, df, bank_type
    
    except Exception as e:
        st.error(f"Dosya işlenirken bir hata oluştu: {str(e)}")
        return None, None, None

# Ana menü sekmeleri
tab1, tab2, tab3 = st.tabs(["Yeni Dönüştürme", "Geçmiş Dönüştürmeler", "Admin Paneli"])

with tab1:
    # Process file when uploaded
    if uploaded_file is not None:
        with st.spinner('Dosya işleniyor...'):
            processed_data, original_df, bank_type = process_bank_statement(uploaded_file)
        
        if processed_data is not None:
            # Display preview of the processed data
            st.header("İşlenmiş Veri Önizleme")
            
            # Ayırıcı ve renklendirme için stil fonksiyonu
            def highlight_rows(df):
                # DataFrame'i stil nesnesine çevir
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                
                # Sarı ayırıcı satırı için arka plan rengi
                if 'is_separator' in df.columns:
                    separator_rows = df['is_separator'] == True
                    styles.loc[separator_rows, :] = 'background-color: gold; color: black; font-weight: bold; border-top: 3px solid orange; border-bottom: 3px solid orange;'
                
                # Fiş No sütununa bakarak üst ve alt bölümü belirle (Fiş No: 1 = üst bölüm, Fiş No: 2 = alt bölüm)
                if 'Fiş No' in df.columns:
                    # ÜST BÖLÜM: Sadece Alacak kırmızı olsun
                    if 'Alacak' in df.columns:
                        ust_alacak_rows = (df['Fiş No'] == 1) & (df['Alacak'] != '')
                        styles.loc[ust_alacak_rows, 'Alacak'] = 'color: red'
                    
                    # ALT BÖLÜM: Sadece Borç kırmızı olsun
                    if 'Borç' in df.columns:
                        alt_borc_rows = (df['Fiş No'] == 2) & (df['Borç'] != '')
                        styles.loc[alt_borc_rows, 'Borç'] = 'color: red'
                
                return styles
            
            # Stil uygulayarak dataframe'i göster
            styled_df = processed_data.style.apply(highlight_rows, axis=None)
            
            # is_separator sütununu gizlemek yerine işlemeden önce silelim
            if 'is_separator' in processed_data.columns:
                # Gösterilen veri setinden is_separator sütununu kaldır
                display_df = processed_data.drop(columns=['is_separator'])
                styled_df = display_df.style.apply(highlight_rows, axis=None)
                
            st.dataframe(styled_df, use_container_width=True, height=600)
            
            # Veritabanına kaydet (veritabanı varsa)
            if db_available:
                try:
                    statement_id = save_bank_statement(uploaded_file.name, bank_type, original_df, processed_data)
                except Exception as e:
                    # Hata mesajını logla ama kullanıcıya daha kullanıcı dostu bir mesaj göster
                    print(f"Veritabanı hatası: {str(e)}")
                    st.warning("Veriler geçici olarak kaydedilemedi, ancak dönüştürme başarıyla tamamlandı.")
                    # Veritabanı olmayabilir, bu durumda hatalara sessizce devam edelim
                    db_available = False  # Daha sonraki işlemleri atla
                    statement_id = None
            else:
                st.info("Veritabanı bağlantısı olmadığı için bu işlem kaydedilmedi.")
                statement_id = None
            
            # Download section
            st.header("İşlenmiş Veriyi İndir")
            
            # Create download buttons for different formats
            excel_buffer = io.BytesIO()
            # Excel indirirken sadece is_separator sütununu kaldır
            download_df = processed_data.drop(columns=['is_separator']) if 'is_separator' in processed_data.columns else processed_data
            download_df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            
            csv_buffer = io.BytesIO()
            # CSV'de sütunların düzgün ayrılması için sep parametresini belirtiyoruz
            # Sadece is_separator sütununu kaldır
            download_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig', sep=';')
            csv_buffer.seek(0)
            
            col1, col2 = st.columns(2)
            
            with col1:
                dl_clicked = st.download_button(
                    label="Excel Olarak İndir",
                    data=excel_buffer,
                    file_name="islenmis_banka_ekstresi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                if dl_clicked and statement_id:
                    try:
                        save_conversion(statement_id, 'excel', {'format': 'xlsx'})
                    except Exception as e:
                        st.error(f"Dönüşüm kaydedilirken hata oluştu: {str(e)}")
            
            with col2:
                dl_clicked = st.download_button(
                    label="CSV Olarak İndir",
                    data=csv_buffer,
                    file_name="islenmis_banka_ekstresi.csv",
                    mime="text/csv"
                )
                
                if dl_clicked and statement_id:
                    try:
                        save_conversion(statement_id, 'csv', {'format': 'csv', 'encoding': 'utf-8-sig'})
                    except Exception as e:
                        st.error(f"Dönüşüm kaydedilirken hata oluştu: {str(e)}")

with tab2:
    st.header("Geçmiş İşlemler")
    
    if not db_available:
        st.warning("Veritabanı bağlantısı şu anda kullanılamıyor. Geçmiş kayıtlara erişilemez.")
        st.info("Veritabanı olmadan da dönüştürme işlemlerini yapabilir ve sonuçları indirebilirsiniz.")
    else:
        try:
            recent_statements = get_recent_bank_statements(20)
            
            if not recent_statements:
                st.info("Henüz kaydedilmiş bir işlem bulunmamaktadır.")
            else:
                # Son işlemleri tabloda göster
                statements_df = pd.DataFrame(recent_statements)
                statements_df.columns = ["ID", "Yükleme Tarihi", "Dosya Adı", "Banka Tipi"]
                st.dataframe(statements_df, use_container_width=True)
                
                # Seçilen kaydı göster
                selected_id = st.selectbox("İşlem detaylarını görüntülemek için bir kayıt seçin:", 
                                          statements_df["ID"].tolist(),
                                          format_func=lambda x: f"ID: {x}")
                
                if selected_id:
                    with st.spinner("Kayıt yükleniyor..."):
                        statement_data = get_bank_statement(selected_id)
                        
                        if statement_data:
                            st.subheader(f"Dosya: {statement_data['file_name']}")
                            st.text(f"Banka Tipi: {statement_data['bank_type']}")
                            st.text(f"Yükleme Tarihi: {statement_data['upload_date']}")
                            
                            st.markdown("### İşlenmiş Veri")
                            
                            # Ayırıcı ve renklendirme için stil fonksiyonu
                            def highlight_rows(df):
                                # DataFrame'i stil nesnesine çevir
                                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                                
                                # Sarı ayırıcı satırı için arka plan rengi
                                if 'is_separator' in df.columns:
                                    separator_rows = df['is_separator'] == True
                                    styles.loc[separator_rows, :] = 'background-color: gold; color: black; font-weight: bold; border-top: 3px solid orange; border-bottom: 3px solid orange;'
                                
                                # Fiş No sütununa bakarak üst ve alt bölümü belirle (Fiş No: 1 = üst bölüm, Fiş No: 2 = alt bölüm)
                                if 'Fiş No' in df.columns:
                                    # ÜST BÖLÜM: Sadece Alacak kırmızı olsun
                                    if 'Alacak' in df.columns:
                                        ust_alacak_rows = (df['Fiş No'] == 1) & (df['Alacak'] != '')
                                        styles.loc[ust_alacak_rows, 'Alacak'] = 'color: red'
                                    
                                    # ALT BÖLÜM: Sadece Borç kırmızı olsun
                                    if 'Borç' in df.columns:
                                        alt_borc_rows = (df['Fiş No'] == 2) & (df['Borç'] != '')
                                        styles.loc[alt_borc_rows, 'Borç'] = 'color: red'
                                
                                return styles
                            
                            # Stil uygulayarak dataframe'i göster
                            styled_df = statement_data['processed_df'].style.apply(highlight_rows, axis=None)
                            
                            # is_separator sütununu gizlemek yerine işlemeden önce silelim
                            if 'is_separator' in statement_data['processed_df'].columns:
                                # Gösterilen veri setinden is_separator sütununu kaldır
                                display_df = statement_data['processed_df'].drop(columns=['is_separator'])
                                styled_df = display_df.style.apply(highlight_rows, axis=None)
                                
                            st.dataframe(styled_df, use_container_width=True, height=600)
                            
                            # İndirme seçenekleri
                            col1, col2 = st.columns(2)
                            
                            # Create download buttons for different formats
                            excel_buffer = io.BytesIO()
                            # Excel indirirken sadece is_separator sütununu kaldır
                            archive_download_df = statement_data['processed_df'].drop(columns=['is_separator']) if 'is_separator' in statement_data['processed_df'].columns else statement_data['processed_df']
                            archive_download_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                            excel_buffer.seek(0)
                            
                            csv_buffer = io.BytesIO()
                            # CSV'de sütunların düzgün ayrılması için sep parametresini belirtiyoruz
                            # Sadece is_separator sütununu kaldır
                            archive_download_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig', sep=';')
                            csv_buffer.seek(0)
                            
                            with col1:
                                dl_clicked = st.download_button(
                                    label="Excel Olarak İndir",
                                    data=excel_buffer,
                                    file_name=f"islenmis_banka_ekstresi_{selected_id}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="excel_archive"
                                )
                                
                                if dl_clicked:
                                    try:
                                        save_conversion(selected_id, 'excel', {'format': 'xlsx', 'archive': True})
                                    except Exception as e:
                                        st.error(f"Dönüşüm kaydedilirken hata oluştu: {str(e)}")
                            
                            with col2:
                                dl_clicked = st.download_button(
                                    label="CSV Olarak İndir",
                                    data=csv_buffer,
                                    file_name=f"islenmis_banka_ekstresi_{selected_id}.csv",
                                    mime="text/csv",
                                    key="csv_archive"
                                )
                                
                                if dl_clicked:
                                    try:
                                        save_conversion(selected_id, 'csv', {'format': 'csv', 'encoding': 'utf-8-sig', 'archive': True})
                                    except Exception as e:
                                        st.error(f"Dönüşüm kaydedilirken hata oluştu: {str(e)}")
                        else:
                            st.error("Kayıt bulunamadı.")
                            
        except Exception as e:
            st.error(f"Geçmiş işlemler yüklenirken bir hata oluştu: {str(e)}")

# Instructions section
with st.expander("Nasıl Kullanılır?"):
    st.write("""
    1. Banka ekstrenizi CSV veya Excel formatında yükleyin.
    2. Uygulama otomatik olarak dosyayı işleyecek ve standart muhasebe formatına dönüştürecektir.
    3. İşlenen verinin önizlemesini göreceksiniz.
    4. İşlenen veriyi Excel veya CSV formatında indirebilirsiniz.
    5. İşlenen veriler veritabanında saklanır ve 'Geçmiş Dönüştürmeler' sekmesinden erişebilirsiniz.
    
    **Desteklenen Banka Formatları:**
    - Garanti Bankası
    - İş Bankası
    - Akbank
    - Ziraat Bankası
    - Diğer bankalar için Admin Panelden yeni format ekleyebilirsiniz
    
    **Çıktı Formatı:**
    Fiş No | Fiş Tarihi | Fiş Açıklama | Hesap Kodu | Evrak No | Evrak Tarihi | Detay Açıklama | Borç | Alacak | Miktar | Belge Türü | Para Birimi | Kur | Döviz Tutar
    """)

# Admin paneli içeriği
with tab3:
    # Admin girişi ve panel
    if is_admin():
        # Admin panelini göster
        admin_panel()
    else:
        # Giriş yapmamış durum için bilgi mesajı
        st.info("Admin paneline erişmek için lütfen giriş yapın.")
        
        # Basit bir kart tasarımı
        st.markdown("""
        <style>
        .admin-login-container {
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #e6e6e6;
            background-color: #f8f9fa;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="admin-login-container">', unsafe_allow_html=True)
        st.subheader("Yönetici Girişi")
        
        with st.form("admin_login_form_main"):
            password = st.text_input("Şifre", type="password")
            submit_button = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if submit_button:
                # Yönetici şifresini kontrol et
                admin_config = get_admin_config() if 'get_admin_config' in globals() else None
                
                if admin_config and 'verify_password' in globals():
                    stored_password_hash = admin_config.get("admin_password")
                    if verify_password(password, stored_password_hash):
                        st.session_state.admin_authenticated = True
                        st.rerun()
                    else:
                        st.error("Hatalı şifre. Lütfen tekrar deneyin.")
                elif password == "admin123":  # Varsayılan şifre (geçici çözüm)
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Hatalı şifre. Lütfen tekrar deneyin.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("© 2025 Umut Erdağ. Tüm hakları saklıdır.")
