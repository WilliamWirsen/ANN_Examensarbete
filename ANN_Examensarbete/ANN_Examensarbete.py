from math import sqrt
import numpy as np 
import pandas as pd
from datetime import datetime
from matplotlib import pyplot
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras.models import Sequential
from keras.layers import Dense, Dropout, LSTM

seed = 7
np.random.seed(seed)

# Convert series to supervised learning
def series_to_supervised(values, n_in=1, n_out=1, dropnan=True):
    n_vars = 1 if type(values) is list else values.shape[1]
    df = pd.DataFrame(values)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
    # forcast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j + 1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j+1)) for j in range(n_vars)]
    # PPut it all together
    agg = pd.concat(cols, axis = 1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan: 
        agg.dropna(inplace=True)
    return agg

# load dataset
url="http://users.du.se/~h15marle/GIK258_Examensarbete/Data/dataset.xlsx"
dataset = pd.read_excel(url, index_col=0, header=0)
values = dataset.values

# integer encode direction
encoder = LabelEncoder()
# values[:,1] = encoder.fit_transform(values[:,1])
# ensure all data is float
values = values.astype('float32')
#normalize features
scaler = MinMaxScaler(feature_range=(0,1))
scaled = scaler.fit_transform(values)
# frame as supervised learning
n_days = 1
n_features = 11
reframed = series_to_supervised(scaled, n_days,1 )

# split into train and test sets
values = reframed.values
train = values[:782, :]
test = values[782:, :]
# split into input and outputs
n_obs = n_days * n_features
train_X, train_y = train[:, :n_obs], train[:, -n_features]
test_X, test_y = test[:, :n_obs], test[:, -n_features]
print(train_X.shape, len(train_X), train_y.shape)
# reshape input to be 3D [samples, timesteps, features]
train_X = train_X.reshape((train_X.shape[0], n_days, n_features))
test_X = test_X.reshape((test_X.shape[0], n_days, n_features))
print(train_X.shape, train_y.shape, test_X.shape, test_y.shape)

# design network
model = Sequential()
model.add(LSTM(450, input_shape=(train_X.shape[1], train_X.shape[2]), return_sequences=True, activation='elu'))
model.add(LSTM(400, activation='elu', return_sequences=True))
model.add(LSTM(250, activation='elu'))
model.add(Dense(1, activation='linear'))
model.compile(loss='mse', optimizer='adam', metrics=['mae'])

# fit network
history = model.fit(train_X, train_y, epochs=30, validation_data=(test_X, test_y))

# Evaluate the model
scores = model.evaluate(train_X, train_y, verbose=0)

# plot history
pyplot.plot(history.history['loss'], label='train')
pyplot.plot(history.history['val_loss'], label='test (MSE)')
pyplot.legend()
pyplot.show()

# make prediction
yhat = model.predict(test_X)
test_X = test_X.reshape((test_X.shape[0], n_days*n_features))
# invert scaling for forecast
inv_yhat = np.concatenate((yhat, test_X[:, -(n_features-1):]), axis=1)
inv_yhat = scaler.inverse_transform(inv_yhat)
inv_yhat = inv_yhat[:,0]
# invert scaling for actual
test_y = test_y.reshape((len(test_y), 1))
inv_y = np.concatenate((test_y, test_X[:, -(n_features-1):]), axis=1)
inv_y = scaler.inverse_transform(inv_y)
inv_y = inv_y[:,0]

pyplot.plot(inv_yhat)
pyplot.plot(inv_y)
pyplot.show()
# calculate RMSE
rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
print('Test RMSE: %.8f' % rmse)
print("%s: %.2f%%" % (model.metrics_names[1], scores[1]*100))

# Serialize model to JSON
model_json = model.to_json()
with open("model.json", "w") as json_file:
        json_file.write(model_json)

# Serialize weights to HDF5
model.save_weights("model.h5")
print("Saved model to disk")

inv_y = pd.DataFrame([inv_y])
inv_y = inv_y.shift(n_days, axis=1)
inv_y = inv_y.transpose()
inv_y = inv_y.dropna(how='all')

pyplot.plot(inv_yhat)
pyplot.plot(inv_y)
pyplot.legend(['Predikterade värden', 'Riktiga värden'])
pyplot.xlabel('Antal värden', fontsize=14)
pyplot.ylabel('Millimeter', fontsize=14)
pyplot.title('Prediktion av marksättning', fontsize=18)
pyplot.show()