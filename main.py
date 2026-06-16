import sys
import os
import socket
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QCheckBox, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pypdf import PdfReader
from pptx import Presentation
import ollama
from openai import OpenAI

# --- Internet Kontrolü ---
def internet_var_mi():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

# --- Arka Plan İşçisi (Donmayı Engeller) ---
class YapayZekaIscisi(QThread):
    yanit_geldi = pyqtSignal(str, str)

    def __init__(self, soru, metin, api_key, openai_zorla):
        super().__init__()
        self.soru = soru
        self.metin = metin
        self.api_key = api_key
        self.openai_zorla = openai_zorla

    def run(self):
        sinirli_metin = self.metin[-7000:] if len(self.metin) > 7000 else self.metin
        sistem_talimati = f"Sen cihaz üzerinde çalışan gizlilik odaklı kurumsal bir asistansın. Verilen BELGELER dışında bilgi kullanma.\n\nBELGELER:\n{sinirli_metin}"
        used_model = "Yerel Model (Qwen2.5:7b)"
        
        # Eğer kullanıcı bulut modunu seçtiyse ve bir API anahtarı girdiyse
        if self.openai_zorla and self.api_key and internet_var_mi():
            try:
                # Akıllı API Yönlendirmesi (Groq mu, OpenAI mı?)
                if self.api_key.startswith("gsk_"):
                    client = OpenAI(api_key=self.api_key, base_url="https://api.groq.com/openai/v1")
                    model_secimi = "llama3-8b-8192"
                    used_model = "Bulut Model (Groq Llama-3)"
                else:
                    client = OpenAI(api_key=self.api_key)
                    model_secimi = "gpt-3.5-turbo"
                    used_model = "Bulut Model (OpenAI GPT)"

                response = client.chat.completions.create(
                    model=model_secimi,
                    messages=[
                        {"role": "system", "content": sistem_talimati},
                        {"role": "user", "content": self.soru}
                    ],
                    temperature=0.1, max_tokens=500
                )
                self.yanit_geldi.emit(response.choices[0].message.content, used_model)
                return
            except Exception as e:
                used_model = "Yerel Model (Qwen2.5) - Fallback"

        # Bulut başarısız olursa veya seçilmediyse Yerel Modele (Ollama) dön
        try:
            cevap = ollama.chat(model='qwen2.5:7b', messages=[
                {'role': 'system', 'content': sistem_talimati},
                {'role': 'user', 'content': self.soru}
            ], options={'temperature': 0.1, 'num_predict': 300, 'num_ctx': 4096})
            self.yanit_geldi.emit(cevap['message']['content'], used_model)
        except Exception as e:
            self.yanit_geldi.emit(f"❌ Hata: Yerel model çalıştırılamadı. Modelin inmesini bekleyin veya geçerli bir API anahtarı ile çevrimiçi modu açın. Detay: {str(e)}", "Hata")


# --- Ana Uygulama ---
class YerelAsistanApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yerel Yapay Zeka Belge Asistanı")
        self.resize(1100, 700)
        self.setAcceptDrops(True)
        self.belge_icerigi = ""
        self.karanlik_mod_aktif = True

        self.arayuzu_kur()
        self.temayi_guncelle()
        self.model_kontrol_et()

    def arayuzu_kur(self):
        merkez_widget = QWidget()
        self.setCentralWidget(merkez_widget)
        ana_layout = QHBoxLayout(merkez_widget)
        ana_layout.setContentsMargins(15, 15, 15, 15)
        ana_layout.setSpacing(15)

        # ----------------- SOL PANEL -----------------
        self.sol_panel = QFrame()
        self.sol_panel.setObjectName("Panel")
        self.sol_panel.setFixedWidth(280)
        sol_layout = QVBoxLayout(self.sol_panel)

        belgeler_baslik = QLabel("Belgeler")
        belgeler_baslik.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        
        self.dosya_etiket = QLabel("📂 Dosya veya klasörü\nburaya sürükleyin\n\nTXT • PDF • PPTX")
        self.dosya_etiket.setObjectName("SurukleAlani")
        self.dosya_etiket.setAlignment(Qt.AlignCenter)
        self.dosya_etiket.setMinimumHeight(120)
        
        self.dosya_listesi = QListWidget()
        self.dosya_listesi.setObjectName("DosyaListesi")

        # --- YENİ EKLENEN API KUTUSU ---
        api_baslik = QLabel("🔑 Bulut API Anahtarı (Opsiyonel)")
        api_baslik.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 10px;")
        self.api_girdisi = QLineEdit()
        self.api_girdisi.setPlaceholderText("sk-... veya gsk_...")
        self.api_girdisi.setEchoMode(QLineEdit.Password) # Güvenlik için yazılanları yıldızlı gösterir
        self.api_girdisi.setToolTip("OpenAI veya Groq API anahtarınızı buraya girebilirsiniz.")

        self.btn_belge_temizle = QPushButton("🗑️ Belgeleri Temizle")
        self.btn_belge_temizle.setObjectName("BtnKirmizi")
        self.btn_belge_temizle.clicked.connect(self.belgeleri_temizle)

        self.btn_sohbet_temizle = QPushButton("🧠 Sohbet Hafızasını Temizle")
        self.btn_sohbet_temizle.setObjectName("BtnGri")
        self.btn_sohbet_temizle.clicked.connect(self.sohbeti_temizle)

        self.btn_tema_degistir = QPushButton("☀️ Açık Moda Geç")
        self.btn_tema_degistir.setObjectName("BtnGri")
        self.btn_tema_degistir.clicked.connect(self.tema_degistir)

        # Sol panel öğelerini yerleştir
        sol_layout.addWidget(belgeler_baslik)
        sol_layout.addWidget(self.dosya_etiket)
        sol_layout.addWidget(self.dosya_listesi)
        sol_layout.addWidget(api_baslik)
        sol_layout.addWidget(self.api_girdisi)
        sol_layout.addSpacing(10)
        sol_layout.addWidget(self.btn_belge_temizle)
        sol_layout.addWidget(self.btn_sohbet_temizle)
        sol_layout.addWidget(self.btn_tema_degistir)
        ana_layout.addWidget(self.sol_panel)

        # ----------------- SAĞ PANEL -----------------
        self.sag_panel = QFrame()
        self.sag_panel.setObjectName("Panel")
        sag_layout = QVBoxLayout(self.sag_panel)

        ust_bar_layout = QHBoxLayout()
        baslik_sag = QLabel("Karma Yapay Zeka Belge Asistanı")
        baslik_sag.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.durum_etiketi = QLabel("🟢 Hazır")
        self.durum_etiketi.setObjectName("DurumEtiketi")
        self.durum_etiketi.setAlignment(Qt.AlignRight)
        
        ust_bar_layout.addWidget(baslik_sag)
        ust_bar_layout.addWidget(self.durum_etiketi)

        self.sohbet_ekrani = QTextEdit()
        self.sohbet_ekrani.setReadOnly(True)
        self.sohbet_ekrani.setObjectName("SohbetEkrani")
        self.ilk_mesaji_yazdir()

        self.openai_check = QCheckBox("Çevrimiçi Modu (Bulut API) Kullan")
        
        girdi_layout = QHBoxLayout()
        self.soru_girdisi = QLineEdit()
        self.soru_girdisi.setPlaceholderText("Belgelerle ilgili sorunuzu yazın...")
        self.soru_girdisi.returnPressed.connect(self.soru_sor)
        
        self.btn_gonder = QPushButton("Gönder")
        self.btn_gonder.setObjectName("BtnMavi")
        self.btn_gonder.setFixedWidth(100)
        self.btn_gonder.clicked.connect(self.soru_sor)

        girdi_layout.addWidget(self.soru_girdisi)
        girdi_layout.addWidget(self.btn_gonder)

        sag_layout.addLayout(ust_bar_layout)
        sag_layout.addWidget(self.sohbet_ekrani)
        sag_layout.addWidget(self.openai_check)
        sag_layout.addLayout(girdi_layout)

        ana_layout.addWidget(self.sag_panel)

    def model_kontrol_et(self):
        try:
            sonuc = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
            if "qwen2.5:7b" not in sonuc.stdout:
                self.indirme_uyarisi_goster("Sistemin çevrimdışı çalışabilmesi için Qwen 2.5 (4.7 GB) modelinin indirilmesi gerekiyor.")
        except FileNotFoundError:
            QMessageBox.critical(self, "Kritik Eksiklik", "Sistemde 'Ollama' uygulaması bulunamadı!\nLütfen önce ollama.com adresinden indirip kurun.")
        except Exception:
            pass

    def indirme_uyarisi_goster(self, mesaj):
        kutu = QMessageBox(self)
        kutu.setWindowTitle("Yerel Model Bulunamadı")
        kutu.setIcon(QMessageBox.Warning)
        kutu.setText(mesaj)
        kutu.setInformativeText("Şimdi indirmek ister misiniz? (İndirme işlemi yeni bir komut penceresinde başlayacaktır).")
        evet_btn = kutu.addButton("Evet, İndir", QMessageBox.AcceptRole)
        kutu.addButton("Hayır, Sadece Çevrimiçi Kullanacağım", QMessageBox.RejectRole)
        kutu.setStyleSheet("QLabel { color: black; }")
        kutu.exec_()
        if kutu.clickedButton() == evet_btn:
            try:
                subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe", "/k", "ollama pull qwen2.5:7b"])
                self.sohbet_ekrani.append("\n⚠️ SİSTEM NOTU: Arka planda model indirmesi başlatıldı.\n")
            except Exception as e:
                self.sohbet_ekrani.append(f"❌ İndirme başlatılamadı: {e}")

    def tema_degistir(self):
        self.karanlik_mod_aktif = not self.karanlik_mod_aktif
        self.btn_tema_degistir.setText("☀️ Açık Moda Geç" if self.karanlik_mod_aktif else "🌙 Karanlık Moda Geç")
        self.temayi_guncelle()

    def temayi_guncelle(self):
        if self.karanlik_mod_aktif:
            self.setStyleSheet("""
                QMainWindow { background-color: #0b0c10; }
                QFrame#Panel { background-color: #15171e; border-radius: 8px; border: 1px solid #222; }
                QLabel { color: #ffffff; font-family: 'Segoe UI', Arial; }
                QLabel#DurumEtiketi { color: #4caf50; font-weight: bold; }
                QLabel#SurukleAlani { background-color: #1a1d24; border: 2px dashed #333; border-radius: 8px; color: #888; font-size: 13px; }
                QListWidget#DosyaListesi { background-color: #0b0c10; border: 1px solid #222; border-radius: 6px; color: #ddd; padding: 5px; }
                QTextEdit#SohbetEkrani { background-color: #0f1115; border: 1px solid #222; border-radius: 6px; color: #ddd; padding: 15px; font-size: 14px; font-family: 'Segoe UI', Arial; }
                QCheckBox { color: #aaa; font-family: 'Segoe UI'; }
                QLineEdit { background-color: #0b0c10; border: 1px solid #333; border-radius: 6px; padding: 10px; color: white; font-size: 14px; }
                QLineEdit:focus { border: 1px solid #0078D7; }
                QPushButton { padding: 10px; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; border: none; }
                QPushButton#BtnMavi { background-color: #0078D7; color: white; }
                QPushButton#BtnMavi:hover { background-color: #005a9e; }
                QPushButton#BtnKirmizi { background-color: #3b1f1f; color: #ff9999; border: 1px solid #552222; }
                QPushButton#BtnKirmizi:hover { background-color: #4a2727; }
                QPushButton#BtnGri { background-color: #22252b; color: #ccc; border: 1px solid #333; }
                QPushButton#BtnGri:hover { background-color: #2d3139; }
                QPushButton:disabled { background-color: #222; color: #555; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #eef0f4; }
                QFrame#Panel { background-color: #ffffff; border-radius: 8px; border: 1px solid #ccc; }
                QLabel { color: #111111; font-family: 'Segoe UI', Arial; }
                QLabel#DurumEtiketi { color: #2e7d32; font-weight: bold; }
                QLabel#SurukleAlani { background-color: #f8f9fa; border: 2px dashed #aaa; border-radius: 8px; color: #555; font-size: 13px; }
                QListWidget#DosyaListesi { background-color: #f4f5f7; border: 1px solid #ddd; border-radius: 6px; color: #333; padding: 5px; }
                QTextEdit#SohbetEkrani { background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 6px; color: #222; padding: 15px; font-size: 14px; font-family: 'Segoe UI', Arial; }
                QCheckBox { color: #444; font-family: 'Segoe UI'; }
                QLineEdit { background-color: #ffffff; border: 1px solid #bbb; border-radius: 6px; padding: 10px; color: #111; font-size: 14px; }
                QLineEdit:focus { border: 1px solid #0078D7; }
                QPushButton { padding: 10px; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; border: none; }
                QPushButton#BtnMavi { background-color: #0078D7; color: white; }
                QPushButton#BtnMavi:hover { background-color: #005a9e; }
                QPushButton#BtnKirmizi { background-color: #ffeaea; color: #c62828; border: 1px solid #ffcaca; }
                QPushButton#BtnKirmizi:hover { background-color: #ffdbdb; }
                QPushButton#BtnGri { background-color: #e0e4e8; color: #333; border: 1px solid #ccc; }
                QPushButton#BtnGri:hover { background-color: #d1d6dc; }
                QPushButton:disabled { background-color: #ddd; color: #999; }
            """)

    def ilk_mesaji_yazdir(self):
        self.sohbet_ekrani.append("🤖 Sistem hazır.\n\nSol panele belge sürükleyip bırakın.\nÇevrimiçi mod için sol tarafa API anahtarınızı (Groq veya OpenAI) girebilirsiniz.\n")

    def sohbeti_temizle(self):
        self.sohbet_ekrani.clear()
        self.ilk_mesaji_yazdir()

    def belgeleri_temizle(self):
        self.belge_icerigi = ""
        self.dosya_listesi.clear()
        self.sohbet_ekrani.append("🗑️ Sistemdeki tüm belgeler silindi.\n")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            yol = url.toLocalFile()
            if os.path.isdir(yol):
                for kok_dizin, _, dosyalar in os.walk(yol):
                    for dosya in dosyalar: self.dosyayi_oku_ve_ekle(os.path.join(kok_dizin, dosya))
            else: self.dosyayi_oku_ve_ekle(yol)

    def dosyayi_oku_ve_ekle(self, dosya_yolu):
        uzanti = dosya_yolu.lower().split('.')[-1]
        if uzanti not in ['txt', 'pdf', 'pptx']: return
        isim = os.path.basename(dosya_yolu)
        icerik = ""
        try:
            if uzanti == 'txt':
                with open(dosya_yolu, 'r', encoding='utf-8') as f: icerik = f.read()
            elif uzanti == 'pdf':
                reader = PdfReader(dosya_yolu)
                for sayfa in reader.pages:
                    metin = sayfa.extract_text()
                    if metin: icerik += metin + "\n"
            elif uzanti == 'pptx':
                prs = Presentation(dosya_yolu)
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"): icerik += shape.text + "\n"
            self.belge_icerigi += f"\n--- {isim} İçeriği ---\n{icerik}\n"
            self.dosya_listesi.addItem(f"📄 {isim}")
        except: pass

    def soru_sor(self):
        soru = self.soru_girdisi.text().strip()
        if not soru or not self.belge_icerigi: return
        
        # API Anahtarı Kontrolü
        girilen_api = self.api_girdisi.text().strip()
        gpt_aktif = self.openai_check.isChecked()
        
        if gpt_aktif and not girilen_api:
            QMessageBox.warning(self, "API Anahtarı Eksik", "Çevrimiçi (Bulut) modunu kullanmak için sol panele geçerli bir API anahtarı girmelisiniz.\nAnahtarınız yoksa çevrimiçi modun işaretini kaldırın.")
            return

        self.sohbet_ekrani.append(f"👤 Sen: {soru}")
        self.soru_girdisi.clear()
        
        self.soru_girdisi.setEnabled(False)
        self.btn_gonder.setEnabled(False)
        self.durum_etiketi.setText("⏳ Düşünüyor...")
        self.durum_etiketi.setStyleSheet("color: #ff9800; font-weight: bold;")

        self.worker = YapayZekaIscisi(soru, self.belge_icerigi, girilen_api, gpt_aktif)
        self.worker.yanit_geldi.connect(self.cevap_yazdir)
        self.worker.start()

    def cevap_yazdir(self, cevap, kullanilan_model):
        self.sohbet_ekrani.append(f"🤖 Asistan ({kullanilan_model}):\n{cevap}\n{'-'*40}\n")
        self.durum_etiketi.setText("🟢 Hazır")
        if self.karanlik_mod_aktif:
            self.durum_etiketi.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self.durum_etiketi.setStyleSheet("color: #2e7d32; font-weight: bold;")
        
        self.soru_girdisi.setEnabled(True)
        self.btn_gonder.setEnabled(True)
        self.soru_girdisi.setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = YerelAsistanApp()
    pencere.show()
    sys.exit(app.exec_())