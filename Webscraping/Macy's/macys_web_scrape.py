# -*- coding: utf-8 -*-
import requests
import re
from bs4 import BeautifulSoup, SoupStrainer

#Since Macys' website blocks use of urllib based on the user agent,
#the user-agent header needs to be overwritten.  Therefore I opted to use the
#Request library in order to specify my header.  In the future, I want to try to
#specify a mobile header in order to make the scraping a little easier.
session = requests.Session()
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

#I opted to start at brand page because since Macy's is a department store, I
#figured I could access all the items from their brands page instead of looping
#through the Men's section, Women's section, etc.
#I made a main URL string so I could concatenate full urls later on when I grab
#hrefs.
mainUrl = "https://www.macys.com"
brandUrl = "https://www.macys.com/shop/all-brands?id=63538&cm_sp=us_hdr-_-brands-_-63538_brands"

req = session.get(brandUrl, headers = headers)

#Use the SoupStrainer class from beautiful to parse only a part of the page in
#an effort to save some memory and speed up search speeds.
#In this case, I elected to use the 'lxml' parser because Beautiful Soup
#parses documents significantly faster using lxml than using html.parser
#or html5lib according to their documentation.
brandBox = SoupStrainer(id = 'localContentContainer')
soup = BeautifulSoup(req.text, 'lxml', parse_only = brandBox)

#I noticed that all the links that I needed had a /shop/ in them.
shoppingRegex = re.compile('/shop/*')
brandLinksList = soup.find_all('a', href = shoppingRegex)

#Created a set in order to avoid duplicate links from featured brands
brandLinksSet = set()

for link in brandLinksList:
    fullLink = mainUrl + link['href']
    if fullLink not in brandLinksSet:
        brandLinksSet.add(fullLink)

#Used this regex to filter out non digits in the price.
nonDigits = re.compile('[^\d.]+')

#I decided to write the item name and lowest prices to a csv file.
with open("macys_items_and_prices.csv", 'wb') as csv_file:
    #Loop through each brand link on the Macy's brand page
    for link in sorted(brandLinksSet):
        #Needed to catch all ReadTimeout errors to keep my script running
        try:
            req = session.get(link, headers = headers)
        except requests.exceptions.ReadTimeout:
            #Printed any brands
            print("A timeout occurred at " + link)

        #I opted to only parse the grid that contained both the products and
        # the page numbers.
        sortableGrid = SoupStrainer(class_ = 'sortableGrid')
        soup = BeautifulSoup(req.text, 'lxml', parse_only = sortableGrid)

        #In order to loop through each product page of the brand, I decided to
        #loop through each page by checking the current page and the next page.
        if soup.find('li', class_ = 'currentPage') != None:
            currentPageListTag = soup.find('li', class_ = 'currentPage')

            #If it is the last page in the list of products, there will be a
            #class = "nextPage hiddenVisibility", which will return a length of
            # 2.  All other pages return a length of 1.
            while (len(currentPageListTag['class']) != 2):
                currentPageLink = currentPageListTag.find('a')
                currentPageUrl = mainUrl + currentPageLink['href']
                nextPageListTag = soup.find('li', class_ = re.compile('nextPage*'))

                try:
                    req = session.get(currentPageUrl, headers = headers)
                except requests.exceptions.ReadTimeout:
                    print("A timeout occurred at " + currentPageUrl)

                soup = BeautifulSoup(req.text, 'lxml', parse_only = sortableGrid)

                products = soup.find_all('li', class_ = 'productThumbnailItem')
                for product in products:
                    #Stripped any beginning and ending whitespace in title, and removed
                    #commas to keep the csv consistent.
                    title = product.find('a', class_ = 'productDescLink')['title'].strip().replace(',',' ')

                    #If a product had a discount price, I grabbed that, else I grabbed
                    #the regular price.  In the case where there is no discount or regular
                    #price, then Macy's replaces the price with an "Everyday Value" price.
                    if product.find('span', class_ = 'discount') != None:
                        price = nonDigits.sub("", product.find('span', class_ = 'discount').text)
                    elif product.find('span', class_ = 'regular') != None:
                        price = nonDigits.sub("", product.find('span', class_ = 'regular').text)
                    else:
                        price = nonDigits.sub("", product.find('span', class_ = 'edv').text)

                    csv_file.write((title + ',' + price + '\n').encode("utf-8"))

                currentPageListTag = nextPageListTag

        #This else area handles pages where the list of products are only 1 page
        # and thus do not have a current or next page.
        else:
            products = soup.find_all('li', class_ = 'productThumbnailItem')
            for product in products:
                title = product.find('a', class_ = 'productDescLink')['title'].strip().replace(',',' ')

                if product.find('span', class_ = 'discount') != None:
                    price = nonDigits.sub("", product.find('span', class_ = 'discount').text)
                elif product.find('span', class_ = 'regular') != None:
                    price = nonDigits.sub("", product.find('span', class_ = 'regular').text)
                else:
                    price = nonDigits.sub("", product.find('span', class_ = 'edv').text)

                csv_file.write((title + ',' + price + '\n').encode("utf-8"))

csv_file.close()