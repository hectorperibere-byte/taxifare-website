import streamlit as st
import requests
from datetime import datetime

st.title("💶 Business Trip Ride 💶")

st.markdown('''Don't lose your time and become rich with Business Trip Ride''')

''''''
'''
1. Let's ask for:
- date and time
- pickup longitude
- pickup latitude
- dropoff longitude
- dropoff latitude
- passenger count


'''
st.markdown("## BTRide parameters")

# Date + time
pickup_date = st.date_input("Pickup date", value=datetime.today())
pickup_time = st.time_input("Pickup time", value=datetime.now().time())
pickup_datetime = datetime.combine(pickup_date, pickup_time).strftime("%Y-%m-%d %H:%M:%S")

# Coordinates
pickup_longitude = st.number_input("Pickup longitude", value=-73.95, format="%.6f")
pickup_latitude = st.number_input("Pickup latitude", value=40.78, format="%.6f")
dropoff_longitude = st.number_input("Dropoff longitude", value=-73.98, format="%.6f")
dropoff_latitude = st.number_input("Dropoff latitude", value=40.76, format="%.6f")

# Passenger count
passenger_count = st.number_input("Passenger count", min_value=1, max_value=8, value=1, step=1)


'''
## Once we have these, let's call our API in order to retrieve a prediction

See ? No need to load a `model.joblib` file in this app, we do not even need to know anything about Data Science in order to retrieve a prediction...

🤔 How could we call our API ? Off course... The `requests` package 💡
'''

url = 'https://taxifare-294990428867.europe-west9.run.app'

if url == 'https://taxifare-294990428867.europe-west9.run.app':

    st.markdown('Maybe you want to use your own API for the prediction, not the one provided by Le Wagon...')

'''

2. Let's build a dictionary containing the parameters for our API...
'''

params = {
    "pickup_datetime": pickup_datetime,
    "pickup_longitude": pickup_longitude,
    "pickup_latitude": pickup_latitude,
    "dropoff_longitude": dropoff_longitude,
    "dropoff_latitude": dropoff_latitude,
    "passenger_count": passenger_count
}

'''
3. Let's call our API using the `requests` package...
'''

if st.button("Predict fare"):
    response = requests.get(url, params=params)

    if response.status_code == 200:
        prediction = response.json()["fare"]
        st.success(f"Estimated fare: ${prediction:.2f}")
    else:
        st.error("Error while calling the API")
        st.write(response.status_code)
        st.write(response.text)

'''
4. Let's retrieve the prediction from the **JSON** returned by the API...

## Finally, we can display the prediction to the user
'''
