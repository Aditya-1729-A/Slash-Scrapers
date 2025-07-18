import tkinter as tk
from tkinter import messagebox, scrolledtext
import os
import requests
import csv
from tqdm import tqdm
from bs4 import BeautifulSoup
import praw
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

HEADERS = {'User-Agent': 'Mozilla/5.0'}
SAVE_DIR = 'scraped_memes'
CAPTIONS_FILE = os.path.join(SAVE_DIR, 'captions.csv')
os.makedirs(SAVE_DIR, exist_ok=True)

downloaded_urls = set()
if os.path.exists(CAPTIONS_FILE):
    with open(CAPTIONS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            downloaded_urls.add(row[2])

def log(text):
    output_box.insert(tk.END, text + "\n")
    output_box.see(tk.END)

def save_caption(source, title, url):
    with open(CAPTIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([source, title, url])

def download_image(url, path):
    if url in downloaded_urls:
        log(f"Skipping already downloaded: {url}")
        return False
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
            downloaded_urls.add(url)
            return True
    except Exception as e:
        log(f"Failed {url}: {e}")
    return False

def scrape_google_images(queries):
    log("Scraping Google Images")
    for query in queries:
        q = query.replace(' ', '+')
        url = f"https://www.google.com/search?q={q}&tbm=isch"
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        imgs = soup.find_all('img')
        for i, img in enumerate(imgs):
            src = img.get('src')
            if src and src.startswith('http'):
                filename = os.path.join(SAVE_DIR, f"google_{query[:10]}_{i}.jpg")
                if download_image(src, filename):
                    save_caption('Google', query, src)
                    log(f"Downloaded Google: {src}")

def scrape_imgur(queries):
    log("Scraping Imgur")
    for query in queries:
        q = query.replace(' ', '+')
        url = f"https://imgur.com/search?q={q}"
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        imgs = soup.find_all('img')
        for i, img in enumerate(imgs):
            src = img.get('src')
            if src:
                full_src = 'https:' + src if src.startswith('//') else src
                filename = os.path.join(SAVE_DIR, f"imgur_{query[:10]}_{i}.jpg")
                if download_image(full_src, filename):
                    save_caption('Imgur', query, full_src)
                    log(f"Downloaded Imgur: {full_src}")

def scrape_reddit(queries):
    log("Scraping Reddit")
    reddit = praw.Reddit(
        client_id='YOUR_ID',
        client_secret='YOUR_SECRET',
        user_agent='bad_gift_meme_scraper/0.1'
    )
    subreddits = ['memes', 'funny', 'ShittyGifts', 'CrappyDesign']
    for sub in subreddits:
        subreddit = reddit.subreddit(sub)
        for submission in subreddit.hot(limit=50):
            if submission.over_18 or submission.title not in queries:
                continue
            if submission.url.endswith(('.jpg', '.png', '.gif', '.jpeg')):
                filename = os.path.join(SAVE_DIR, f"reddit_{submission.id}.jpg")
                if download_image(submission.url, filename):
                    save_caption('Reddit', submission.title, submission.url)
                    log(f"Downloaded Reddit: {submission.url}")

def scrape_pinterest(queries):
    log("Scraping Pinterest")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    for query in queries:
        driver.get(f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}")
        time.sleep(3)
        imgs = driver.find_elements(By.TAG_NAME, 'img')
        for i, img in enumerate(imgs[:30]):
            src = img.get_attribute('src')
            if src and src.startswith('http'):
                filename = os.path.join(SAVE_DIR, f"pinterest_{query[:10]}_{i}.jpg")
                if download_image(src, filename):
                    save_caption('Pinterest', query, src)
                    log(f"Downloaded Pinterest: {src}")
    driver.quit()

def scrape_giphy(queries):
    log("Scraping Giphy")
    for query in queries:
        q = query.replace(' ', '-')
        url = f"https://giphy.com/search/{q}"
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        gifs = soup.find_all('img')
        for i, gif in enumerate(gifs[:30]):
            src = gif.get('src')
            if src and src.startswith('http'):
                filename = os.path.join(SAVE_DIR, f"giphy_{query[:10]}_{i}.gif")
                if download_image(src, filename):
                    save_caption('Giphy', query, src)
                    log(f"Downloaded Giphy: {src}")

def run_scraper():
    queries = query_entry.get().split(',')
    queries = [q.strip() for q in queries if q.strip()]
    if not queries:
        messagebox.showwarning("Input Error", "Please enter at least one query.")
        return
    output_box.delete(1.0, tk.END)
    if google_var.get():
        scrape_google_images(queries)
    if imgur_var.get():
        scrape_imgur(queries)
    if reddit_var.get():
        scrape_reddit(queries)
    if pinterest_var.get():
        scrape_pinterest(queries)
    if giphy_var.get():
        scrape_giphy(queries)
    log("✅ Done!")

# Tkinter GUI
root = tk.Tk()
root.title("Meme Scraper")
root.configure(bg="#222831")  # dark background

# Style options
label_style = {"bg": "#222831", "fg": "#FFD369", "font": ("Arial", 14, "bold")}
entry_style = {"bg": "#393E46", "fg": "#EEEEEE", "font": ("Arial", 12)}
button_style = {"bg": "#FFD369", "fg": "#222831", "font": ("Arial", 12, "bold"), "activebackground": "#393E46", "activeforeground": "#FFD369"}
checkbox_style = {"bg": "#222831", "fg": "#FFD369", "font": ("Arial", 12)}

tk.Label(root, text="Enter Queries (comma-separated):", **label_style).pack(pady=(15,5))
query_entry = tk.Entry(root, width=80, **entry_style)
query_entry.pack(pady=(0,10))

# Checkbox frame for grouping
checkbox_frame = tk.Frame(root, bg="#222831")
checkbox_frame.pack(pady=(0,10))

google_var = tk.BooleanVar(value=True)
imgur_var = tk.BooleanVar(value=True)
reddit_var = tk.BooleanVar(value=True)
pinterest_var = tk.BooleanVar(value=True)
giphy_var = tk.BooleanVar(value=True)

tk.Checkbutton(checkbox_frame, text="Google", variable=google_var, **checkbox_style).pack(anchor='w', padx=10, pady=2)
tk.Checkbutton(checkbox_frame, text="Imgur", variable=imgur_var, **checkbox_style).pack(anchor='w', padx=10, pady=2)
tk.Checkbutton(checkbox_frame, text="Reddit", variable=reddit_var, **checkbox_style).pack(anchor='w', padx=10, pady=2)
tk.Checkbutton(checkbox_frame, text="Pinterest", variable=pinterest_var, **checkbox_style).pack(anchor='w', padx=10, pady=2)
tk.Checkbutton(checkbox_frame, text="Giphy", variable=giphy_var, **checkbox_style).pack(anchor='w', padx=10, pady=2)

tk.Button(root, text="Run Scraper", command=run_scraper, **button_style).pack(pady=10)

output_box = scrolledtext.ScrolledText(root, width=100, height=20, bg="#393E46", fg="#FFD369", font=("Consolas", 11))
output_box.pack(padx=10, pady=(0,15))

root.mainloop()
