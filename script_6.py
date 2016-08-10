# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 01:25:43 2016

Based on yibo's R script and JianXiao's translation to Python

@author: Tony
"""
#public 2.25440

# 

import pandas as pd
import numpy as np
import xgboost as xgb
from scipy import sparse
from sklearn.feature_extraction import FeatureHasher
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, scale
from sklearn.decomposition import TruncatedSVD, SparsePCA
from sklearn.cross_validation import train_test_split, cross_val_score
from sklearn.feature_selection import SelectPercentile, f_classif, chi2
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.metrics import log_loss

# Create bag-of-apps in character string format
# first by event
# then merge to generate larger bags by device

##################
#   App Events
##################
print("# Read App Events")
app_ev = pd.read_csv("../input/app_events.csv", dtype={'device_id': np.str})
app_ev_for_labels = app_ev.copy()
# remove duplicates(app_id)
app_ev = app_ev.groupby("event_id")["app_id"].apply(
    lambda x: " ".join(set("app_id:" + str(s) for s in x)))
    
##################
#   App Labels
##################
###TAKES A LOT OF MEMORY!
print("# Read App Labels")
app_labels = pd.read_csv("../input/app_labels.csv", dtype={'label_id': np.str})
app_labels = pd.merge(app_ev_for_labels, app_labels, on='app_id', how='left')
app_labels = app_labels.drop(['event_id', 'is_installed', 'is_active'], axis=1)

del app_ev_for_labels
###TAKES A LOT OF MEMORY!
app_labels = app_labels["label_id"].apply(
    lambda x: "app_label:" + str(x))
app_labels = pd.DataFrame(app_labels)
app_labels['app_id'] = app_labels.index
app_labels = app_labels[['app_id','label_id']] 
################

##################
#     Events
##################
print("# Read Events")
events = pd.read_csv("../input/events.csv", dtype={'device_id': np.str})
events["app_id"] = events["event_id"].map(app_ev)

events = events.dropna()

#del app_ev

events = events[["device_id", "app_id"]]

# remove duplicates(app_id)
events = events.groupby("device_id")["app_id"].apply(
    lambda x: " ".join(set(str(" ".join(str(s) for s in x)).split(" "))))
events = events.reset_index(name="app_id")

# expand to multiple rows
events = pd.concat([pd.Series(row['device_id'], row['app_id'].split(' '))
                    for _, row in events.iterrows()]).reset_index()
events.columns = ['app_id', 'device_id']

##################
#   Label Categories
##################
label_categories = pd.read_csv("../input/label_categories.csv")
app_labels_for_categories = pd.read_csv("../input/app_labels.csv")
label_categories = label_categories.dropna(axis=0, how='any')
label_categories = pd.merge(app_labels_for_categories, label_categories, on='label_id', how='left')

label_categories['category'] = label_categories['category'].apply(lambda x: "category:" + str(x))
label_categories['app_id'] = label_categories['app_id'].apply(lambda x: "app_id:" + str(x))
label_categories = pd.merge(label_categories, events, on='app_id', how='right')
label_categories.drop(['app_id','label_id'],axis=1,inplace='True')
label_categories = label_categories[['device_id','category']]
label_categories = label_categories.drop_duplicates(keep='first')

#label_categories3 = label_categories3.groupby("device_id")["category"].apply(
#    lambda x: " ".join(set("category:" + str(s) for s in x)))
#label_categories3 = pd.DataFrame(label_categories3)
#label_categories3['device_id'] = label_categories3.index
#label_categories3 = label_categories3[['device_id','category']] 

#label_categories3 = pd.merge(label_categories2, app_labels2, on='label_id', how='left')

#from collections import Counter
#words = list(label_categories2.category)
#freqs = Counter(label_categories2.category).most_common()
#print(freqs)


#########################################

#app_labels4 = app_labels3.copy()

#del app_labels





##################
#   Phone Brand
##################
print("# Read Phone Brand")
pbd = pd.read_csv("../input/phone_brand_device_model.csv",
                  dtype={'device_id': np.str})
pbd.drop_duplicates('device_id', keep='first', inplace=True)


##################
#  Train and Test
##################
print("# Generate Train and Test")

train = pd.read_csv("../input/gender_age_train.csv",
                    dtype={'device_id': np.str})
train.drop(["age", "gender"], axis=1, inplace=True)

test = pd.read_csv("../input/gender_age_test.csv",
                   dtype={'device_id': np.str})
test["group"] = np.nan


split_len = len(train)

# Group Labels
Y = train["group"]
lable_group = LabelEncoder()
Y = lable_group.fit_transform(Y)
device_id = test["device_id"]

# Concat
Df = pd.concat((train, test), axis=0, ignore_index=True)

Df = pd.merge(Df, pbd, how="left", on="device_id")
Df["phone_brand"] = Df["phone_brand"].apply(lambda x: "phone_brand:" + str(x))
Df["device_model"] = Df["device_model"].apply(
    lambda x: "device_model:" + str(x))


###################
#  Concat Feature
###################
#app_labels = app_labels.drop(['event_id', 'is_installed', 'is_active'], axis=1)
#app_labels.drop_duplicates('app_id',keep='first',inplace=True)
#app_labels = app_labels4.drop(['event_id', 'is_installed', 'is_active'], axis=1)
#app_labels['app_id'] = app_labels['app_id'].apply(lambda x: "app_id:" + str(x))

###TAKES A LOT OF MEMORY!
new_app_labels = pd.merge(events, app_labels, on='app_id', how='left')


f1 = Df[["device_id", "phone_brand"]]   # phone_brand
f2 = Df[["device_id", "device_model"]]  # device_model
f3 = events[["device_id", "app_id"]]    # app_id
f4 = new_app_labels[["device_id","label_id"]] #app_label
f5 = label_categories[["device_id","category"]] #app_label

del app_labels
del app_ev
del app_labels_for_categories
del events
del new_app_labels
del label_categories
del Df

f1.columns.values[1] = "feature"
f2.columns.values[1] = "feature"
f3.columns.values[1] = "feature"
f4.columns.values[1] = "feature"
f5.columns.values[1] = "feature"

FLS = pd.concat((f1, f2, f3, f4, f5), axis=0, ignore_index=True)


###################
# User-Item Feature
###################
print("# User-Item-Feature")

device_ids = FLS["device_id"].unique()
feature_cs = FLS["feature"].unique()

data = np.ones(len(FLS))
dec = LabelEncoder().fit(FLS["device_id"])
row = dec.transform(FLS["device_id"])
col = LabelEncoder().fit_transform(FLS["feature"])
sparse_matrix = sparse.csr_matrix(
    (data, (row, col)), shape=(len(device_ids), len(feature_cs)))

sparse_matrix = sparse_matrix[:, sparse_matrix.getnnz(0) > 0]

##################
#      Data
##################

train_row = dec.transform(train["device_id"])
train_sp = sparse_matrix[train_row, :]

test_row = dec.transform(test["device_id"])
test_sp = sparse_matrix[test_row, :]

X_train, X_val, y_train, y_val = train_test_split(
    train_sp, Y, train_size=.90, random_state=10)

##################
#   Feature Sel
##################
print("# Feature Selection")
selector = SelectPercentile(f_classif, percentile=40)

selector.fit(X_train, y_train)

X_train = selector.transform(X_train)
X_val = selector.transform(X_val)

train_sp = selector.transform(train_sp)
test_sp = selector.transform(test_sp)

print("# Num of Features: ", X_train.shape[1])

##################
#  Build Model
##################
import NN
num_inputs = X_train.shape[1]
hidden_units_1 = 48
num_classes = 12
p_dropout = 0.0
X_train_shared, y_train_shared, X_cv_shared, y_cv_shared, X_test_shared =\
    NN.load_data_into_shared(X_train.toarray(), y_train, X_val.toarray(), y_val, test_sp.toarray())
clf = NN.Network([NN.HiddenLayer(num_inputs, hidden_units_1, p_dropout=p_dropout),\
                  NN.SoftmaxLayer(hidden_units_1, num_classes, p_dropout=p_dropout)],\
                 num_batch = 38, epochs=10, eta=0.2, lmb=2.5)
clf.fit(X_train_shared, y_train_shared, X_cv_shared, y_cv_shared)
pred_prob_cv_nn = clf.predict_proba(X_test_shared)
def logloss(pred_prob, actual):
    # Takes the probabilities of each class and compares them with actual
    # values to give the log loss. Limit values near 0 and 1 since they are
    # undefined. Returns log loss only of actual class.
    pred_prob[pred_prob < 1e-15] = 1e-15
    pred_prob[pred_prob > 1-1e-15] = 1-1e-15
    log_prob = np.log(pred_prob)
    indicator_actual = np.zeros(pred_prob.shape)
    indicator_actual[np.arange(len(actual)), actual] = 1
    err = -np.multiply(log_prob, indicator_actual)
    return err.sum()/err.shape[0]
print("Log Loss = {}".format(logloss(pred_prob_cv_nn, y_val)))
### Log Loss = 


dtrain = xgb.DMatrix(X_train, y_train)
dvalid = xgb.DMatrix(X_val, y_val)

params = {
    "objective": "multi:softprob",
    "num_class": 12,
    "booster": "gblinear",
    "max_depth": 6,
    "eval_metric": "mlogloss",
    "eta": 0.07,
    "silent": 1,
    "alpha": 3,
}

watchlist = [(dtrain, 'train'), (dvalid, 'eval')]
gbm = xgb.train(params, dtrain, 40, evals=watchlist,
                early_stopping_rounds=25, verbose_eval=True)

print("# Train")
dtrain = xgb.DMatrix(train_sp, Y)
gbm = xgb.train(params, dtrain, 40, verbose_eval=True)
y_pre = gbm.predict(xgb.DMatrix(test_sp))

#Combine results of NN and xgboost
y_pre = (pred_prob_cv_nn+y_pre)/2.0 

# Write results
result = pd.DataFrame(y_pre, columns=lable_group.classes_)
result["device_id"] = device_id
result = result.set_index("device_id")
result.to_csv('bag_of_apps_w_nn.gz', index=True,
              index_label='device_id', compression="gzip")