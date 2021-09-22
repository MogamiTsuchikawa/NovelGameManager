import os
import time
import urllib.error
import urllib.request
from bs4 import BeautifulSoup
from urllib import request
import requests
import json
from datetime import datetime as dt
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud import storage

FIREBASE_STORAGE_BUCKET = 'home-data-store-994e9.appspot.com'
GOOGLE_APPLICATION_CREDENTIALS = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS) # ダウンロードした秘密鍵
firebase_admin.initialize_app(cred,{'storageBucket':FIREBASE_STORAGE_BUCKET })
#bucket = storage.bucket()

cookie = {'getchu_adalt_flag': 'getchu.com'}
def download_file(url, dst_path,session,ITEM_HISTORY):
    dummy_user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'
    try:
        cookie = {'getchu_adalt_flag': 'getchu.com','ITEM_HISTORY':ITEM_HISTORY}
        response = session.get(url, cookies=cookie, allow_redirects=False, timeout=10, headers={"User-Agent": dummy_user_agent,"Referer":"http://www.getchu.com/soft.phtml?id="+ITEM_HISTORY})
        print(response.status_code)
        if response.status_code != 200:
            e = Exception("HTTP status: " + str(response.status_code))
            raise e

        content_type = response.headers["content-type"]
        if 'image' not in content_type:
            e = Exception("Content-Type: " + content_type)
            raise e
        with open(dst_path, "wb") as fout:
            fout.write(response.content)
    except urllib.error.URLError as e:
        print(e)

def save_json(erg):
    f = open('data.json', 'r')
    json_dict = json.load(f)
    f.close()
    json_dict.append(erg)
    json_str = json.dumps(json_dict)
    w = open('data.json','w')
    w.write(json_str)
    w.close()

def get_erg_data(jan_code):
    session = requests.session()
    url = 'http://www.getchu.com/php/search.phtml?search_keyword={0}&list_count=30&sort=sales&sort2=down&search_title=&search_brand=&search_person=&search_jan=&search_isbn=&genre=all&start_date=&end_date=&age=&list_type=list&search=search'.format(jan_code)
    html = session.get(url, cookies=cookie).content
    soup = BeautifulSoup(html)
    #print(soup)
    gethu_item_id = soup.find('div',class_='package').find('a')['href'].split('=')[1]
    print('げっちゅうやID:'+gethu_item_id)
    response = session.get('http://www.getchu.com/soft.phtml?id='+gethu_item_id, cookies=cookie)
    html = response.content
    ITEM_HISTORY = response.cookies.get('ITEM_HISTORY')
    print("####"+ITEM_HISTORY)
    soup = BeautifulSoup(html)
    erg_title = soup.find('h1').get_text().replace('\n','').replace('（このタイトルの関連商品）','').strip()
    print(erg_title)
    erg_maker = soup.find('a',class_='glance').get_text()
    erg_maker_url = soup.find('a',class_='glance')['href']
    erg_pubdate = soup.find('a',{'title':'同じ発売日の同ジャンル商品を開く'}).get_text()
    img_url = 'http://www.getchu.com/brandnew/{0}/c{1}package.jpg'.format(gethu_item_id,gethu_item_id)
    download_file(img_url,'img/{0}.jpg'.format(jan_code),session,ITEM_HISTORY)
    erg = {'title':erg_title,'maker':erg_maker,'makerUrl':erg_maker_url,'pubDate':dt.strptime(erg_pubdate,'%Y/%m/%d'),'janCode':jan_code}
    return erg

def upload_blob(source_file_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(FIREBASE_STORAGE_BUCKET)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )

def main():
    erg = get_erg_data(input())
    db = firestore.client()
    if len(db.collection('erg').where('janCode','==',erg['janCode']).get()) != 0:
        return
    response = db.collection('erg').add(erg)
    print(response)
    upload_blob('img/'+erg['janCode']+'.jpg','erg_img/'+erg['janCode']+'.jpg')


main()