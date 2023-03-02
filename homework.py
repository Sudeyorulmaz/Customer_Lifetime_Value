import numpy as np
import pandas as pd
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
import datetime as dt

df_ = pd.read_excel("online_retail_II.xlsx", sheet_name = "Year 2010-2011")
pd.set_option("display.max_columns",None)
pd.set_option("display.width",500)
df= df_.copy()
df.head()
df.dropna(inplace=True)

# VERİ ÖN İŞLEME
# Verinin aykırı değerlerini ayıklama

def outlier_thresholds(dataframe,variable):
    quartile1 = dataframe[variable].quantile(0.01)
    quartile3 = dataframe[variable].quantile(0.99)
    interquantile_range = quartile3 - quartile1
    up_limit = quartile3 + 1.5 * interquantile_range
    low_limit = quartile1 - 1.5 * interquantile_range
    return low_limit, up_limit

def replace_with_thresholds(dataframe,variable):
    low_limit,up_limit = outlier_thresholds(dataframe,variable)
    dataframe.loc[(dataframe[variable] < low_limit),variable] = low_limit
    dataframe.loc[dataframe[variable] > up_limit,variable] = up_limit

replace_with_thresholds(df,"Quantity")
replace_with_thresholds(df,"Price")
df.dropna(inplace=True)
df = df[~df["Invoice"].str.contains("C",na= False)]
df = df[df["Quantity"] > 0]
df = df[df["Price"] > 0]
df.describe().T
df["TotalPrice"] = df["Quantity"] * df["Price"]

# CLTV değerlerinin hesaplanması
# recency: son satın alma  ilk satın alma tarihi arasındaki fark.(Hafta cinsinden)
# T : Analiz günüyle ilk satın alınma tarihi arasındaki fark.(Hafta cinsinden,Müşterinin yaşı)
# frequency : Tekrar eden birden fazla satın alma sayısı.
# monetary : Satın alma başına ortalama kazanç.

df["InvoiceDate"].max()
analysis_date= dt.datetime(2011,12,11)

cltv_df= df.groupby("Customer ID").agg({"InvoiceDate": [lambda x : (x.max()- x.min()).days,
                                                        lambda x : (analysis_date - x.min()).days],
                                        "Invoice": lambda x : x.nunique(),
                                        "TotalPrice": lambda x: x.sum()})
cltv_df.columns=cltv_df.columns.droplevel(0)
cltv_df.columns = ["recency","T","frequency","monetary"]
cltv_df["recency"] = cltv_df["recency"] / 7
cltv_df["T"] = cltv_df["T"] / 7
cltv_df["monetary"] = cltv_df["monetary"] / cltv_df["frequency"]
cltv_df =cltv_df[(cltv_df["frequency"])> 1]


# BG-NDB MODELİNİN KURULMASI

bgf = BetaGeoFitter(penalizer_coef=0.001)
bgf.fit(cltv_df["frequency"],
        cltv_df["recency"],
        cltv_df["T"])


# GAMMA GAMMA MODELİNİN KURULMASI
ggf = GammaGammaFitter(penalizer_coef=0.01)
ggf.fit(cltv_df["frequency"], cltv_df["monetary"])

# Müşteri yaşam boyu değerinin hesaplanması(CLTV Değeri)
# 6 aylık cltv değeri

cltv_6 = ggf.customer_lifetime_value(bgf,
                                   cltv_df["frequency"],
                                   cltv_df["recency"],
                                   cltv_df["T"],
                                   cltv_df["monetary"],
                                   time = 6,
                                   freq="W",
                                   discount_rate=0.01)

cltv_final = cltv_df.merge(cltv_6, on="Customer ID",how= "left" )

