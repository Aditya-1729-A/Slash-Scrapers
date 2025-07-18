# Slash-Scrapers
Scrapers built during the PS1 internship at slash experiences
For instagram scraper:

Steps to set it up on your system
1) install python and add it to environment variables on your system
2) run these on cmd one by one to install libraries
      python -m pip install --upgrade pip
      pip install playwright asyncio tkinter
      playwright install
      save all these files in a folder and open cmd and then open the folder directory in which these are saved
3) run python Login.py and login into Instagram on the newly popped up tab. do not close it it will close by itself in 2 minutes.
4)  run Python final instagram scraper.py in cmd and a GUI window will open.
Also this is the final scraper it has both supplier and user outreach all the filters are optional (including business, engagement ratio, follower count) just add hashtags or upload a CSV with hashtags. choose the number of results per hastag you want and you will get a CSV ready in a few minutes. (try not to use above a certain number like 40-50 for the results though it supports upto 100 because instagram bot detection)


For multimedia scraper
install python and add it to environment variables on your system
1)  open cmd in the folder directory in which the files are saved.
2)  run pip install requests tqdm beautifulsoup4 praw selenium webdriver-manager
3)  install other libraries as needed.
4)  run multimedia_scraper.py
5)  A GUI will open select the websites you want to scrape. also give inputs on what the data is expected to be found.
6)  Run it
A new folder will be created in the original folder where the required data will be saved to be used by the user.

