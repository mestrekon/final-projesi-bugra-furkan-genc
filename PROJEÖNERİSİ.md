# PROJE ÖNERİSİ

**Seçilen Görev Numarası:** 4

**Ürünün Adı:** Yerel Yapay Zeka Belge Asistanı (Karma Mimari)

**Çözülecek Problem:** Kullanıcıların ve kurumların hassas belgelerini (şirket raporları, araştırma verileri vb.) analiz etmek için bulut tabanlı yapay zeka servislerine (ChatGPT, Claude vb.) yüklemek zorunda kalması, veri gizliliği ve güvenlik ihlallerine yol açmaktadır. Ayrıca, internet bağlantısının olmadığı kısıtlı ortamlarda uzun metinlerin, PDF'lerin ve sunumların hızlıca analiz edilip bilgi çıkarımı yapılması mevcut araçlarla mümkün olmamaktadır.

**Hedef Kullanıcı:** Hassas verilerle çalışan avukatlar, kurumsal şirket çalışanları, internet kısıtlaması olan veya veri mahremiyetine önem veren üniversite öğrencileri, akademisyenler ve araştırmacılar.

**Kullanılacak Veri veya Bilgi Kaynakları:** Kullanıcının kendi yerel bilgisayarından sisteme sürükle-bırak yöntemiyle aktaracağı, dışa kapalı **TXT, PDF ve PPTX (PowerPoint)** formatlarındaki metin ve sunum belgeleri. Sistem bu belgelerdeki bağlamı (context) bilgi kaynağı olarak kullanacaktır.

**Kullanılması Planlanan Teknolojiler:** * **Ana Programlama Dili:** Python 3.10+
* **Arayüz (GUI) Geliştirme:** PyQt5 (Asenkron QThread mimarisi ile)
* **Yerel Dil Modeli (LLM) Motoru:** Ollama (Qwen 2.5:7b modeli)
* **Opsiyonel Bulut API:** OpenAI API (GPT-3.5/4)
* **Belge Ayrıştırma Kütüphaneleri:** `pypdf`, `python-pptx`

**Beklenen Ürün Çıktısı:** Tamamen çevrimdışı çalışabilen, modern bir masaüstü kullanıcı arayüzüne (aydınlık/karanlık mod) sahip, sürükle-bırak özelliği ile çoklu belge formatlarını okuyabilen ve kullanıcının belgeler üzerinde soru-cevap yapmasına olanak tanıyan donma karşıtı (asenkron) çalışan bir masaüstü uygulaması.

**Ürünün Diğer Çalışmalardan Ayrılan Yönü:** Piyasadaki diğer belge asistanları (örneğin ChatPDF) tamamen bulut ve internet bağımlısıdır. Bu ürün ise "Sıfır Güven (Zero-Trust)" gizlilik ilkesiyle verileri bilgisayardan dışarı çıkarmaz. En büyük yeniliği ise **Karma (Fallback) Mimari** kullanmasıdır: Sistem varsayılan olarak cihaz donanımında yerel modelle çalışır, ancak kullanıcı hız talep ettiğinde ve internet erişimi olduğunda dinamik olarak bulut API'sine (OpenAI) geçiş yapabilir. İnternet kesildiğinde sistem çökmez, otomatik olarak yerel işlemci tabanlı okumaya geri döner.