# language.py
CURRENT_LANG = "tr"      # Varsayılan dil Türkçe
CURRENT_CURRENCY = "USD"  # Varsayılan para birimi Dolar

translations = {
    # --- GENEL KELİMELER & BUTONLAR ---
    "Hata": {"en": "Error", "zh": "错误"},
    "Başarılı": {"en": "Success", "zh": "成功"},
    "Uyarı": {"en": "Warning", "zh": "警告"},
    "Onay": {"en": "Confirm", "zh": "确认"},
    "Hazır": {"en": "Ready", "zh": "准备就绪"},
    "Kapat": {"en": "Close", "zh": "关闭"},
    "İşlemler": {"en": "Actions", "zh": "操作"},
    "Düzenle": {"en": "Edit", "zh": "编辑"},
    "Sil": {"en": "Delete", "zh": "删除"},
    "Kaydet": {"en": "Save", "zh": "保存"},
    "İptal": {"en": "Cancel", "zh": "取消"},
    "Silmek istiyor musunuz?": {"en": "Are you sure you want to delete?", "zh": "您确定要删除吗？"},
    "Silinsin mi?": {"en": "Are you sure to delete?", "zh": "你确定要删除吗？"},
    "Bilgi": {"en": "Information", "zh": "信息"},
    "Tarih:": {"en": "Date:", "zh": "日期："},
    "Teklif No:": {"en": "Offer No:", "zh": "报价单号："},
    "Sayın Yetkili:": {"en": "Dear Sir/Madam:", "zh": "尊敬的先生/女士："},

    # --- PARA BİRİMLERİ ---
    "Para Birimi": {"en": "Currency", "zh": "货币"},
    "Para Birimi:": {"en": "Currency:", "zh": "货币："},
    "Teklif Para Birimi:": {"en": "Offer Currency:", "zh": "报价货币："},
    "USD - Dolar": {"en": "USD - Dollar", "zh": "USD - 美元"},
    "EUR - Euro": {"en": "EUR - Euro", "zh": "EUR - 欧元"},
    "RMB - Yuan": {"en": "RMB - Yuan", "zh": "RMB - 人民币"},

    # --- YENİ EKLENEN KELİMELER (KATEGORİ, ADET, KOPYALAMA) ---
    "Adet": {"en": "Qty", "zh": "数量"},
    "Adet:": {"en": "Qty:", "zh": "数量："},
    "Makine Adedi:": {"en": "Machine Quantity:", "zh": "机器数量:"},
    "Standart Özellikleri Gizle": {"en": "Hide Standard Specifications", "zh": "隐藏标准规格"},
    "Kategori": {"en": "Category", "zh": "类别"},
    "Kategoriler": {"en": "Categories", "zh": "类别"},
    "Tüm Kategoriler": {"en": "All Categories", "zh": "所有类别"},
    "Kategori:": {"en": "Category:", "zh": "类别："},
    "Makine Kategorisi:": {"en": "Machine Category:", "zh": "机器类别："},
    "Donanım Grubu Filtresi:": {"en": "Hardware Group Filter:", "zh": "硬件组过滤器："},
    "Genel / Tüm Makineler": {"en": "General / All Machines", "zh": "通用 / 所有机器"},
    "Diğer Makinalar": {"en": "Other Machines", "zh": "其他机器"},
    "Kategori Adını Giriniz": {"en": "Enter Category Name", "zh": "输入类别名称"},
    "Kategori Adı:": {"en": "Category Name:", "zh": "类别名称："},
    "Kategori Adı": {"en": "Category Name", "zh": "类别名称"},
    "Kategori Düzenleyici": {"en": "Category Editor", "zh": "类别编辑器"},
    "Yeni Kategori Ekle": {"en": "Add New Category", "zh": "添加新类别"},
    "Bu kategoriyi silmek istediğinize emin misiniz? (Makineler silinmez, sadece bu kategori ismi kaybolur).": {
        "en": "Are you sure you want to delete this category? (Machines will not be deleted, only this category name will disappear).", 
        "zh": "您确定要删除此类别吗？（机器不会被删除，只有此类别名称会消失）。"
    },
    "Bu kaydı silmek istediğinize emin misiniz?": {"en": "Are you sure you want to delete this record?", "zh": "您确定要删除这条记录吗？"},
    "Kopya": {"en": "Copy", "zh": "副本"},

    # --- ANA MENÜ (SIDEBAR) ---
    "YÖNETİM PANELİ": {"en": "MANAGEMENT PANEL", "zh": "管理面板"},
    "👥 Müşteri Yönetimi": {"en": "👥 Customer Management", "zh": "👥 客户管理"},
    "📦 Ürün Portföyü (🔒)": {"en": "📦 Product Portfolio (🔒)", "zh": "📦 产品组合 (🔒)"},
    "📄 Yeni Teklif Hazırla": {"en": "📄 Create New Offer", "zh": "📄 创建新报价"},
    "📋 Geçmiş Teklifler": {"en": "📋 Offer History", "zh": "📋 历史报价"},
    "⚙️ Firma / Bayi Ayarları": {"en": "⚙️ Company Settings", "zh": "⚙️ 公司设置"},
    
    # --- YENİ: YÖNETİCİ OTURUMU & SHOWROOM ---
    "🔐 Yönetici Girişi": {"en": "🔐 Admin Login", "zh": "🔐 管理员登录"},
    "🔓 Yönetici Çıkışı": {"en": "🔓 Admin Logout", "zh": "🔓 管理员退出"},
    "Yönetici oturumunu kapatmak istiyor musunuz?": {"en": "Do you want to log out of the admin session?", "zh": "您确定要注销管理员会话吗？"},
    "Yönetici şifresini giriniz:": {"en": "Enter admin password:", "zh": "请输入管理员密码："},
    "Yönetici girişi başarılı. Ürün portföyü kilidi açıldı.": {"en": "Admin login successful. Product portfolio unlocked.", "zh": "管理员登录成功。产品组合已解锁。"},
    "📦 Ürün Portföyü": {"en": "📦 Product Portfolio", "zh": "📦 产品组合"},
    "🖼️ Showroom / Müşteri Galerisi": {"en": "🖼️ Showroom / Customer Gallery", "zh": "🖼️ 展厅 / 客户画廊"},

    # --- DASHBOARD (ANA SAYFA) ---
    "Genel Bakış": {"en": "Overview", "zh": "概览"},
    "Sistem Durumu: Aktif": {"en": "System Status: Active", "zh": "系统状态：活跃"},
    "Hızlı Erişim & Son İşlemler": {"en": "Quick Access & Recent Activities", "zh": "快速访问和近期活动"},
    "Müşteriler": {"en": "Customers", "zh": "客户"},
    "Modeller": {"en": "Models", "zh": "型号"},
    "Makineler": {"en": "Machines", "zh": "机器"},
    "Teklifler": {"en": "Offers", "zh": "报价"},
    "Ürün Portföyüne model eklendiğinde burada sergilenecektir.": {
        "en": "Models will be displayed here when added to the portfolio.",
        "zh": "添加到产品组合时，型号将显示在此处。"
    },

    # --- GÜVENLİK / ŞİFRE ---
    "Güvenlik Doğrulaması": {"en": "Security Verification", "zh": "安全验证"},
    "Ürün portföyüne erişmek için lütfen yetkili şifresini giriniz:": {
        "en": "Please enter the admin password to access:",
        "zh": "请输入管理员密码以访问："
    },
    "Erişim Reddedildi": {"en": "Access Denied", "zh": "拒绝访问"},
    "Hatalı şifre girdiniz!": {"en": "Incorrect password!", "zh": "密码错误！"},

    # --- SHOWROOM (GALERİ) İÇERİĞİ ---
    "Müşteri Showroom & Galeri": {"en": "Customer Showroom & Gallery", "zh": "客户展厅及画廊"},
    "Makine Kategorileri": {"en": "Machine Categories", "zh": "机器类别"},
    "Kategorilere Dön": {"en": "Back to Categories", "zh": "返回类别"},
    "Makine Listesine Dön": {"en": "Back to Machine List", "zh": "返回机器列表"},
    "Bu Makine İçin Teklif Hazırla": {"en": "Create Offer for This Machine", "zh": "为此机器创建报价"},
    "Makine Görselleri": {"en": "Machine Images", "zh": "机器图片"},
    "Standart Özellikler": {"en": "Standard Specs", "zh": "标准规格"},
    "Opsiyonel Donanımlar": {"en": "Optional Equipments", "zh": "可选设备"},
    "Seçime Ekle": {"en": "Add to Selection", "zh": "添加到选择"},

    # --- ENVANTER / MODEL YÖNETİMİ (model_management.py) ---
    "Katalog ve Envanter Yönetimi": {"en": "Catalog & Inventory Management", "zh": "目录与库存管理"},
    "Yeni Makine Ekle": {"en": "Add New Machine", "zh": "添加新机器"},
    "Yeni Donanım Ekle": {"en": "Add New Equipment", "zh": "添加新设备"},
    "Donanım Havuzu": {"en": "Equipment Pool", "zh": "设备池"},
    "Makine Kartı Düzenleyici": {"en": "Machine Card Editor", "zh": "机器卡片编辑器"},
    "Genel Bilgiler": {"en": "General Information", "zh": "基本信息"},
    "Makine Adı:": {"en": "Machine Name:", "zh": "机器名称："},
    "Yurtiçi Fiyat:": {"en": "Domestic Price:", "zh": "国内价格："},
    "Liman Teslim İskontosu:": {"en": "Port Delivery Discount:", "zh": "港口交付折扣："},
    "Liman teslim seçilirse fiyattan düşülecek indirim oranı": {
        "en": "Discount rate to be applied for port delivery",
        "zh": "港口交付适用的折扣率"
    },
    "Resim Yolu:": {"en": "Image Path:", "zh": "图片路径："},
    "Ana Resim Seç": {"en": "Select Main Image", "zh": "选择主图"},
    "📸 Ana Resim Seç": {"en": "📸 Select Main Image", "zh": "📸 选择主图"},
    "Teknik Özellikler": {"en": "Technical Specifications", "zh": "技术规格"},
    "Teknik Özellikler:": {"en": "Technical Specifications:", "zh": "技术规格："},
    "Özellik Ekle": {"en": "Add Specification", "zh": "添加规格"},
    "Bu makine için seçilebilecek uyumlu donanımları belirleyin": {
        "en": "Select compatible equipments for this machine",
        "zh": "为此机器选择兼容设备"
    },
    "Tümünü Seç": {"en": "Select All", "zh": "全选"},
    "Seçimi Temizle": {"en": "Clear Selection", "zh": "清除选择"},
    "UYUMLU EKSTRA DONANIMLAR": {"en": "COMPATIBLE EXTRA EQUIPMENTS", "zh": "兼容的额外设备"},
    "Yukarı Taşı": {"en": "Move Up", "zh": "上移"},
    "Aşağı Taşı": {"en": "Move Down", "zh": "下移"},
    "Görsel Seç": {"en": "Select Image", "zh": "选择图片"},
    "Özellik Görseli Seç": {"en": "Select Spec Image", "zh": "选择规格图片"},
    "Kaldır": {"en": "Remove", "zh": "移除"},
    "Görsel": {"en": "Image", "zh": "图片"},
    "Görsel Yok": {"en": "No Image", "zh": "无图片"},
    "Görsel Bulunamadı": {"en": "Image Not Found", "zh": "未找到图片"},
    "Görsel Bozuk": {"en": "Image Corrupted", "zh": "图片损坏"},
    "Resim bekleniyor...": {"en": "Waiting for image...", "zh": "正在等待图片..."},
    "Başlık (Örn: Kontrol Ünitesi)": {"en": "Title (e.g. Control Unit)", "zh": "标题（如：控制单元）"},
    "Teknik Detay (Örn: Mitsubishi M80)": {"en": "Technical Detail (e.g. Mitsubishi M80)", "zh": "技术细节（如：三菱 M80）"},
    "Donanım / Opsiyon Editörü": {"en": "Equipment / Option Editor", "zh": "设备/选项编辑器"},
    "Donanım Adı:": {"en": "Equipment Name:", "zh": "设备名称："},
    "Fiyat:": {"en": "Price:", "zh": "价格："},
    "Çakışma Özelliği:": {"en": "Conflict Feature:", "zh": "冲突特征："},
    "Çakışma Özelliği (Opsiyonel)": {"en": "Conflict Feature (Optional)", "zh": "冲突特征（可选）"},
    "Teknik Açıklama:": {"en": "Technical Description:", "zh": "技术说明："},
    "Teknik açıklama...": {"en": "Technical description...", "zh": "技术说明..."},
    "Uyumlu Makine Grubu:": {"en": "Compatible Machine Group:", "zh": "兼容机器组："},
    "Resim Seç": {"en": "Select Image", "zh": "选择图片"},
    "Resim Seçmek İçin Tıklayın\n(Yüksek Kalite 200x200 Kare)": {
        "en": "Click to Select Image\n(High Quality 200x200 Square)",
        "zh": "点击选择图片\n（高质量 200x200 正方形）"
    },
    "İPUCU: Bu donanım seçildiğinde, standart listeden çıkarılacak özelliğin başlığını buraya yazın.": {
        "en": "HINT: Type the title of the specification to be removed from the standard list when this is selected.",
        "zh": "提示：选中此项后，输入要从标准列表中删除的规格标题。"
    },
    "Makine kaydedilemedi": {"en": "Machine could not be saved", "zh": "无法保存机器"},

    # --- TEKLİF SİHİRBAZI & PDF İÇERİĞİ ---
    "Profesyonel Teklif Sihirbazı": {"en": "Professional Quotation Wizard", "zh": "专业报价向导"},
    "Teklifi Düzenle": {"en": "Edit Offer", "zh": "编辑报价"},
    "TEKLİF AYARLARI": {"en": "OFFER SETTINGS", "zh": "报价设置"},
    "Müşteri": {"en": "Customer", "zh": "客户"},
    "Model": {"en": "Model", "zh": "型号"},
    "Teslimat": {"en": "Delivery", "zh": "交付"},
    "Müşteri:": {"en": "Customer:", "zh": "客户："},
    "Model:": {"en": "Model:", "zh": "型号："},
    "Teslimat:": {"en": "Delivery:", "zh": "交付："},
    "📝 TEKLİF ŞARTLARINI DÜZENLE": {"en": "📝 EDIT OFFER CONDITIONS", "zh": "📝 编辑报价条件"},
    "💾 SİSTEME KAYDET": {"en": "💾 SAVE TO SYSTEM", "zh": "💾 保存到系统"},
    "📄 PDF İNDİR": {"en": "📄 DOWNLOAD PDF", "zh": "📄 下载 PDF"},
    "Sisteme kaydedildi.": {"en": "Saved to system.", "zh": "已保存到系统。"},
    "Teklif kaydedilemedi": {"en": "Offer could not be saved", "zh": "无法保存报价"},
    "PDF oluşturuldu": {"en": "PDF created", "zh": "PDF 已创建"},
    "PDF oluşturulamadı": {"en": "PDF could not be created", "zh": "无法创建 PDF"},
    "PDF Kaydet": {"en": "Save PDF", "zh": "保存 PDF"},
    "Liman": {"en": "Port", "zh": "港口"},
    "PROFESYONEL TEKLİF FORMU": {"en": "PROFESSIONAL QUOTATION FORM", "zh": "专业报价单"},
    "Tarih": {"en": "Date", "zh": "日期"},
    "MODEL:": {"en": "MODEL:", "zh": "型号："},
    "🔍 MAKİNE STANDART ÖZELLİKLERİ": {"en": "🔍 MACHINE STANDARD SPECIFICATIONS", "zh": "🔍 机器标准规格"},
    "📦 SEÇİLEN OPSİYONLAR": {"en": "📦 SELECTED OPTIONS", "zh": "📦 选定选项"},
    "Donanım Açıklaması": {"en": "Equipment Description", "zh": "设备说明"},
    "Fiyat": {"en": "Price", "zh": "价格"},
    "Makine Baz Fiyatı:": {"en": "Machine Base Price:", "zh": "机器基本价格："},
    "TEKLİF GENEL TOPLAMI (KDV Hariç)": {"en": "OFFER GRAND TOTAL (Excl. VAT)", "zh": "报价总计（不含增值税）"},
    "📝 SATIŞ VE TESLİMAT ŞARTLARI": {"en": "📝 SALES AND DELIVERY CONDITIONS", "zh": "📝 销售与交付条款"},
    "Teslimat Şekli:": {"en": "Delivery Type:", "zh": "交付方式："},
    "Teslim Süresi:": {"en": "Delivery Time:", "zh": "交付时间："},
    "Nakliye / Lojistik:": {"en": "Shipping / Logistics:", "zh": "运输 / 物流："},
    "Vergi / KDV:": {"en": "Tax / VAT:", "zh": "税费 / 增值税："},
    "Ödeme Planı:": {"en": "Payment Plan:", "zh": "付款计划："},
    "Banka Bilgileri:": {"en": "Bank Details:", "zh": "银行信息："},
    "Özel Notlar:": {"en": "Special Notes:", "zh": "特别备注："},
    "Açıklama / Vade": {"en": "Description / Maturity", "zh": "说明 / 期限"},
    "Oran": {"en": "Rate", "zh": "比例"},
    "Oran (%)": {"en": "Rate (%)", "zh": "比例 (%)"},
    "Tutar": {"en": "Amount", "zh": "金额"},
    "Tutar ($)": {"en": "Amount ($)", "zh": "金额 ($)"},
    "Ekstra opsiyon seçilmedi.": {"en": "No extra options selected.", "zh": "未选择额外选项。"},
    "Standart donanım opsiyonu.": {"en": "Standard equipment option.", "zh": "标准设备选项。"},
    "Belirtilmedi": {"en": "Not specified", "zh": "未指定"},
    "Gümrük İşlemleri Yapılmış Antrepo Teslim": {"en": "Warehouse Delivery (Customs Cleared)", "zh": "保税仓库交货（已清关）"},
    "Gümrük İşlemleri Yapılmadan Limandan Devir": {"en": "Port Transfer (Before Customs)", "zh": "港口转让（清关前）"},
    "Yurtiçi Teslim (Standart)": {"en": "Domestic Delivery (Standard)", "zh": "国内交付（标准）"},
    "Liman / Antrepo Teslim (İndirimli)": {"en": "Port / Warehouse Delivery (Discounted)", "zh": "港口/保税仓库交付（折扣）"},
    "Alıcıya Aittir": {"en": "Belongs to Buyer", "zh": "由买方承担"},
    "Fiyatlara KDV Dahil Değildir": {"en": "Prices Exclude VAT", "zh": "价格不含增值税"},
    "Sipariş Onayında (Peşinat)": {"en": "At Order Confirmation (Down Payment)", "zh": "订单确认时（预付款）"},
    "Sayfa": {"en": "Page", "zh": "页"},

    # --- ŞARTLAR PENCERESİ (conditions_window.py) ---
    "Teklif Şartlarını Düzenle": {"en": "Edit Offer Conditions", "zh": "编辑报价条件"},
    "Teklif Toplam Tutarı:": {"en": "Total Offer Amount:", "zh": "报价总金额："},
    "Teslimat ve Vergi": {"en": "Delivery and Tax", "zh": "交付与税收"},
    "Ödeme Planı ve Banka": {"en": "Payment Plan and Bank", "zh": "付款计划与银行"},
    "Notlar": {"en": "Notes", "zh": "备注"},
    "Teslimat Şekli": {"en": "Delivery Type", "zh": "交付方式"},
    "Teslim Süresi": {"en": "Delivery Time", "zh": "交付时间"},
    "Nakliye / Kurulum": {"en": "Shipping / Installation", "zh": "运输 / 安装"},
    "KDV / Vergi Durumu": {"en": "VAT / Tax Status", "zh": "增值税 / 税务状态"},
    "Vergi Durumu:": {"en": "Tax Status:", "zh": "税务状态："},
    "Banka Hesap Bilgileri": {"en": "Bank Account Information", "zh": "银行账户信息"},
    "Satır Ekle": {"en": "Add Row", "zh": "添加行"},
    "Satır Sil": {"en": "Delete Row", "zh": "删除行"},
    "İşlem": {"en": "Action", "zh": "操作"},
    "Ödeme Vadesi / Açıklama": {"en": "Payment Term / Description", "zh": "付款期限 / 说明"},
    "💰 Ödeme Planı": {"en": "💰 Payment Plan", "zh": "💰 付款计划"},
    "Toplam Oran": {"en": "Total Ratio", "zh": "总比例"},
    "UYGULA VE KAPAT": {"en": "APPLY AND CLOSE", "zh": "应用并关闭"},
    "ŞARTLARI KAYDET VE TEKLİFİ GÜNCELLE": {"en": "SAVE CONDITIONS AND UPDATE OFFER", "zh": "保存条件并更新报价"},
    "TOPLAM ORAN %100 OLMALI": {"en": "TOTAL RATIO MUST BE 100%", "zh": "总比例必须为 100%"},

    # --- MÜŞTERİ YÖNETİMİ (customer_window) ---
    "Müşteri Cari Kart Yönetimi": {"en": "Customer Profile Management", "zh": "客户档案管理"},
    "Müşteri Kayıt ve Düzenleme": {"en": "Customer Registration & Edit", "zh": "客户注册与编辑"},
    "Firma Unvanı:": {"en": "Company Name:", "zh": "公司名称："},
    "Vergi Dairesi:": {"en": "Tax Office:", "zh": "税务局："},
    "Vergi Numarası:": {"en": "Tax Number:", "zh": "税号："},
    "Yetkili Kişi:": {"en": "Contact Person:", "zh": "联系人："},
    "E-Posta Adresi:": {"en": "Email Address:", "zh": "电子邮件："},
    "Telefon No:": {"en": "Phone Number:", "zh": "电话号码："},
    "Açıklama": {"en": "Description", "zh": "说明"},
    "Açık Adres:": {"en": "Full Address:", "zh": "详细地址："},
    "💾 KAYDET": {"en": "💾 SAVE", "zh": "💾 保存"},
    "🗑️ SİL": {"en": "🗑️ DELETE", "zh": "🗑️ 删除"},
    "🧹 TEMİZLE": {"en": "🧹 CLEAR", "zh": "🧹 清除"},
    "SİSTEMDE KAYITLI MÜŞTERİLER": {"en": "REGISTERED CUSTOMERS", "zh": "注册客户"},
    "Firma adı boş bırakılamaz.": {"en": "Company name cannot be empty.", "zh": "公司名称不能为空。"},
    "Firma Adı": {"en": "Company Name", "zh": "公司名称"},
    "Vergi No": {"en": "Tax No", "zh": "税号"},
    "Yetkili": {"en": "Contact", "zh": "联系人"},
    "Telefon": {"en": "Phone", "zh": "电话"},
    "E-Posta": {"en": "Email", "zh": "电子邮件"},
    "🔍 Müşteri Ara (Ad, Yetkili veya Tel)...": {"en": "🔍 Search Customer (Name, Contact or Phone)...", "zh": "🔍 搜索客户（姓名、联系人或电话）..."},
    "Zorunlu Alan...": {"en": "Required Field...", "zh": "必填项..."},
    "🔄 GÜNCELLE": {"en": "🔄 UPDATE", "zh": "🔄 更新"},

    # --- GEÇMİŞ TEKLİFLER ---
    "Geçmiş Teklif Kayıtları": {"en": "Offer History Records", "zh": "历史报价记录"},
    "📋 Oluşturulan Tekliflerin Listesi": {"en": "📋 List of Created Offers", "zh": "📋 已创建报价列表"},
    "🔍 Müşteri veya Makine Ara:": {"en": "🔍 Search Customer or Machine:", "zh": "🔍 搜索客户或机器："},
    "Firma adı veya model yazarak filtreleyin...": {"en": "Filter by company name or model...", "zh": "通过公司名称或型号过滤..."},
    "Toplam Tutar ($)": {"en": "Total Amount ($)", "zh": "总金额 ($)"},
    "✏️ Seçili Teklifi Düzenle": {"en": "✏️ Edit Selected Offer", "zh": "✏️ 编辑选定的报价"},
    "🗑️ Teklifi Sil": {"en": "🗑️ Delete Offer", "zh": "🗑️ 删除报价"},
    "Lütfen düzenlemek için bir teklif seçin.": {"en": "Please select an offer to edit.", "zh": "请选择要编辑的报价。"},
    "Bu teklif kaydını silmek istediğinize emin misiniz?": {"en": "Are you sure you want to delete this offer?", "zh": "您确定要删除此报价吗？"},

    # --- FİRMA AYARLARI ---
    "Firma ve Bayi Profil Ayarları": {"en": "Company and Dealer Settings", "zh": "公司和经销商设置"},
    "Bu bilgiler PDF tekliflerinde marka olarak görünecektir.": {"en": "This information will appear as branding on PDFs.", "zh": "此信息将作为品牌显示在PDF上。"},
    "Firma / Bayi Adı:": {"en": "Company / Dealer Name:", "zh": "公司/经销商名称："},
    "Web Sitesi:": {"en": "Website:", "zh": "网站："},
    "Resmi Ünvan (Alt Bilgi):": {"en": "Official Title (Footer):", "zh": "官方头衔（页脚）："},
    "Firma Logosu:": {"en": "Company Logo:", "zh": "公司标志："},
    "🖼️ Logo Seç": {"en": "🖼️ Select Logo", "zh": "🖼️ 选择标志"},
    "Logo seçilmedi": {"en": "No logo selected", "zh": "未选择标志"},
    "💾 AYARLARI KAYDET": {"en": "💾 SAVE SETTINGS", "zh": "💾 保存设置"},
    "Firma ayarları başarıyla güncellendi.": {"en": "Settings updated successfully.", "zh": "公司设置更新成功。"},

    # --- İSKONTO VE VİDEO OYNATICI ---
    "Müşteri İskontosu / Anlaşılan Fiyat": {"en": "Customer Discount / Agreed Price", "zh": "客户折扣 / 约定价格"},
    "Sistem Toplamı:": {"en": "System Total:", "zh": "系统总计:"},
    "Özel İskonto Oranı:": {"en": "Special Discount Rate:", "zh": "特别折扣率:"},
    "Anlaşılan Net Fiyat:": {"en": "Agreed Net Price:", "zh": "约定净价:"},
    "Sistem Liste Toplamı:": {"en": "System List Total:", "zh": "系统列表总计:"},
    "Uygulanan Özel İskonto:": {"en": "Applied Special Discount:", "zh": "适用特别折扣:"},
    "ANLAŞILAN NET FİYAT (KDV Hariç)": {"en": "AGREED NET PRICE (Excl. VAT)", "zh": "约定净价（不含增值税）"},
    "Video Oynatıcı": {"en": "Video Player", "zh": "视频播放器"},
    "Videoyu İzle": {"en": "Watch Video", "zh": "观看视频"},
    "Video Seç (Çoklu Seçim Yapılabilir)": {"en": "Select Video (Multiple Selection Allowed)", "zh": "选择视频（允许多选）"},
    "Seçtiğiniz her video için şimdi bir kapak resmi (thumbnail) seçmeniz istenecek.": {
        "en": "You will now be asked to select a cover image (thumbnail) for each selected video.", 
        "zh": "现在将要求您为每个选定的视频选择一张封面图像（缩略图）。"
    },
    "Video ve Kapak Resmi Ekle": {"en": "Add Video and Cover Image", "zh": "添加视频和封面图片"},
    "Kapak Yok": {"en": "No Cover", "zh": "没有封面"}
}

# --- DİL FONKSİYONLARI ---
def set_lang(lang_code):
    global CURRENT_LANG
    if lang_code in ["tr", "en", "zh"]:
        CURRENT_LANG = lang_code

def tr(text):
    """Metni seçili dile çevirir."""
    if CURRENT_LANG == "tr":
        return text
    if text in translations and CURRENT_LANG in translations[text]:
        return translations[text][CURRENT_LANG]
    return text

# --- PARA BİRİMİ FONKSİYONLARI ---
def set_currency(currency_code):
    global CURRENT_CURRENCY
    if currency_code in ["USD", "EUR", "RMB"]:
        CURRENT_CURRENCY = currency_code

def get_currency_symbol():
    """Seçili para biriminin sembolünü döndürür."""
    symbols = {"USD": "$", "EUR": "€", "RMB": "¥"}
    return symbols.get(CURRENT_CURRENCY, "$")

def get_symbol_by_code(code):
    """Verilen koda göre sembol döndürür (USD -> $, EUR -> € vb.)."""
    symbols = {"USD": "$", "EUR": "€", "RMB": "¥"}
    return symbols.get(code, "$")