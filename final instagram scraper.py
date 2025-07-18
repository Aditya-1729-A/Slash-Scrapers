import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import asyncio
import csv
import threading
import os
import json
import re
from playwright.async_api import async_playwright

output_file = "user_profiles.csv"
state_file = "state.json"
max_allowed = 100

window = tk.Tk()
window.title("Instagram Hashtag Scraper with Engagement Filtering")
window.geometry("580x680")

progress_var = tk.DoubleVar()
status_var = tk.StringVar()
textbox = scrolledtext.ScrolledText(window, height=6)
results_entry = tk.Entry(window)
progress_bar = Progressbar(window, variable=progress_var, maximum=100)

# Add min/max followers entries
min_followers_entry = tk.Entry(window, width=12)
max_followers_entry = tk.Entry(window, width=12)

# Profession/Business Filter Controls
profession_frame = tk.Frame(window)
profession_frame.pack(pady=5)
tk.Label(profession_frame, text="Filter by Profession/Business (comma-separated):").pack(side=tk.LEFT, padx=5)
profession_entry = tk.Entry(profession_frame, width=40)
profession_entry.pack(side=tk.LEFT, padx=5)
profession_entry.insert(0, "")

def calculate_engagement_ratio(followers, avg_likes, avg_comments):
    """Calculate engagement ratio as percentage"""
    if followers == 0:
        return 0
    total_engagement = avg_likes + avg_comments
    ratio = (total_engagement / followers) * 100
    return round(ratio, 2)

def parse_instagram_number(text):
    """Parse Instagram number format (e.g., '1.2M', '45.3K', '1,234')"""
    if not text:
        return 0
        
    # Remove commas and convert to lowercase
    text = text.replace(',', '').lower().strip()
    
    # Handle 'k' suffix (thousands)
    if 'k' in text:
        try:
            number = float(text.replace('k', ''))
            return int(number * 1000)
        except:
            return 0
    
    # Handle 'm' suffix (millions)
    elif 'm' in text:
        try:
            number = float(text.replace('m', ''))
            return int(number * 1000000)
        except:
            return 0
    
    # Handle 'b' suffix (billions)
    elif 'b' in text:
        try:
            number = float(text.replace('b', ''))
            return int(number * 1000000000)
        except:
            return 0
    
    # Handle regular numbers
    else:
        try:
            return int(float(text))
        except:
            return 0

def get_hashtags_from_text(text):
    # Find all hashtags in the text using regex
    hashtag_pattern = r'#([a-zA-Z][a-zA-Z0-9_]*)'
    hashtags = re.findall(hashtag_pattern, text)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_hashtags = []
    for tag in hashtags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique_hashtags.append(tag)
    
    print(f"Found hashtags in text: {unique_hashtags}")
    return unique_hashtags

def get_hashtags_from_csv(file_path):
    hashtags = []
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                hashtags.append(row[0].strip().lstrip("#"))
    return hashtags

def run_scraper_gui(input_type, value, results_per_tag, min_engagement, max_engagement, min_followers, max_followers, professions):
    # Always use hashtags for initial search, filter by profession/business after profile extraction
    if input_type == "csv":
        hashtags = get_hashtags_from_csv(value)
    else:
        hashtags = get_hashtags_from_text(value)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scrape_instagram(hashtags, results_per_tag, min_engagement, max_engagement, min_followers, max_followers, professions))
    loop.close()


def start_scraper(input_type):
    try:
        results_per_tag = int(results_entry.get())
        if results_per_tag <= 0 or results_per_tag > max_allowed:
            raise ValueError
    except:
        messagebox.showerror("Error", f"Enter a valid number (1–{max_allowed})")
        return

    # Validate engagement ratio inputs
    try:
        min_engagement = float(engagement_min_entry.get()) if engagement_min_entry.get().strip() else 0
        max_engagement = float(engagement_max_entry.get()) if engagement_max_entry.get().strip() else float('inf')
        if min_engagement < 0 or max_engagement < 0:
            raise ValueError("Engagement ratios cannot be negative")
        if min_engagement > max_engagement:
            raise ValueError("Minimum engagement cannot be greater than maximum")
    except ValueError as e:
        messagebox.showerror("Error", f"Invalid engagement ratio: {str(e)}")
        return

    # Validate followers inputs
    try:
        min_followers = int(min_followers_entry.get()) if min_followers_entry.get().strip() else 0
        max_followers = int(max_followers_entry.get()) if max_followers_entry.get().strip() else 10000000
        if min_followers < 0 or max_followers < 0:
            raise ValueError("Followers cannot be negative")
        if min_followers > max_followers:
            raise ValueError("Minimum followers cannot be greater than maximum")
    except ValueError as e:
        messagebox.showerror("Error", f"Invalid followers value: {str(e)}")
        return

    # Get professions/businesses filter
    professions = [p.strip().lower() for p in profession_entry.get().split(',') if p.strip()]

    if not os.path.exists(state_file):
        messagebox.showerror("Missing Login", f"Login session file '{state_file}' not found.\n\nRun the login script first to generate it.")
        return

    if input_type == "csv":
        file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        threading.Thread(target=run_scraper_gui, args=("csv", file_path, results_per_tag, min_engagement, max_engagement, min_followers, max_followers, professions)).start()
    elif input_type == "text":
        input_text = textbox.get("1.0", tk.END)
        if not input_text.strip():
            messagebox.showerror("Error", "Please enter some text with hashtags.")
            return
        hashtags = get_hashtags_from_text(input_text)
        if not hashtags:
            messagebox.showerror("Error", "No hashtags found in the text. Please include hashtags with # symbol (e.g., #travel #food)")
            return
        hashtag_list = ", ".join([f"#{tag}" for tag in hashtags])
        response = messagebox.askyesno("Hashtags Found", 
            f"Found {len(hashtags)} hashtags:\n{hashtag_list}\n\nEngagement filter: {min_engagement}% - {max_engagement}%\nFollowers filter: {min_followers} - {max_followers}\nProfession filter: {', '.join(professions) if professions else 'None'}\n\nProceed with scraping?")
        if not response:
            return
        threading.Thread(target=run_scraper_gui, args=("text", input_text, results_per_tag, min_engagement, max_engagement, min_followers, max_followers, professions)).start()

async def scroll_to_load_posts(page, count=30):
    loaded = set()
    tries = 0
    
    print("Waiting for page to load...")
    
    selectors_to_try = [
        'a[href*="/p/"]',
        'article a[href*="/p/"]',
        '[role="link"][href*="/p/"]',
        'div[style*="display"] a[href*="/p/"]'
    ]
    
    found_selector = None
    for selector in selectors_to_try:
        try:
            await page.wait_for_selector(selector, timeout=10000)
            found_selector = selector
            print(f"Found posts using selector: {selector}")
            break
        except:
            continue
    
    if not found_selector:
        print("No post selectors found, trying to scroll and look for any links...")
        await asyncio.sleep(3)
        found_selector = 'a[href*="/p/"]'

    print(f"Starting to collect posts with selector: {found_selector}")
    
    while len(loaded) < count and tries < 25:
        try:
            links = await page.eval_on_selector_all(found_selector, 'els => els.map(e => e.href)')
            
            for link in links:
                if '/p/' in link and 'instagram.com' in link:
                    loaded.add(link)
            
            print(f"Found {len(loaded)} unique posts so far (try {tries + 1})")
            
            if len(loaded) >= count:
                break
                
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await asyncio.sleep(2)
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.5)
            tries += 1
            
        except Exception as e:
            print(f"Error in scroll attempt {tries}: {e}")
            await asyncio.sleep(2)
            tries += 1

    final_posts = list(loaded)[:count]
    print(f"Collected {len(final_posts)} post links")
    return final_posts

async def find_profile_efficiently(page, post_link):
    """Optimized profile finding function with prioritized selectors"""
    print("Finding profile link...")
    
    profile_selectors = [
        ('span a[href*="/"]', 1000),
        ('article a[role="link"]', 1000),
        ('header a[href*="/"]', 1500),
        ('article header a', 1500),
        ('header a[role="link"]', 1500),
        ('[data-testid="user_avatar"] + a', 800),
        ('img[alt*="profile picture"] + a', 800),
        ('div[role="button"] a', 800),
        ('header img[alt]', 500),
        ('img[alt*="profile picture"]', 500),
    ]
    
    profile_url = None
    initial_username = None
    
    for i, (selector, timeout) in enumerate(profile_selectors):
        try:
            print(f"  Trying selector {i+1}: {selector}")
            await page.wait_for_selector(selector, timeout=timeout)
            
            elements = await page.query_selector_all(selector)
            
            for element in elements:
                if selector.endswith('img[alt]') or selector.endswith('profile picture"]'):
                    parent = await element.query_selector('xpath=..')
                    if parent:
                        href = await parent.get_attribute('href')
                    else:
                        continue
                else:
                    href = await element.get_attribute('href')
                
                if href and '/' in href and not href.endswith('#') and '/explore' not in href and '/p/' not in href:
                    if not href.startswith('http'):
                        href = 'https://www.instagram.com' + href
                    
                    username_match = re.search(r'instagram\.com/([^/?#]+)', href)
                    if username_match:
                        potential_username = username_match.group(1)
                        if potential_username not in ['explore', 'accounts', 'direct', 'stories', 'reels', 'tv']:
                            profile_url = href
                            initial_username = potential_username
                            print(f"  ✓ Found profile: {initial_username} -> {profile_url}")
                            return profile_url, initial_username
            
        except Exception as e:
            print(f"  ✗ Selector failed: {str(e)[:50]}...")
            continue
    
    if not profile_url:
        print("  Trying page source extraction...")
        try:
            page_content = await page.content()
            
            profile_patterns = [
                r'"username":"([^"]+)"',
                r'"owner":{"username":"([^"]+)"',
                r'instagram\.com/([a-zA-Z0-9_.]+)/',
                r'"shortcode_media":{"owner":{"username":"([^"]+)"'
            ]
            
            for pattern in profile_patterns:
                matches = re.findall(pattern, page_content)
                if matches:
                    initial_username = matches[0]
                    if initial_username and initial_username not in ['explore', 'accounts', 'direct', 'stories', 'reels', 'tv']:
                        profile_url = f"https://www.instagram.com/{initial_username}/"
                        print(f"  ✓ Extracted from source: {initial_username}")
                        return profile_url, initial_username
                        
        except Exception as e:
            print(f"  ✗ Source extraction failed: {e}")
    
    print("  ✗ Could not find profile URL")
    return None, None

async def extract_profile_metrics(page):
    """Extract follower count and engagement metrics from profile"""
    metrics = {
        'followers': 0,
        'following': 0,
        'posts': 0,
        'recent_likes': [],
        'recent_comments': []
    }
    try:
        # Try to extract stats by matching labels
        stats_found = False
        try:
            # Look for the stats block (ul > li)
            stat_lis = await page.query_selector_all('header section ul li')
            if stat_lis and len(stat_lis) >= 3:
                for li in stat_lis:
                    text = await li.text_content()
                    if not text:
                        continue
                    text = text.strip().replace('\n', ' ')
                    num_match = re.match(r'([\d.,KkMmBb]+)', text)
                    if num_match:
                        num = parse_instagram_number(num_match.group(1))
                        if 'followers' in text.lower():
                            metrics['followers'] = num
                        elif 'following' in text.lower():
                            metrics['following'] = num
                        elif 'post' in text.lower():
                            metrics['posts'] = num
                stats_found = True
        except Exception as e:
            print(f"  Error extracting stats by label: {e}")
        # Fallback to old method if needed
        if not stats_found or metrics['followers'] == 0:
            stats_selectors = [
                'main section ul li a span',
                'header section ul li span span',
                'header section ul li a span',
                'header section div span span',
                '[data-testid="UserProfileHeader"] span'
            ]
            for selector in stats_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if len(elements) >= 3:
                        stats_texts = []
                        for elem in elements[:3]:
                            text = await elem.text_content()
                            if text:
                                stats_texts.append(text.strip())
                        if len(stats_texts) >= 3:
                            metrics['posts'] = parse_instagram_number(stats_texts[0])
                            metrics['followers'] = parse_instagram_number(stats_texts[1])
                            metrics['following'] = parse_instagram_number(stats_texts[2])
                            print(f"  Fallback stats: {metrics['posts']} posts, {metrics['followers']} followers, {metrics['following']} following")
                            break
                except:
                    continue
        print(f"  Stats: {metrics['posts']} posts, {metrics['followers']} followers, {metrics['following']} following")
        # Extract recent post engagement (likes and comments from first few posts)
        print("  Extracting recent post engagement...")
        
        # Find post links on profile
        post_links = []
        try:
            post_selectors = [
                'article a[href*="/p/"]',
                'div a[href*="/p/"]',
                'main a[href*="/p/"]'
            ]
            
            for selector in post_selectors:
                try:
                    links = await page.eval_on_selector_all(selector, 'els => els.map(e => e.href)')
                    post_links = [link for link in links if '/p/' in link][:5]  # Get first 5 posts
                    if post_links:
                        break
                except:
                    continue
            
            print(f"  Found {len(post_links)} recent posts to analyze")
            
            # Analyze engagement from recent posts
            for i, post_link in enumerate(post_links[:3]):  # Analyze up to 3 recent posts
                try:
                    print(f"  Analyzing post {i+1}: {post_link}")
                    await page.goto(post_link, timeout=30000)
                    await asyncio.sleep(2)
                    
                    # Extract likes
                    likes = 0
                    like_selectors = [
                        'section span span',  # Common likes selector
                        '[data-testid="like_count"]',
                        'button span span',
                        'section button span'
                    ]
                    
                    for like_sel in like_selectors:
                        try:
                            like_elements = await page.query_selector_all(like_sel)
                            for elem in like_elements:
                                text = await elem.text_content()
                                if text and ('like' in text.lower() or re.match(r'^\d+[.,]?\d*[KM]?$', text.strip())):
                                    # Extract number from likes text
                                    number_match = re.search(r'([\d,]+(?:\.\d+)?[KM]?)', text)
                                    if number_match:
                                        likes = parse_instagram_number(number_match.group(1))
                                        break
                            if likes > 0:
                                break
                        except:
                            continue
                    
                    # Extract comments count
                    comments = 0
                    comment_selectors = [
                        'section button span',
                        '[data-testid="comment_count"]',
                        'section span'
                    ]
                    
                    for comment_sel in comment_selectors:
                        try:
                            comment_elements = await page.query_selector_all(comment_sel)
                            for elem in comment_elements:
                                text = await elem.text_content()
                                if text and 'comment' in text.lower():
                                    number_match = re.search(r'([\d,]+(?:\.\d+)?[KM]?)', text)
                                    if number_match:
                                        comments = parse_instagram_number(number_match.group(1))
                                        break
                            if comments > 0:
                                break
                        except:
                            continue
                    
                    if likes > 0 or comments > 0:
                        metrics['recent_likes'].append(likes)
                        metrics['recent_comments'].append(comments)
                        print(f"    Post {i+1}: {likes} likes, {comments} comments")
                    
                except Exception as e:
                    print(f"    Error analyzing post {i+1}: {e}")
                    continue
                    
        except Exception as e:
            print(f"  Error extracting post engagement: {e}")
    
    except Exception as e:
        print(f"  Error extracting profile metrics: {e}")
    
    return metrics

async def scrape_instagram(hashtags, results_per_tag, min_engagement, max_engagement, min_followers, max_followers, professions):
    total_expected = len(hashtags) * results_per_tag
    current_count = 0
    filtered_count = 0
    progress_var.set(0)
    status_var.set("Launching browser...")
    
    data = []
    
    # Load existing entries to avoid duplicates
    existing_entries = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'hashtag' in row and 'username' in row:
                        existing_entries.add((row['hashtag'], row['username']))
            print(f"Loaded {len(existing_entries)} existing entries")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=state_file)
        page = await context.new_page()
        
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        for tag in hashtags:
            url = f"https://www.instagram.com/explore/tags/{tag}/"
            print(f"\nScraping hashtag: #{tag}")
            status_var.set(f"Scraping #{tag}...")
            profiles_found_for_tag = 0
            filtered_count_for_tag = 0
            tried_posts = set()
            max_total_attempts = 1000  # Prevent infinite loop
            total_attempts = 0
            while profiles_found_for_tag < results_per_tag and total_attempts < max_total_attempts:
                try:
                    await page.goto(url, timeout=60000)
                    await asyncio.sleep(3)
                    # Handle popups
                    popup_texts = ['Not Now', 'Cancel', 'Not now', 'Close']
                    for popup_text in popup_texts:
                        try:
                            await page.click(f'text="{popup_text}"', timeout=2000)
                            await asyncio.sleep(1)
                        except:
                            pass
                    try:
                        await page.click('text="Show all posts"', timeout=3000)
                        await asyncio.sleep(2)
                    except:
                        pass
                    # Try to load more posts each time
                    post_links = await scroll_to_load_posts(page, results_per_tag * 3)
                    print(f"Found {len(post_links)} posts for #{tag}")
                    new_posts = [p for p in post_links if p not in tried_posts]
                    if not new_posts:
                        print("No new posts found, breaking loop.")
                        break
                    for i, post_link in enumerate(new_posts):
                        total_attempts += 1
                        tried_posts.add(post_link)
                        if profiles_found_for_tag >= results_per_tag:
                            break
                        print(f"Processing post {i+1}/{len(new_posts)}: {post_link}")
                        try:
                            await page.goto(post_link, timeout=60000)
                            await asyncio.sleep(3)
                            try:
                                await page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                pass
                            profile_url, initial_username = await find_profile_efficiently(page, post_link)
                            if not profile_url:
                                print("  ⚠️ Could not find profile URL, skipping")
                                continue
                            print(f"Going to profile: {profile_url}")
                            await page.goto(profile_url, timeout=60000)
                            await asyncio.sleep(3)
                            try:
                                await page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                pass
                            final_username = initial_username if initial_username else ""
                            try:
                                username_selectors = [
                                    'header h2',
                                    'h1',
                                    'header h1', 
                                    '[data-testid="user_name"]',
                                    'main section h1',
                                    'main section h2'
                                ]
                                for sel in username_selectors:
                                    try:
                                        page_username = await page.text_content(sel, timeout=3000)
                                        if page_username and page_username.strip():
                                            final_username = page_username.strip()
                                            print(f"  Found username on page: {final_username}")
                                            break
                                    except:
                                        continue
                            except:
                                pass
                            if not final_username and initial_username:
                                final_username = initial_username
                            if not final_username:
                                print("  ⚠️ No username found, skipping this profile")
                                continue
                            key = (tag, final_username)
                            if key in existing_entries:
                                print(f"  Already have {final_username} for #{tag}, skipping...")
                                continue
                            print(f"  Extracting metrics for {final_username}...")
                            metrics = await extract_profile_metrics(page)
                            engagement_ratio = 0
                            if metrics['followers'] > 0 and metrics['recent_likes']:
                                avg_likes = sum(metrics['recent_likes']) / len(metrics['recent_likes'])
                                avg_comments = sum(metrics['recent_comments']) / len(metrics['recent_comments']) if metrics['recent_comments'] else 0
                                engagement_ratio = calculate_engagement_ratio(metrics['followers'], avg_likes, avg_comments)
                            print(f"  Engagement ratio: {engagement_ratio}%")
                            if metrics['followers'] < min_followers or metrics['followers'] > max_followers:
                                print(f"  ❌ Filtered out: {metrics['followers']} followers not in range {min_followers}-{max_followers}")
                                filtered_count += 1
                                filtered_count_for_tag += 1
                                continue
                            if engagement_ratio < min_engagement or engagement_ratio > max_engagement:
                                print(f"  ❌ Filtered out: {engagement_ratio}% not in range {min_engagement}%-{max_engagement}%")
                                filtered_count += 1
                                filtered_count_for_tag += 1
                                continue
                            print(f"  ✅ Passed filters: {engagement_ratio}% engagement, {metrics['followers']} followers")
                            full_name = ""
                            bio = ""
                            profession = ""
                            try:
                                name_selectors = ['header section div h1', 'header h1', 'main section div h1']
                                for sel in name_selectors:
                                    try:
                                        name_elem = await page.query_selector(sel)
                                        if name_elem:
                                            full_name = await name_elem.text_content()
                                            if full_name:
                                                full_name = full_name.strip()
                                                break
                                    except:
                                        continue
                                bio_selectors = ['header section div div span', 'header section div span', 'main section div span']
                                for sel in bio_selectors:
                                    try:
                                        bio_elem = await page.query_selector(sel)
                                        if bio_elem:
                                            bio = await bio_elem.text_content()
                                            if bio and len(bio) > 10:
                                                bio = bio.strip()
                                                break
                                    except:
                                        continue
                                # Extract profession/business (robust extraction above bio)
                                profession = ""
                                try:
                                    # Try to find the profession/business label above the bio
                                    # Instagram usually puts it in a span or div above the bio, but not always
                                    # We'll get all spans/divs in the header section and try to find the one that is not full_name or bio
                                    header_section = await page.query_selector('header section')
                                    prof_candidates = []
                                    if header_section:
                                        children = await header_section.query_selector_all('div, span')
                                        for child in children:
                                            text = await child.text_content()
                                            if text:
                                                text = text.strip()
                                                if text and text.lower() != full_name.lower() and text.lower() != bio.lower():
                                                    prof_candidates.append(text)
                                    # Heuristic: pick the first candidate that is not full_name or bio and is not empty
                                    if prof_candidates:
                                        profession = prof_candidates[0]
                                    else:
                                        # Fallback to previous selectors
                                        profession_selectors = [
                                            'header section div span',
                                            'header section div div',
                                            'main section div span',
                                            'main section div div'
                                        ]
                                        for sel in profession_selectors:
                                            try:
                                                prof_elem = await page.query_selector(sel)
                                                if prof_elem:
                                                    prof_text = await prof_elem.text_content()
                                                    if prof_text and prof_text.strip() and prof_text.strip().lower() != full_name.lower() and prof_text.strip().lower() != bio.lower():
                                                        profession = prof_text.strip()
                                                        break
                                            except:
                                                continue
                                    print(f"  Extracted profession/business: '{profession}'")
                                except Exception as e:
                                    print(f"  Profession extraction error: {e}")
                            except:
                                pass
                            if professions:
                                prof_lower = profession.lower() if profession else ""
                                if not any(p in prof_lower for p in professions):
                                    print(f"  ❌ Filtered out: Profession '{profession}' not in {professions}")
                                    filtered_count += 1
                                    filtered_count_for_tag += 1
                                    continue
                            profile_data = {
                                'hashtag': tag,
                                'username': final_username,
                                'full_name': full_name,
                                'bio': bio,
                                'profession': profession,
                                'followers': metrics['followers'],
                                'following': metrics['following'],
                                'posts': metrics['posts'],
                                'engagement_ratio': engagement_ratio,
                                'profile_url': profile_url,
                                'post_url': post_link
                            }
                            data.append(profile_data)
                            existing_entries.add(key)
                            profiles_found_for_tag += 1
                            current_count += 1
                            progress_percent = (current_count / total_expected) * 100
                            progress_var.set(progress_percent)
                            status_var.set(f"{current_count} profiles scraped, {filtered_count} filtered out")
                            print(f"✅ Successfully scraped: {final_username} (Engagement: {engagement_ratio}%, Followers: {metrics['followers']})")
                            await asyncio.sleep(max(5, results_per_tag / 12))
                        except Exception as e:
                            print(f"⚠️ Skipped a post: {e}")
                            continue
                    # If not enough profiles found, try again (loop will reload posts)
                except Exception as e:
                    print(f"❌ Failed to scrape #{tag}: {e}")
                    break
            if profiles_found_for_tag < results_per_tag:
                print(f"⚠️ Only found {profiles_found_for_tag} valid profiles for #{tag} after {total_attempts} attempts.")
                status_var.set(f"⚠️ Only found {profiles_found_for_tag} valid profiles for #{tag} after {total_attempts} attempts.")
        await browser.close()

        # Save results
        print(f"\nSaving {len(data)} profiles to CSV...")
        
        if len(data) == 0:
            print("No new data to save")
            status_var.set("✅ Done. No profiles passed the engagement filter.")
            messagebox.showinfo("Done", f"Scraping complete.\nNo profiles passed the engagement filter ({min_engagement}%-{max_engagement}%).\nProfiles filtered out: {filtered_count}")
            return
        
        # Save with engagement metrics
        saved = False
        attempts = 0
        max_attempts = 3
        while not saved and attempts < max_attempts:
            attempts += 1
            try:
                current_output_file = output_file
                if attempts > 1:
                    base_name = output_file.replace('.csv', '')
                    current_output_file = f"{base_name}_backup_{attempts}.csv"
                    print(f"Attempt {attempts}: Trying to save as {current_output_file}")
                file_exists = os.path.exists(current_output_file)
                with open(current_output_file, 'a', newline='', encoding='utf-8') as f:
                    fieldnames = ['hashtag', 'username', 'full_name', 'bio', 'profession', 'followers', 'following', 'posts', 'engagement_ratio', 'profile_url', 'post_url']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    if not file_exists:
                        writer.writeheader()
                        print("Created new CSV file with headers including engagement metrics and profession")
                    writer.writerows(data)
                    print(f"Successfully wrote {len(data)} profiles to {current_output_file}")
                    saved = True
                    if attempts > 1:
                        print(f"Data saved to backup file: {current_output_file}")
                        messagebox.showinfo("File Saved", f"Original file was locked.\nData saved to: {current_output_file}")
            except PermissionError as e:
                print(f"Attempt {attempts} failed - Permission denied: {e}")
                if attempts < max_attempts:
                    print("The file might be open in Excel or another program.")
                    print("Trying backup filename...")
                    continue
                else:
                    error_msg = (f"Cannot save to CSV file after {max_attempts} attempts.\n\n"
                               f"Please:\n"
                               f"1. Close Excel or any program that might have the file open\n"
                               f"2. Check file permissions\n"
                               f"3. Try running the script as administrator\n\n"
                               f"Scraped data ({len(data)} profiles) will be lost!")
                    print(error_msg)
                    messagebox.showerror("Cannot Save File", error_msg)
                    return
            except Exception as e:
                print(f"Attempt {attempts} failed with error: {e}")
                if attempts >= max_attempts:
                    messagebox.showerror("Error", f"Failed to save data after {max_attempts} attempts: {e}")
                    return

        # Update status
        total_in_file = len(existing_entries)
        status_var.set(f"✅ Done. {len(data)} profiles added, {filtered_count} filtered out.")
        messagebox.showinfo("Done", f"Scraping complete.\nProfiles added: {len(data)}\nProfiles filtered out: {filtered_count}\nEngagement range: {min_engagement}%-{max_engagement if max_engagement != float('inf') else '∞'}%\nTotal profiles in file: {total_in_file}")
        print(f"\n=== SCRAPING COMPLETE ===")
        print(f"New profiles scraped: {len(data)}")
        print(f"Profiles filtered out: {filtered_count}")
        print(f"Total profiles in CSV: {total_in_file}")

# GUI Layout
tk.Label(window, text="Instagram Hashtag Scraper with Engagement Filtering", font=("Arial", 12, "bold")).pack(pady=(10, 5))

# Engagement Ratio Info
info_frame = tk.Frame(window, bg="lightblue", relief="ridge", bd=2)
info_frame.pack(fill=tk.X, padx=10, pady=5)
tk.Label(info_frame, text="Engagement Ratio = (Avg Likes + Avg Comments) / Followers × 100", font=("Arial", 9, "bold"), bg="lightblue").pack(pady=2)
tk.Label(info_frame, text="Benchmarks: Excellent (6%+) | Good (3-6%) | Average (1-3%) | Poor (<1%)", font=("Arial", 8), bg="lightblue").pack(pady=2)

# Engagement Filter Controls
engagement_frame = tk.Frame(window)
engagement_frame.pack(pady=10)

tk.Label(engagement_frame, text="Engagement Ratio Filter:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=(0, 5))

tk.Label(engagement_frame, text="Min %:").grid(row=1, column=0, padx=5)
engagement_min_entry = tk.Entry(engagement_frame, width=8)
engagement_min_entry.grid(row=1, column=1, padx=5)
engagement_min_entry.insert(0, "1.0")

tk.Label(engagement_frame, text="Max %:").grid(row=1, column=2, padx=5)
engagement_max_entry = tk.Entry(engagement_frame, width=8)
engagement_max_entry.grid(row=1, column=3, padx=5)
engagement_max_entry.insert(0, "∞")

# Followers Filter Controls
followers_frame = tk.Frame(window)
followers_frame.pack(pady=5)
tk.Label(followers_frame, text="Min Followers:").grid(row=0, column=0, padx=5)
min_followers_entry = tk.Entry(followers_frame, width=12)
min_followers_entry.grid(row=0, column=1, padx=5)
min_followers_entry.insert(0, "0")
tk.Label(followers_frame, text="Max Followers:").grid(row=0, column=2, padx=5)
max_followers_entry = tk.Entry(followers_frame, width=12)
max_followers_entry.grid(row=0, column=3, padx=5)
max_followers_entry.insert(0, "10000000")

# Hashtag Input Section
tk.Label(window, text="Option 1: Paste any text with hashtags (e.g., captions, descriptions)").pack(pady=(20, 5))
tk.Label(window, text="Example: 'Amazing sunset! #travel #photography #nature'", font=("Arial", 8), fg="gray").pack()
textbox.pack(padx=10, pady=(5, 10))

tk.Label(window, text="OR").pack(pady=(5, 5))
tk.Button(window, text="Choose CSV File", command=lambda: start_scraper("csv")).pack(pady=5)

tk.Label(window, text=f"How many profiles per hashtag? (max {max_allowed})").pack(pady=(10, 0))
results_entry.insert(0, "30")
results_entry.pack(pady=5)

tk.Button(window, text="Start from Text Input", command=lambda: start_scraper("text")).pack(pady=10)
progress_bar.pack(fill=tk.X, padx=10, pady=10)
tk.Label(window, textvariable=status_var).pack(pady=(0, 10))

window.mainloop()