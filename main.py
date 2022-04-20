from asyncio import constants
import datetime
import string
from fastapi import FastAPI
import pyTigerGraph as tg
import config as Credential
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import numpy as np
from math import cos, asin, sqrt

import uuid

app = FastAPI()

hostName = "https://hospitalcapacity.i.tgcloud.io"
graphName = "hospitalCapacity"
secret = "vtf3cetfak6t4achk8ejejidmd8i5g4m"
userName = "tigergraph"
password = "hospital"


conn = tg.TigerGraphConnection(
    host=hostName, username=userName, password=password)

graph = tg.TigerGraphConnection(host=hostName, graphname=graphName)

authToken = graph.getToken(secret)
authToken = authToken[0]
print(f"SHHHH.... Keep this a secret. Here's your token:\n {authToken}")


conn = tg.TigerGraphConnection(host=hostName, graphname=graphName,
                               username=userName, password=password, apiToken=authToken)
print(conn)


origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://192.168.4.53:3000",

]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class Person(BaseModel):
    name: str
    age: int
    email: str
    is_infected: bool
    latitude: float
    longitude: float


class Hospital(BaseModel):
    name: str
    capacity: int
    filled: int
    latitude: float
    longitude: float


class Admitted(BaseModel):
    person_id: str
    hospital_id: str
    admittedAt: datetime.datetime
    admittedEnd: datetime.datetime
    healthStatus: str
    disease: str


# see http://www.mathworks.de/help/toolbox/aeroblks/llatoecefposition.html
def latlangToCoordinate(lat, lng):
    f_lat = float(lat)
    f_lng = float(lng)
    rad = np.float64(6378137.0)        # Radius of the Earth (in meters)
    f = np.float64(1.0/298.257223563)  # Flattening factor WGS84 Model
    cosLat = np.cos(f_lat)
    sinLat = np.sin(f_lat)
    FF = (1.0-f)*2
    C = 1/np.sqrt(cosLat**2 + FF * sinLat**2)
    S = C * FF

    x = (rad * C)*cosLat * np.cos(f_lng)
    y = (rad * C)*cosLat * np.sin(f_lng)
    z = (rad * S)*sinLat

    return [x, y, z]


def distance(lat1, lon1, lat2, lon2):
    p = 0.017453292519943295
    hav = 0.5 - cos((lat2-lat1)*p)/2 + cos(lat1*p) * \
        cos(lat2*p) * (1-cos((lon2-lon1)*p)) / 2
    return 12742 * asin(sqrt(hav))

# data is the list of hospital long and latitude


def closest(data, lat, lng):
    distances = min(data, key=lambda p: distance(
        lat, lng, p['latitude'], p['longitude']))

    index_value = data.index(distances)

    return index_value


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/schema")
def read_patient_list():
    results = conn.getSchema()
    print('hello')
    return results


@app.get("/persons")
def get_persons():
    result = conn.getVertices('person')
    return result


@app.get('/hospitals')
def get_hospitals():
    result = conn.getVertices('hospital')
    return result


@app.get("/person/{person_id}")
def get_person_by_id(person_id: int):
    result = conn.getVerticesById('person', person_id)
    return result


@app.delete('/person/{person_id}')
def delete_person_by_id(person_id: int):
    result = conn.delVerticesById(
        'person', person_id, permanent=False, timeout=0)
    return result


@app.get("/hospital/{hospital_id}")
def get_hospital_by_id(hospital_id: int):
    result = conn.getVerticesById('hospital', hospital_id)
    return result


@app.delete('/hospital/{hospital_id}')
def delete_hospital_by_id(hospital_id: int):
    result = conn.delVerticesById(
        'hospital', hospital_id, permanent=False, timeout=0)
    return result


@app.post('/persons')
def create_person(person: dict):
    print(person)
    id = uuid.uuid4()

    result = conn.upsertVertex('person', str(id),  person)
    print(result)
    return {"status": 'ok', "data": result, "id": str(id)}


@app.post('/hospitals')
def create_hospital(hospital: dict):
    print(hospital)
    id = uuid.uuid4()
    ## todo: id
    result = conn.upsertVertex('hospital', str(id), hospital)
    print(result)
    return {"status": 'ok', "data": result, "id": str(id)}


@app.post('/admitted')
def admitte_person(admitted: Admitted):

    attributes = {k: v for admitted in admitted.items() if k !=
                  'person_id' & k != 'hospital_id'}

    result = conn.upsertEdge(
        'person', admitted['person_id'], 'admitted', 'hospital', admitted['hospital_id'], attributes)
    return result


@app.post('/distance')
def distance(person_lat, person_lng, hospital_lat, hospital_lng):
    person_coord = latlangToCoordinate(person_lat, person_lng)
    hospital_coord = latlangToCoordinate(hospital_lat, hospital_lng)

    data = {
        'x1': person_coord[0],
        'y1': person_coord[1],
        'z1': person_coord[2],
        'x2': hospital_coord[0],
        'y2': hospital_coord[1],
        'z2': hospital_coord[2]
    }

    result = conn.runInstalledQuery('euclideanDistance', data)
    return result


@app.get('/nearperson/{person_id}')
def get_nearperson_by_id(person_id: str):

    return 'nearest persons'


@app.get('/nearhospital/{person_id}')
def get_nearhospital_by_id(person_id: str):
    # create a function which will return the nearest hospital
    person = conn.getVerticesById('person', person_id)

    print(person)

    hospitals = conn.getVertices('hospital')

    data = [{key: val for key, val in sub.items() if key == 'attributes'}
            for sub in hospitals]

    print(data)

    data1 = [x['attributes'] for x in data]

    print(data1)

    data2 = [{key: val for key, val in sub.items(
    ) if key == 'latitude' or key == 'longitude'} for sub in data1]

    print(data2)

    person_ = {'latitude': person[0]['attributes']['latitude'],
               'longitude': person[0]['attributes']['longitude']}

    print('person', person_)

    index = closest(
        data2,  person[0]['attributes']['latitude'],
        person[0]['attributes']['longitude']
    )

    return hospitals[index]


# commands to run the server
# source venv/bin/activate
# uvicorn main:app --reload
