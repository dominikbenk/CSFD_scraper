# The Film Ranker
### Dominik Benk, Miroslav Duda

The aim of our project is to provide a script, which will collect data from Česko-Slovenská filmová databáze (ČSFD), and Internet Movie Database (IMDb), with a focus on ratings, visualize these ratings, and rank the scraped films according to criteria specified by the user.

The script scrapes the required data from the individual pages of the films on both databases, and consolidates them into a data frame. According to the conditions specified, a function then prints an ordered list of films. The ordering conditions include the film's duration, rating, and genre. The user may also specify the desired weight of the films' rating on ČSFD compared to IMDb ratings.

We hope that this tool provides a simple way of ranking and comparing films based on their selected attributes.


#### required modules: 
* request
* pandas
* numpy
* BeautifulSoup
* unidecode
* time
* tqdm 
* matplotlib
* sklearn
