import os
import json
import pandas as pd
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, ForeignKey, func, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta

# PostgreSQL veritabanı URL'sini çevresel değişkenden al
DATABASE_URL = os.environ.get("DATABASE_URL")

# Global değişken - veritabanı bağlantısı durumunu kontrol etmek için
db_available = False

# SQLAlchemy engine oluştur (PostgreSQL için)
try:
    print(f"PostgreSQL veritabanı bağlantısı kuruluyor...")
    # PostgreSQL veritabanı bağlantısı oluştur
    engine = create_engine(DATABASE_URL)
    # Test bağlantısı
    connection = engine.connect()
    connection.close()
    print("PostgreSQL veritabanı bağlantısı başarıyla kuruldu!")
    db_available = True
except Exception as e:
    print(f"PostgreSQL veritabanı bağlantısı kurulamadı: {str(e)}")
    print("Uygulama veritabanı olmadan çalışmaya devam edecek.")
    engine = None

Base = declarative_base()
Session = None
if engine:
    Session = sessionmaker(bind=engine)

# Veritabanı modelleri
class BankStatement(Base):
    __tablename__ = 'bank_statements'
    
    id = Column(Integer, primary_key=True)
    upload_date = Column(DateTime, default=datetime.now)
    file_name = Column(String)
    bank_type = Column(String)
    original_data = Column(JSON)  # PostgreSQL'in native JSON desteği
    processed_data = Column(JSON)  # PostgreSQL'in native JSON desteği
    
    conversions = relationship("Conversion", back_populates="bank_statement")
    
class Conversion(Base):
    __tablename__ = 'conversions'
    
    id = Column(Integer, primary_key=True)
    bank_statement_id = Column(Integer, ForeignKey('bank_statements.id'))
    conversion_date = Column(DateTime, default=datetime.now)
    conversion_format = Column(String)
    conversion_settings = Column(JSON)  # PostgreSQL'in native JSON desteği
    
    bank_statement = relationship("BankStatement", back_populates="conversions")

# Veritabanı işlemleri
def save_bank_statement(file_name, bank_type, original_df, processed_df):
    """
    Banka ekstresini veritabanına kaydet
    """
    # Veritabanı bağlantısı yoksa işlem yapılmaz
    if not db_available or Session is None:
        print("Veritabanı bağlantısı bulunmadığı için kayıt yapılamıyor")
        return None
        
    try:
        session = Session()
        
        # DataFrame'leri JSON formatına dönüştür
        # orient='split' kullanarak daha iyi sıkıştırma sağlayalım ve daha az veri saklayalım
        original_data = json.loads(original_df.to_json(orient='split', date_format='iso'))
        processed_data = json.loads(processed_df.to_json(orient='split', date_format='iso'))
        
        # Yeni kayıt oluştur
        new_statement = BankStatement(
            file_name=file_name,
            bank_type=bank_type,
            original_data=original_data,
            processed_data=processed_data
        )
        
        session.add(new_statement)
        session.commit()
        
        statement_id = new_statement.id
        session.close()
        
        print(f"Banka ekstresi başarıyla kaydedildi. ID: {statement_id}")
        return statement_id
    
    except Exception as e:
        print(f"Veritabanı kaydetme hatası: {str(e)}")
        if 'session' in locals() and session:
            session.rollback()
            session.close()
        return None

def save_conversion(bank_statement_id, conversion_format, settings=None):
    """
    Dönüştürme işlemini veritabanına kaydet
    """
    # Veritabanı bağlantısı yoksa işlem yapılmaz
    if not db_available or Session is None:
        print("Veritabanı bağlantısı bulunmadığı için dönüşüm kaydedilemedi")
        return None
        
    try:
        session = Session()
        
        if settings is None:
            settings = {}
        
        # Yeni dönüştürme kaydı oluştur
        new_conversion = Conversion(
            bank_statement_id=bank_statement_id,
            conversion_format=conversion_format,
            conversion_settings=settings
        )
        
        session.add(new_conversion)
        session.commit()
        
        conversion_id = new_conversion.id
        session.close()
        
        return conversion_id
    
    except Exception as e:
        print(f"Dönüşüm kaydetme hatası: {str(e)}")
        if 'session' in locals() and session:
            session.rollback()
            session.close()
        return None

def get_recent_bank_statements(limit=10):
    """
    En son yüklenen banka ekstrelerini al
    """
    # Veritabanı bağlantısı yoksa boş liste döndür
    if not db_available or Session is None:
        print("Veritabanı bağlantısı bulunmadığı için son kayıtlar alınamadı")
        return []
        
    try:
        session = Session()
        statements = session.query(BankStatement).order_by(BankStatement.upload_date.desc()).limit(limit).all()
        
        result = []
        for stmt in statements:
            result.append({
                'id': stmt.id,
                'upload_date': stmt.upload_date.strftime('%d.%m.%Y %H:%M'),
                'file_name': stmt.file_name,
                'bank_type': stmt.bank_type
            })
        
        session.close()
        return result
    
    except Exception as e:
        print(f"Kayıtları alma hatası: {str(e)}")
        if 'session' in locals() and session:
            session.close()
        return []

def get_bank_statement(statement_id):
    """
    Belirli bir banka ekstresini ID'ye göre al
    """
    # Veritabanı bağlantısı yoksa None döndür
    if not db_available or Session is None:
        print("Veritabanı bağlantısı bulunmadığı için kayıt alınamadı")
        return None
        
    try:
        session = Session()
        statement = session.query(BankStatement).filter(BankStatement.id == statement_id).first()
        
        if statement:
            try:
                # JSON verisini DataFrame'e dönüştür
                if 'columns' in statement.original_data and 'data' in statement.original_data:
                    # split formatını kullan
                    original_df = pd.DataFrame(
                        data=statement.original_data.get('data', []),
                        columns=statement.original_data.get('columns', [])
                    )
                else:
                    # eski format veya records formatı ise
                    original_df = pd.DataFrame(statement.original_data)
                
                if 'columns' in statement.processed_data and 'data' in statement.processed_data:
                    # split formatını kullan
                    processed_df = pd.DataFrame(
                        data=statement.processed_data.get('data', []),
                        columns=statement.processed_data.get('columns', [])
                    )
                else:
                    # eski format veya records formatı ise
                    processed_df = pd.DataFrame(statement.processed_data)
                
                result = {
                    'id': statement.id,
                    'upload_date': statement.upload_date.strftime('%d.%m.%Y %H:%M'),
                    'file_name': statement.file_name,
                    'bank_type': statement.bank_type,
                    'original_df': original_df,
                    'processed_df': processed_df
                }
            except Exception as df_error:
                print(f"DataFrame dönüştürme hatası: {str(df_error)}")
                # Hataya rağmen bazı verileri dönebilmek için
                result = {
                    'id': statement.id,
                    'upload_date': statement.upload_date.strftime('%d.%m.%Y %H:%M'),
                    'file_name': statement.file_name,
                    'bank_type': statement.bank_type,
                    'error': str(df_error)
                }
        else:
            result = None
        
        session.close()
        return result
    
    except Exception as e:
        print(f"Kayıt alma hatası: {str(e)}")
        if 'session' in locals() and session:
            session.close()
        return None

# Veritabanı yönetim fonksiyonları
def get_statement_stats():
    """
    Veritabanı istatistiklerini al
    """
    try:
        session = Session()
        
        # Toplam kayıt sayısı
        total_statements = session.query(func.count(BankStatement.id)).scalar() or 0
        
        # Toplam dönüştürme sayısı
        total_conversions = session.query(func.count(Conversion.id)).scalar() or 0
        
        # Son 30 gün içindeki kayıtlar
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_statements = session.query(func.count(BankStatement.id)).filter(
            BankStatement.upload_date >= thirty_days_ago
        ).scalar() or 0
        
        session.close()
        
        return {
            "total_statements": total_statements,
            "total_conversions": total_conversions,
            "recent_statements": recent_statements
        }
    
    except Exception as e:
        if session:
            session.close()
        return None

def clean_old_statements(days_to_keep=90):
    """
    Belirli bir süreden eski banka ekstresi kayıtlarını temizle
    """
    try:
        session = Session()
        
        # Silinecek kayıtların tarih sınırı
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Silinecek kayıtlar (ve onların dönüşümleri)
        stmt = session.query(BankStatement).filter(BankStatement.upload_date < cutoff_date)
        
        # Önce ilişkili dönüşüm kayıtlarını sil
        statement_ids = [s.id for s in stmt.all()]
        deleted_conversions = session.query(Conversion).filter(
            Conversion.bank_statement_id.in_(statement_ids)
        ).delete(synchronize_session=False)
        
        # Sonra banka ekstresi kayıtlarını sil
        deleted_statements = stmt.delete(synchronize_session=False)
        
        session.commit()
        session.close()
        
        return deleted_statements
    
    except Exception as e:
        if session:
            session.rollback()
            session.close()
        raise e

def purge_database():
    """
    Veritabanındaki tüm kayıtları temizle
    """
    try:
        session = Session()
        
        # Önce dönüşümleri sil
        session.query(Conversion).delete(synchronize_session=False)
        
        # Sonra banka ekstrelerini sil
        session.query(BankStatement).delete(synchronize_session=False)
        
        session.commit()
        session.close()
        
        return True
    
    except Exception as e:
        if session:
            session.rollback()
            session.close()
        return False

# Veritabanı tablolarını oluştur
def create_tables():
    if not engine:
        print("Veritabanı engine olmadığı için tablolar oluşturulamadı")
        return False
        
    try:
        Base.metadata.create_all(engine)
        return True
    except Exception as e:
        print(f"Veritabanı tabloları oluşturulurken hata: {str(e)}")
        return False

# Uygulama başlangıcında tabloları oluşturmayı dene
if db_available and engine:
    try:
        create_tables()
    except Exception as e:
        print(f"Veritabanı oluşturma hatası: {str(e)}")
else:
    print("Veritabanı bağlantısı kurulamadı, tablolar oluşturulmayacak")