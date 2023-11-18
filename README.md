# solo-project-ai-ml

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import geo.py as gps
API_KEY = "AkvYaDkG40h_rbg-DIGhsap7cxZic5v4GUlAWqeAMkZ1prAuXXx_TLRUGCrb-Uiv"  # Replace with your Bing Maps API key

geolocator = geopy.geocoders.Bing(AkvYaDkG40h_rbg-DIGhsap7cxZic5v4GUlAWqeAMkZ1prAuXXx_TLRUGCrb-Uiv)



dataset = pd.read_csv('realtor-data.zip.csv')
dataset2= pd.read_csv('test.csv')


a = input("what is your monthley income ")
b= input ("type of property required (enter the no of beds required)")
c=12*int(a)
print(c)
X= dataset.iloc[:, 1:4].values
y = dataset.iloc[:, 3].values
from sklearn.ensemble import RandomForestRegressor
regressor = RandomForestRegressor(n_estimators = 10, random_state = 0)




