import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse
from datetime import datetime, timedelta
import re
import pandas as pd
import requests
import io

# Streamlitウェブインターフェースの設定
st.title('Xポスト取得アプリ')
query = st.text_input("検索クエリを入力してください", "#踊ってみた新作")
total_tweets = st.number_input("取得するポスト数", min_value=10, max_value=1000, value=100)

# ボタンを横に配置するための列を作成
col1, col2 = st.columns([2, 1])

with col1:
    button = st.button('ポストを取得')

if button:
    with st.spinner('ポストを取得中...'):
        # ブラウザのセットアップ
        options = Options()
        options.add_argument("--headless")  # ヘッドレスモードでの実行
        driver = webdriver.Chrome(options=options)

        encoded_query = urllib.parse.quote(query)
        url = f"https://search.yahoo.co.jp/realtime/search?p={encoded_query}&ei=UTF-8"
        driver.get(url)

        # 短縮URLを展開する関数
        def expand_url(short_url):
            try:
                response = requests.head(short_url, allow_redirects=True)
                return response.url
            except requests.RequestException:
                return short_url

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
            while len(driver.find_elements(By.CSS_SELECTOR, ".Tweet_bodyContainer__n_Cs6")) < total_tweets:
                try:
                    more_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".More_text__1eDS4"))
                    )
                    driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(2)  # クリック間のディレイ
                except Exception as e:
                    st.error(f"More button not found or not clickable: {e}")
                    break

            tweet_containers = driver.find_elements(By.CSS_SELECTOR, ".Tweet_bodyContainer__n_Cs6")

            tweets = []
            images = []
            usernames = []
            user_ids = []
            footers = []
            urls = []
            video_urls = []
            sm_numbers = []
            has_new_dance = []
            has_return_niconico = []
            has_odottemita = []
            for container in tweet_containers:
                tweet_body = container.find_element(By.CSS_SELECTOR, ".Tweet_bodyWrap__w5eT_").text

                # ポスト本文内の短縮URLを取得
                short_urls = container.find_elements(By.CSS_SELECTOR, ".Tweet_body__XtDoj a")
                for short_url_element in short_urls:
                    short_url = short_url_element.get_attribute('href')
                    if short_url.startswith('https://t.co'):
                        expanded_url = expand_url(short_url)
                        tweet_body = tweet_body.replace(short_url_element.text, expanded_url)

                tweets.append(tweet_body)
                
                image_elements = container.find_elements(By.CSS_SELECTOR, ".Tweet_imageContainerWrapper__wPE0R img")
                image_urls = [img.get_attribute('src') for img in image_elements]
                images.append(image_urls)

                username = container.find_element(By.CSS_SELECTOR, ".Tweet_authorName__V3waK").text
                user_id = container.find_element(By.CSS_SELECTOR, ".Tweet_authorID__B1U8c").text
                usernames.append(username.strip())
                user_ids.append(user_id.strip())

                footer = container.find_element(By.CSS_SELECTOR, ".Tweet_footer__NTM49").text
                footers.append(footer)

                try:
                    tweet_url_elements = container.find_elements(By.CSS_SELECTOR, ".Tweet_time__78Ddq a")
                    tweet_url = [elem.get_attribute('href').split('?')[0] for elem in tweet_url_elements if elem.get_attribute('href')][0]
                except Exception as e:
                    tweet_url = ""
                    st.write(f"Tweet URL not found for tweet: {tweet_body}, error: {e}")
                urls.append(tweet_url)

                # ポスト内の動画URLとsm番号を取得
                video_url_match = re.search(r"https://www\.nicovideo\.jp/watch/sm\d+", tweet_body)
                video_url = video_url_match.group(0) if video_url_match else ""
                video_urls.append(video_url)

                sm_number_match = re.search(r"sm\d+", video_url)
                sm_number = sm_number_match.group(0) if sm_number_match else ""
                sm_numbers.append(sm_number)

                # 特定のハッシュタグやメンションをチェック
                has_new_dance.append('◯' if '#踊ってみた新作' in tweet_body else '×')
                has_return_niconico.append('◯' if '#帰ってきたニコニコ' in tweet_body else '×')
                has_odottemita.append('◯' if '@odottemita_PR' in tweet_body else '×')

        finally:
            driver.quit()

        # 日時フォーマットを統一する関数
        def format_datetime(footer):
            try:
                if "昨日" in footer:
                    time_str = re.search(r"(\d{1,2}:\d{2})", footer).group(1)
                    datetime_obj = datetime.now() - timedelta(days=1)
                    return datetime_obj.strftime("%Y/%m/%d") + f" {time_str}:00"
                elif re.search(r"\d{1,2}月\d{1,2}日", footer):
                    date_str = re.search(r"(\d{1,2})月(\d{1,2})日", footer)
                    month = int(date_str.group(1))
                    day = int(date_str.group(2))
                    time_str = re.search(r"(\d{1,2}:\d{2})", footer).group(1)
                    datetime_obj = datetime(datetime.now().year, month, day)
                    return datetime_obj.strftime("%Y/%m/%d") + f" {time_str}:00"
                elif re.search(r"(\d{1,2})分前", footer):
                    minutes_ago = int(re.search(r"(\d{1,2})分前", footer).group(1))
                    datetime_obj = datetime.now() - timedelta(minutes=minutes_ago)
                    return datetime_obj.strftime("%Y/%m/%d %H:%M:%S")
                elif re.search(r"(\d{1,2})時間前", footer):
                    hours_ago = int(re.search(r"(\d{1,2})時間前", footer).group(1))
                    datetime_obj = datetime.now() - timedelta(hours_ago)
                    return datetime_obj.strftime("%Y/%m/%d %H:%M:%S")
                elif re.search(r"(\d{1,2}:\d{2})", footer):
                    time_str = re.search(r"(\d{1,2}:\d{2})", footer).group(1)
                    datetime_obj = datetime.now()
                    return datetime_obj.strftime("%Y/%m/%d") + f" {time_str}:00"
                else:
                    datetime_obj = datetime.strptime(footer, "%Y年%m月%d日 %H:%M")
                    return datetime_obj.strftime("%Y/%m/%d %H:%M:%S")
            except (ValueError, AttributeError):
                return footer

        # URLをハイパーリンク化する関数
        def make_links_clickable(text):
            url_pattern = re.compile(r'(https?://\S+)')
            return url_pattern.sub(r'<a href="\1" target="_blank">\1</a>', text)

        rows = []
        # ポストの表示とCSVファイルへの書き込みデータの準備
        st.header("ポストと画像")
        for index, (tweet, image_urls, username, user_id, footer, url, video_url, sm_number, new_dance, return_niconico, odottemita) in enumerate(zip(tweets, images, usernames, user_ids, footers, urls, video_urls, sm_numbers, has_new_dance, has_return_niconico, has_odottemita)):
            clickable_tweet = make_links_clickable(tweet)
            st.markdown(f"<div style='font-size: small;'>{clickable_tweet}</div>", unsafe_allow_html=True)

            st.write(f"ユーザー名: {username} [@{user_id}](https://twitter.com/{user_id})")

            formatted_datetime = format_datetime(footer)
            
            cols = st.columns(2)  # 2カラムのレイアウトを作成
            for i, image_url in enumerate(image_urls):
                with cols[i % 2]:  # 2列に交互に配置
                    st.image(image_url, use_column_width=True)
            
            st.write(f"時間: {formatted_datetime}")

            # スプレッドシートに書き込むデータを追加
            rows.append([formatted_datetime, username, user_id, tweet, url, video_url, sm_number, new_dance, return_niconico, odottemita])

        # データをCSVファイルに保存
        df = pd.DataFrame(rows, columns=["ポスト日時", "ユーザー名", "アカウントID", "ポスト本文", "ポストURL", "踊ってみた動画URL", "sm番号", "#踊ってみた新作", "#帰ってきたニコニコ", "@odottemita_PR"])
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding="shift-jis", errors='ignore')
        csv_buffer.seek(0)
        csv_data = csv_buffer.getvalue().encode("shift-jis", errors='ignore')

        st.success("データがCSV形式で保存されました。")

        # mm/dd に何件投稿があったかを集計
        try:
            df['ポスト日時'] = pd.to_datetime(df['ポスト日時'], format="%Y/%m/%d %H:%M:%S", errors='coerce')
            df['日付'] = df['ポスト日時'].dt.strftime('%m/%d')
            post_counts = df['日付'].value_counts().reset_index()
            post_counts.columns = ['日付', '件数']
            
            st.header("投稿件数集計")
            st.table(post_counts)
        except Exception as e:
            st.error(f"Error parsing dates: {e}")

with col2:
    if 'csv_data' in locals():
        st.download_button(
            label="CSVファイルをダウンロード",
            data=csv_data,
            file_name="tweets.csv",
            mime="text/csv"
        )
