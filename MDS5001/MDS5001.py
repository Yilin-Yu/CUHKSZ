import requests
import pandas as pd
import time
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.sandbox.regression.predstd import wls_prediction_std

# Establish connection to Yahoo Finance
yahoo_finance_url = 'https://au.finance.yahoo.com/quote/%s/history?period1=%s&period2=%s&interval=1d&filter=history&frequency=1d' 
# July 1, 2018 starting_date = '1530403200'
# June 30, 2019 ending_day = '1561939199'
timestamp = ['1530403200', '1536710400', '1543017600', '1549324800', '1555632000', '1561939199']
# timestamp = [20183.7.31, 2018.9.12, 2018.11.24, 2019.2.5, 2019.4.19, 2019.6.30]

def fetch_Yahoo_Finance(security, timestamp):
    All_DataFrame = None
    for starting in range(0, len(timestamp)-1):
        each_DataFrame = fetch_Yahoo_Finance_part(security, timestamp[starting], timestamp[starting+1])
        All_DataFrame = pd.concat([All_DataFrame, each_DataFrame], axis = 0)
    #All_DataFrame.set_index(All_DataFrame['Date'], inplace = True)
    #All_DataFrame.sort_index(ascending = True, inplace = True)
    temp = All_DataFrame.sort_values(by = 'Date', ascending = True)
    tt = temp.reset_index(drop = 'True')
    return tt

# Return each security's Ri
def fetch_Yahoo_Finance_part(security, starting, ending):
    yahoo_hist_price_page = requests.get(yahoo_finance_url % (security, starting, ending))    
    # Read historical summary statistics table from Yahoo Finance and clean the DataFrame
    
    # To get every rows but the last row
    yahoo_hist_price_DataFrame = pd.read_html(yahoo_hist_price_page.text)[0].iloc[:-1]
    # Drop these dividend records from the DataFrame
    yahoo_hist_price_DataFrame = yahoo_hist_price_DataFrame[~yahoo_hist_price_DataFrame['Adj. close**'].str.contains('Dividend')] 
    # We only need its Adj. close**
    for column in yahoo_hist_price_DataFrame.columns:
        if column != 'Adj. close**':
            yahoo_hist_price_DataFrame.drop([column], axis = 1)
    # Convert all relevant strings to floats/numbers. Reset to 'NaN' for those shouldn't be converted.
    for column in yahoo_hist_price_DataFrame.columns:
        if column != 'Date':
            yahoo_hist_price_DataFrame[column] = pd.to_numeric(yahoo_hist_price_DataFrame[column], errors='coerce')
    
    # Add security and daily stock return to the DataFrame
    yahoo_hist_price_DataFrame['%s Ri'% security] = yahoo_hist_price_DataFrame['Adj. close**'].pct_change(periods=1)
    
    # Convert String to Date
    yahoo_hist_price_DataFrame['Date'] = pd.to_datetime(yahoo_hist_price_DataFrame['Date'])
    temp = yahoo_hist_price_DataFrame.loc[:,['Date', '%s Ri'% security]]
    return temp

# Use for Rm
def SP500():
    time1 = time.time()
    sp500 = fetch_Yahoo_Finance('^GSPC', timestamp)
    time2 = time.time()
    sp500.rename(columns = {'^GSPC Ri':'^GSPC Rm'}, inplace = True)
    print("Fetch Rm:SP500 sucessful. Spend time %s" % (time2 - time1))
    print()
    return sp500

# Use for Rf
def US_Treasure():
    time1 = time.time()
    US_treasury_URL = 'https://www.treasury.gov/resource-center/data-chart-center/interest-rates/Pages/TextView.aspx?data=yieldYear&year=%s'
    year1 = '2018'
    year2 = '2019'
    US_treasury_hist_price_page1 = requests.get(US_treasury_URL % year1)
    US_treasury_hist_price_page2 = requests.get(US_treasury_URL % year2)

    #Read Table from the US Treasury webpage
    US_treasury_hist_price_DataFrame1 = pd.read_html(US_treasury_hist_price_page1.text)[1]
    US_treasury_hist_price_DataFrame2 = pd.read_html(US_treasury_hist_price_page2.text)[1]

    #Convert string to date
    US_treasury_hist_price_DataFrame1['Date'] = pd.to_datetime(US_treasury_hist_price_DataFrame1['Date'])
    US_treasury_hist_price_DataFrame2['Date'] = pd.to_datetime(US_treasury_hist_price_DataFrame2['Date'])
    
    temp1 = US_treasury_hist_price_DataFrame1.loc[:,['Date', '1 mo']]
    temp2 = US_treasury_hist_price_DataFrame2.loc[:,['Date', '1 mo']]
    
    #Combine US treasure of 2018 and 2019
    Combined_US_Treasure = None
    Combined_US_Treasure = pd.concat([temp1, temp2], axis = 0)
    
    time2 = time.time()
    print("Fetch Rf:US Treasure sucessful. Spend time %s" % (time2 - time1))
    print()
    return Combined_US_Treasure

def X1(Rm, Rf):
    ''' beta_i is the coefficient of X1 = Rm - Rf '''
    time1 = time.time()
    X1_DataFrame = pd.merge(Rm, Rf, on = 'Date')
    X1_DataFrame['Rm_Rf'] = X1_DataFrame['^GSPC Rm'] - X1_DataFrame['1 mo']/100/365
    temp = X1_DataFrame.loc[:,['Date', 'Rm_Rf']] 
    time2 = time.time()
    print("Obtain X1 DataFrame Sucessful. Spend time %s." % (time2 - time1))
    print()
    return temp

def SP500_cap_range_list():

    ''' This part was written by Zuokun Lin '''
    ''' 
    Extract the symbols of top 60 securities from S&P 500, equally divided into two lists.
    Securities have been sorted by their market capitalization.
    '''
    
    time1 = time.time()
    #web has already sorted by cap
    stocks_pool_url = 'https://www.slickcharts.com/sp500'                 
    stocks_pool_page = requests.get(stocks_pool_url)
    stocks_pool_DataFrame = pd.read_html(stocks_pool_page.text)[0]
    
    #construct the target list and list_for_test
    stocks_pool_DataFrame_test = stocks_pool_DataFrame[31:61]['Symbol']
    stocks_pool_DataFrame = stocks_pool_DataFrame[0:31]['Symbol']
    security_list_test = stocks_pool_DataFrame_test.tolist()
    security_list = stocks_pool_DataFrame.tolist()
    security_list.remove('BRK.B')
    time2 = time.time()
    print("Obtained Y and X2 security list sucessful.Spend time %s." %(time2 - time1))
    print()
    # security_list_test是回归方程等式右边， security_list是等式左边
    return security_list_test, security_list

def fetch_vol(security_list):

    ''' This part was written by Zuokun Lin '''

    print("Obtaing X3 security list...")
    time_1 = time.time()
    #initialization
    security_vol_dict = {}
    security_list_vol = []
    #use avg volume
    yahoo_vol_url = 'https://au.finance.yahoo.com/quote/%s?p=%s'               
    
    for security in security_list:
        time1 = time.time()
        #fetch the page
        yahoo_vol_page = requests.get(yahoo_vol_url % (security,security))
        yahoo_vol_data_frame = pd.read_html(yahoo_vol_page.text)[0]
        #fetch the Num and add them into a dict
        vol = yahoo_vol_data_frame.iloc[7,1]
        vol_1 = pd.to_numeric(vol)
        security_vol_dict[security] = vol_1
        time2 = time.time()
        print("get %s, spend time %s" % (security, (time2 - time1)))
    #sort the security_volume dict by the volume
    vol_rank = sorted(security_vol_dict.items(),key=lambda x:x[1])
    #fetch the name of security and construct the target list
    for key,value in vol_rank:
        security_list_vol.append(key)
        #print("%s appended" % key)
    time_2 = time.time()
    print("Obtain X3 security list sucessful. Spend time %s" % (time_2 - time_1))
    print()
    return  security_list_vol

def X3(security_list,timestamp):
    time1 = time.time()
    list1 = security_list[0:int(len(security_list)/2)]
    list2 = security_list[int(len(security_list)/2):int(len(security_list))]
    R1 = combine_Ri_DataFrame(list1, timestamp)
    R1.rename(columns = {'Ri Average':'R1 Ri Average'}, inplace = True)
    R2 = combine_Ri_DataFrame(list2, timestamp)
    R2.rename(columns = {'Ri Average':'R2 Ri Average'}, inplace = True)
    R = pd.merge(R1, R2, on = 'Date')
    R['Volume'] = R['R1 Ri Average'] - R['R2 Ri Average']
    temp = R.loc[:,['Date', 'Volume']]
    time2 = time.time()
    print("X3 DataFrame create sucessful. Spend time %s" % (time2 - time1))
    print()
    return temp


# Combine all Ri and return Ri's average
def combine_Ri_DataFrame(security_list, timestamp):
    # Use the first security to initialize the first DataFrame
    print("Fetching Security %s %s......" % (1, security_list[0]))
    time_1 = time.time()
    Combined_Ri_DataFrame = fetch_Yahoo_Finance(security_list[0], timestamp)
    time_2 = time.time()
    print("Fetching %s sucessful. Spend time %s" % (security_list[0], (time_2 - time_1)))
    print()
    for i in range(1, len(security_list)):
        # Check whether the DataFrame has data and combine them
        time1 = time.time()
        print("Fetching Security %s %s......" % (i + 1, security_list[i]))
        security_Ri_DataFrame = fetch_Yahoo_Finance(security_list[i], timestamp)
        time2 = time.time()
        print("Fetch  %s sucessful, time spend %s" % (security_list[i], time2 - time1))
        Combined_Ri_DataFrame = pd.merge(Combined_Ri_DataFrame, security_Ri_DataFrame, on = 'Date')
        print("Combined  %s sucessful" % security_list[i])
        time3 = time.time()
        print("Obtaining current Ri Average....")
        Combined_Ri_DataFrame['Ri Average'] = Combined_Ri_DataFrame.mean(axis = 1)
        for column in Combined_Ri_DataFrame.columns:
            if column != 'Ri Average':
                Combined_Ri_DataFrame.drop([column], axis = 1)
        time4 = time.time()
        print("Obtaining current Ri Average sucessful. Spend time %s" %(time4 - time3))
        print()
        
    # Create column to store the average Ri for all the securities
    #print("Calculate Ri.....")
    #Combined_Ri_DataFrame['Ri Average'] = Combined_Ri_DataFrame.mean(axis = 1)
    #print("Calculate Ri sucessful")
    temp = Combined_Ri_DataFrame.loc[:,['Date', 'Ri Average']]
    return temp


def X2(security_list, timestamp):
    time1 = time.time()
    list1 = security_list[0:int(len(security_list)/2)]
    list2 = security_list[int(len(security_list)/2):int(len(security_list))]
    R1 = combine_Ri_DataFrame(list1, timestamp)
    R1.rename(columns = {'Ri Average':'R1 Ri Average'}, inplace = True)
    R2 = combine_Ri_DataFrame(list2, timestamp)
    R2.rename(columns = {'Ri Average':'R2 Ri Average'}, inplace = True)
    R = pd.merge(R1, R2, on = 'Date')
    R['Weight'] = R['R1 Ri Average'] - R['R2 Ri Average']
    temp = R.loc[:,['Date', 'Weight']]
    time2 = time.time()
    print("X2 DataFrame create sucessful. Spend time %s" % (time2 - time1))
    print()
    return temp

def Y(security_list, timestamp, Rf):
    time1 = time.time()
    Ri = combine_Ri_DataFrame(security_list, timestamp)
    Y_DataFrame = pd.merge(Ri, Rf, on = 'Date')
    Y_DataFrame['Ri_Rf'] = Y_DataFrame['Ri Average'] - Y_DataFrame['1 mo']/100/365
    temp = Y_DataFrame.loc[:,['Date', 'Ri_Rf']]
    time2 = time.time()
    print("Y DataFrame create sucessful. Spend time %s" % (time2 - time1))
    print()
    return temp


if __name__ == '__main__':

    #yahoo_finance_url = 'https://au.finance.yahoo.com/quote/%s/history?period1=%s&period2=%s&interval=1d&filter=history&frequency=1d' 

    # July 1, 2018 starting_date = '1530403200'
    # June 30, 2019 ending_day = '1561939199'
    timestamp = ['1530403200', '1536710400', '1543017600', '1549324800', '1555632000', '1561939199']
    # timestamp = [20183.7.31, 2018.9.12, 2018.11.24, 2019.2.5, 2019.4.19, 2019.6.30]

    Rm = SP500()

    Rf = US_Treasure()

    xx1 = X1(Rm, Rf)

    Security_List = SP500_cap_range_list()
    Y_security = Security_List[0]
    X_security = Security_List[1]
    X_security_ = fetch_vol(X_security)

    xx2 = X2(X_security, timestamp)
    xx3 = X3(X_security_, timestamp)
    yyy = Y(Y_security, timestamp, Rf)

    Y_X = pd.merge(yyy, xx1, on = 'Date')
    Y_X = pd.merge(Y_X, xx2, on = 'Date')
    Y_X = pd.merge(Y_X, xx3, on = 'Date')

    R_model = ols("""Ri_Rf ~ Rm_Rf""", data = Y_X).fit()
    print(R_model.summary())
    print(R_model.params)

    R_model = ols("""Ri_Rf ~ Rm_Rf + Weight""", data = Y_X).fit()
    print(R_model.summary())
    print(R_model.params)

    R_model = ols("""Ri_Rf ~ Rm_Rf + Weight + Volume""", data = Y_X).fit()
    print(R_model.summary())
    print(R_model.params)