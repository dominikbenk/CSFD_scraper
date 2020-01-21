#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import unidecode
import time
from tqdm import tqdm
from IPython.display import Image, HTML
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression



class csfd:
    '''
    The class scrapes and prepares the data from ČSFD for further analysis. Notice that we had to set the "user agent", otherwise the scraping would not be possible.
    Optionally you may set the number of pages from which you would like to scrape the films (10 pages take around 15 minutes) or disable ratings from IMDb.
    '''
    def __init__(self,number_of_pages=1,imdb_rating = True):
        self.number_of_pages = number_of_pages
        self.imdb_rating = imdb_rating
        self.data = pd.DataFrame()
        self.allurl = []
        self.filmlinks = []
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"}

    def FilmLinks(self):
        '''
        The function gathers the links to the individual film pages using ČSFD's built-in search functionality.
        '''
        for page in tqdm(range(1,1+self.number_of_pages),desc='Downloading film links from {} page(s)'.format(str(self.number_of_pages))):
            url = 'https://www.csfd.cz/podrobne-vyhledavani/strana-'+str(page)+'/?type%5B0%5D=0&genre%5Btype%5D=2&genre%5Binclude%5D%5B0%5D=&genre%5Bexclude%5D%5B0%5D=&origin%5Btype%5D=2&origin%5Binclude%5D%5B0%5D=&origin%5Bexclude%5D%5B0%5D=&year_from=&year_to=&rating_from=&rating_to=&actor=&director=&composer=&screenwriter=&author=&cinematographer=&production=&edit=&sound=&scenography=&mask=&costumes=&tag=&ok=Hledat&_form_=film'
            response = requests.get(url, headers = self.headers)
            souped = BeautifulSoup(response.text, 'html.parser')
            self.souped = souped
            self.allurl = [x.a.get('href') for x in self.souped.findAll('td', {'class':'name'})]
            self.filmlinks.extend(['https://www.csfd.cz' + str(x) for x in self.allurl])

        return(self.filmlinks)     
    
    


    def GetData(self):
        '''
        Scrapes the films' individual pages for the desired data. Multiple levels of exception were required, because of the inconsistency of english titles on ČSFD.
        The search 
        '''
        for filmurl in tqdm(self.FilmLinks(),desc='Downloading data for {} films'.format(str(len(self.filmlinks)))):
            response = requests.get(filmurl, headers = self.headers)
            souped = BeautifulSoup(response.text, 'html.parser')

            cztitle = souped.find('h1', {'itemprop':'name'}).string.replace("\t","").replace("\n","")

            try:
                entitle = souped.find('div',class_="info").find('img', alt='USA').findNext('h3').text
            except: 
                try:
                    entitle = souped.find('div',class_="info").find('img', alt='Velká Británie').findNext('h3').text
                except:
                    try:
                        entitle = souped.find('div',class_="info").find('img', alt='anglický').findNext('h3').text
                    except:
                        entitle = ''

            year = int(souped.find('span', itemprop='dateCreated').text)
            poster = souped.find(id='poster').img.get("src")
            genre = souped.find(class_='genre').text.split(' / ')
            origin = souped.find(class_='origin').text.split(', ')[0].split(' / ')
            length = int(souped.find(class_='origin').text.split(', ')[2].split(' ')[0])
            average = float(souped.find(class_='average').text.replace('%',''))
            count = int(souped.find(class_='count').text.replace('\nvšechna hodnocení(','').replace(')\n\t\t\t\t','').replace('\xa0',''))
            director = souped.find(itemprop="director").text.replace("\n","")

            data = pd.DataFrame({"poster":[poster],"cztitle":[cztitle],"entitle":[entitle],"year":[year],"genre":[genre],"origin":[origin],"length (min)":[length],"director":[director],"film_url":[filmurl],"CSFD avg rating (%)":[average],"CSFD num of ratings":[count]})

            if self.imdb_rating:
                try:
                    if entitle == '':
                        imdb = ImdbRating(cztitle,year).GetRating()
                    else:
                        imdb = ImdbRating(entitle,year).GetRating()
                    data = pd.concat([data, imdb], axis=1)
                except:
                    pass
            
            self.data = self.data.append(data,sort=False).reset_index(drop=True)
        
    def PrintData(self,n_rows=100):
        '''
        Prints a table with the film data, adds posters. You may set the number of films to be shown.
        '''
        def path_to_image_html(path):
            return '<img src="'+ path + '"/>'
        
        return(HTML(self.data.to_html(escape=False,render_links=True,max_rows=n_rows,formatters=dict(poster=path_to_image_html))))
        
        
class ImdbRating:
    '''
    The class scrapes and prepares the data from IMDb for further analysis. Required inputs are the title and year which will be passed from ČSFD.
    '''
    def __init__(self,title,year):
        self.title = title
        self.year = year
        self.unaccented = unidecode.unidecode(self.title).replace(" ","+")
        
    def getAndParse(self,url):
        '''
        Initial parse.
        '''
        result = requests.get(url)
        soup = BeautifulSoup(result.text, 'html.parser')
        return(soup)
    
    def GetRatingLink(self): 
        '''
        Gathers the links of the individual films.
        '''
        search_pattern = "https://www.imdb.com/search/title/?title={}&release_date={}-01-01,{}-12-31"
        search_link = search_pattern.format(self.unaccented,self.year,self.year)
        soup = self.getAndParse(search_link)
        title_number = soup.find("h3",class_="lister-item-header").a.get("href")
        rating_link = "https://www.imdb.com" + title_number + "ratings?ref_=tt_ov_rt"
        return(rating_link)
    
    def GetRating(self):
        '''
        Collects the ratings for each individual film. Namely averages, male/female rating differences, us/non-us rating differences as well as whole rating distribution.
        '''
        soup = self.getAndParse(self.GetRatingLink())
        average = float(soup.find(class_="inline-block ratings-imdb-rating").span.text)
        rating_distribution = [s.text for s in soup.find("div",class_="title-ratings-sub-page").table.find_all("div",class_="leftAligned")][1:]
        
        rating_table = [s.find("div",class_="bigcell").text for s in soup.find_all("td",class_="ratingTable")]
        
        ''' Male - Female '''
        rating_MFdifference = float(rating_table[5])-float(rating_table[10])
        ''' non-US - US '''
        rating_USdifference = float(rating_table[17])-float(rating_table[16])
        
        rating_labels = ["IMDB_" + str(i)+"star" for i in range(10,0,-1)]  + ["IMDB avg rating","IMDB_MF_diff","IMDB_US_diff"]
        rating_values = rating_distribution
        rating_values.extend([average,rating_MFdifference,rating_USdifference])
        
        output = pd.DataFrame([rating_values],columns=rating_labels)
        return(output)           

    

class Ranker:
    '''
    Ranks the films according to the criteria specified.
    '''
    def __init__(self, dataset):
        self.data = dataset
        
    def rank(self, number = 'NA', genre = 'NA', country = 'NA', year_lower = 0, year_upper = 2100, duration_lower = 0, duration_upper = 50000, director = 'NA', weightCSFD = 1):
        self.data['weighted rating'] = weightCSFD*self.data['CSFD avg rating (%)']+(1-weightCSFD)*10*self.data['IMDB avg rating']
        years = range(year_lower, year_upper)
        duration = range(duration_lower, duration_upper)
        if (weightCSFD > 1) or (weightCSFD < 0):
            raise ValueError('Please, specify a value between 0 and 1 for weightCSFD.')
        
        subset = self.data
        if genre != 'NA':
            subset = subset.loc[[genre in val for val in subset.genre]]
        if country != 'NA':
            subset = subset.loc[[country in val for val in subset.origin]]
        if years != 'NA':
            subset = subset.loc[(subset.year.isin(years))]
        if duration != 'NA':
            subset = subset.loc[subset['length (min)'].isin(duration)]
        if director != 'NA':
            subset = subset.loc[[director in val for val in subset.director]]

        subset = subset.sort_values(by = ['weighted rating'], ascending = False)
        
        if (number != 'NA') and (number <= subset.shape[0]):
            subset = subset.iloc[0:number]
        subset.reset_index(drop=True, inplace=True)
        
        def path_to_image_html(path):
            return '<img src="'+ path + '"/>'
        
        return(HTML(subset.to_html(escape=False,render_links=True,formatters=dict(poster=path_to_image_html))))
    
    

class Visualize:
    '''
    Visualizes some interesting facts concerning the scraped data. You need to provide it with the data output from ČSFD scraper.
    '''
    def __init__(self,scraped_data):
        self.scraped_data = scraped_data
        
    def Plot(self,scat=True,bar=True,hist=True,reg=True):
        pd.options.mode.chained_assignment = None
        df = self.scraped_data.dropna(axis=0)
        
        if scat:
            fig, ax = plt.subplots()
            df.plot(kind='scatter', x='IMDB avg rating', y='CSFD avg rating (%)', c='year', cmap='viridis',s=60, ax=ax,figsize=(20,10)) 
        
        if bar:
            labels = ['Akční','Krimi','Rodinný','Sci-Fi','Mysteriózní','Drama','Fantasy','Dobrodružný','Thriller','Válečný','Životopisný','Horor','Komedie','Sportovní','Hudební','Western','Psychologický','Road movie','Historický','Romantický','Muzikál','Taneční','Poetický','Pohádka']
            cols = ['Action','Crime','Family','Sci-Fi','Mystery','Drama','Fantasy','Adventure','Thriller','War','Biography','Horror','Comedy','Sport','Music','Western','Psychological','Road Movie','History','Romance','Musical','Dance','Poetic','Fairytale']

            c = []
            for i in range(len(labels)):
                df[cols[i]] = [labels[i] in val for val in df["genre"]]
                c.append(df[df[cols[i]]].mean(axis=0)["IMDB_MF_diff"])

            plt.rcdefaults()
            fig, ax = plt.subplots(figsize=(14, 8))
            y_pos = np.arange(len(cols))
            ax.barh(y_pos, c, align='center',color=["blue" if val > 0 else "red" for val in c],alpha=0.6)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(cols)
            ax.invert_yaxis()  
            ax.set_xlabel('Average difference (Male - Female)')
            ax.set_title('Male/Female rating differences with respect to genres')
            plt.show()
        
        if hist:
            local = [(("Česko" in val) or ("Československo" in val)) for val in df['origin']]
            abroad = np.invert(local)

            imdb_local = df[local]['IMDB avg rating']*10
            csfd_local= df[local]['CSFD avg rating (%)'] 
            imdb_abroad = df[abroad]['IMDB avg rating']*10
            csfd_abroad = df[abroad]['CSFD avg rating (%)'] 

            plt.subplots(ncols=2, figsize=(24, 12))
            plt.subplot(2, 2, 1)

            plt.hist(imdb_abroad,bins = 15,alpha =0.6,label = 'IMDb',facecolor='black')
            plt.hist(csfd_abroad,bins = 15,alpha =0.6,label = 'CSFD',facecolor='red')
            plt.legend(loc='upper left')
            plt.title('Films from Abroad',fontdict={'fontsize':20})
            plt.xlabel("rating",fontdict={'fontsize':12})
            plt.ylabel("frequency",fontdict={'fontsize':12})

            plt.subplot(2, 2, 2)
            plt.hist(imdb_local,bins = 15,alpha =0.6,label = 'IMDb',facecolor='black')
            plt.hist(csfd_local,bins = 15,alpha =0.6,label = 'CSFD',facecolor='red')
            plt.legend(loc='upper left')
            plt.title('Local Films',fontdict={'fontsize':20})
            plt.xlabel("rating",fontdict={'fontsize':12})
            plt.ylabel("frequency",fontdict={'fontsize':12})

            fig.tight_layout()
            plt.show()
        
        if reg:
            df["CSFD - IMDb difference"] =  df['CSFD avg rating (%)'] - df['IMDB avg rating']*10 
            X= df["CSFD - IMDb difference"].values.reshape(-1, 1)
            Y= df['IMDB_US_diff'].values.reshape(-1, 1)
            linear_regressor = LinearRegression()
            linear_regressor.fit(X, Y)
            Y_pred = linear_regressor.predict(X)

            plt.figure(figsize=(8, 8), dpi=80)
            plt.scatter(X, Y,cmap='viridis',s=50)
            plt.plot(X, Y_pred, color='red')
            plt.xlabel("Difference between CSFD and IMDb ratings",fontdict={'fontsize':12})
            plt.ylabel("Difference between non-US and US rating (from IMDb)",fontdict={'fontsize':12})
            plt.show()

