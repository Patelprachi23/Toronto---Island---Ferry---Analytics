"""Rebuild the cleaned dataset and summary outputs from data/raw_ferry_tickets.csv."""
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).parent
d=pd.read_csv(ROOT/"data"/"raw_ferry_tickets.csv")
d["Timestamp"]=pd.to_datetime(d["Timestamp"],errors="coerce")
d["Sales Count"]=pd.to_numeric(d["Sales Count"],errors="coerce")
d["Redemption Count"]=pd.to_numeric(d["Redemption Count"],errors="coerce")
d=d.dropna(subset=["Timestamp","Sales Count","Redemption Count"]).sort_values("Timestamp")
d["Net Movement"]=d["Sales Count"]-d["Redemption Count"]
d["Hour"]=d.Timestamp.dt.hour
d["Date"]=d.Timestamp.dt.date.astype(str)
d["Day of Week"]=d.Timestamp.dt.day_name()
d["Day Number"]=d.Timestamp.dt.dayofweek
d["Month"]=d.Timestamp.dt.month
d["Month Name"]=d.Timestamp.dt.month_name()
d["Year"]=d.Timestamp.dt.year
d["Season"]=d.Month.map({12:"Winter",1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",6:"Summer",7:"Summer",8:"Summer",9:"Fall",10:"Fall",11:"Fall"})
d["Day Type"]=np.where(d["Day Number"]>=5,"Weekend","Weekday")
for col in ["Sales Count","Redemption Count"]:
    q1,q3=d[col].quantile([.25,.75]); fence=q3+1.5*(q3-q1)
    d[col.replace(" Count"," Outlier")]=d[col]>fence
d.to_csv(ROOT/"data"/"ferry_cleaned_featured.csv",index=False)
d.set_index("Timestamp").resample("h").agg({"Sales Count":"sum","Redemption Count":"sum","Net Movement":"sum"}).dropna(how="all").to_csv(ROOT/"data"/"hourly_summary.csv")
d.groupby("Date").agg({"Sales Count":"sum","Redemption Count":"sum","Net Movement":"sum"}).to_csv(ROOT/"data"/"daily_summary.csv")
print("Rebuilt data outputs:",len(d),"records")
