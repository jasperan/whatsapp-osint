# WhatsApp OSINT Tool

## TikTok Tutorial (Spanish)

https://user-images.githubusercontent.com/20752424/222984331-4928e06d-7da1-4521-8f2a-37cbb2a4f0cc.mp4

Video credits go to [linkfydev](https://www.instagram.com/linkfydev/) (thanks for the awesome explanation).
## Turkish explanation at the bottom (Türkçe olarak kullanımı aşağıda anlatılmıştır.)
## Example

![example](./img/doc1.PNG?raw=true)

Welcome to the first WhatsApp OSINT tool. This was developed in early 2019 but I decided to restart the project now for fun. 

# How to Install

First, install requirements:

```
pip install -r requirements.txt
```

- You will need chromedriver, or you can modify the code and use GeckoDriver or any other drivers for Selenium.
- You will need a GUI to execute the code since it interacts with web.whatsapp.com to get statuses
- Replace the name in the file with whichever name you want to track

# How to Run

```
python3 whatsappbeacon.py --username <username_to_track> --language "<language_code>"
```
# Excel format to get data
```
    python3 whatsappbeacon.py --username <username_to_track> --language "<language_code>" -e
```    
#### Example
![img_2.png](img/img_2.png)

where language_code is either 'en' 'tr' 'es' for English,Turkish and Spanish languages. Future language support will be added.

# Credits

This tool was developed by myself in my free time. It's a tool that demonstrates the power of Selenium and web scraping. I don't endorse using this tool for stalking people or any other fraudulent purposes. If you have suggestions on how to expand or improve the functionality, please submit a PR and I'll gladly review changes

[jasperan](https://github.com/jasperan)

# WhatsApp OSINT Tool (Türkçe) 

## TikTok Tutorial (İspanyolca Olarak Anlatılmıştır)

https://user-images.githubusercontent.com/20752424/222984331-4928e06d-7da1-4521-8f2a-37cbb2a4f0cc.mp4

Video credits go to [linkfydev](https://www.instagram.com/linkfydev/) (thanks for the awesome explanation).

## Örnek

![example](./img/doc1.PNG?raw=true)

İlk WhatsApp Osint(Casusluk) aracına Hoş Geldiniz.Bu araç 2019 senesinde geliştirilmeye başlandı ancak şimdi zevkine tekrardan geliştirmeye karar verdim. 

# Nasıl İndirebilirim

### İlk olarak repoyu indirmemiz gerekiyor ve terminale bu satırı yapıştırıyoruz.
```
    git clone https://github.com/jasperan/whatsapp-osint.git
```
Sonra 'requirements.txt' dosyasını indirmemiz gerekiyor 
Terminale aşağıdaki kod satırını yapıştırınız:
```
pip install -r requirements.txt
```

- Chrome Driver'a ihtiyacımız olacaktır.Repoda Chrome Driver mevcuttur.Eğer repo güncel değilse kendiniz indiriniz.
- WhatsApp Osint aracı şuanlık sadece Google Chrome desteklemektedir.Chrome yüklü değilse hata alırsınız.Kendi driverinizi oluşturarak "Brave,Edge,Safari" vs  çalıştırabilirsiniz.
- Google açıldıktan sonra WhatsApp Web'e tek seferlik giriş yapmanız gerekmektedir.QR kodu okutarak giriş yapınız.
- Dosyadaki adı, izlemek istediğiniz adla değiştirin

# Programı Nasıl Çalıştırırım

```
python3 whatsappbeacon.py --username <Bu kısma rehberinizdeki kullanıcı adını yazınız> --language "tr"
```
#### Örneğin 
![img.png](img/img.png)

### Eğer tüm verilerinizi excel formatında almak istiyorsanız bu kodu çalıştırın

```    
    python3 whatsappbeacon.py --username <Bu kısma rehberinizdeki kullanıcı adını yazınız> --language "tr" -e
```

#### Örneğin
![img_1.png](img/img_1.png)


# Katkıda Bulunanlar

Bu araç benim tarafımdan boş zaman aktivitesi olarak geliştirildi.Aracın insanları "Stalklamınız" ve "Dolandırmanız" için kullanmamanızı rica ediyorum çünkü ben bu aracı "Selenium" ve "Web Scrayping" önemini göstermek için geliştirdim.Eğer projeye destek vermek istiyorsanız pull requestlerinizi bekliyorum.Memnuniyetle gözden geçireceğim.

[jasperan](https://github.com/jasperan)

## Bu Kaynak Türkçeye Berkehan Göktürk Tarafından Çevrilmiştir. 
[BerkeGokturk71](https://github.com/BerkeGokturk71)

