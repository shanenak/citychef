from sys import path
from webbrowser import get
import streamlit as st
import json
import pandas as pd
import geopandas as gpd
import pyproj
import plotly
import plotly.graph_objs as go
import plotly.express as px
import pydeck as pdk
from itertools import compress
# from shapely.geometry import LineString

import os
# os.environ['GDAL_DATA'] = '/home/server/anaconda3/share/gdal'
os.environ['PROJ_LIB'] = 'C:/Program Files/GDAL/projlib'
st.set_page_config(layout="wide")
mapboxt = 'pk.eyJ1IjoiamFyZWRzdG9jayIsImEiOiJjam1jZnU5eTM1eG9iM3BwNDRmanhoNmh5In0.T4d8R_EHrcnx7lMtw8yTLQ'

networks = {
    'train':{'label':'Train Network','path': 'rail_network.geojson','color':[38, 70, 83]},
    'car':{'label':'Car Network','path': 'car_network.geojson','color':[42, 157, 143]},
    'bus':{'label':'Bus Network','path': 'bus_network.geojson','color':[233, 196, 106]},
    'buildings':{'label':'Building Locations', 'path': 'building_locations.geojson', 'color':[244, 162, 97]},
    'zones':{'label':'Administrative zones', 'path': "administrative_zones.geojson", 'color':[231, 111, 81]},
    'areas':{'label':'Administrative areas', 'path': "administrative_areas.geojson", 'color':[187, 62, 3]},
    'commuters':{'label':'Commuter frequency', 'path':"zone_commuter_freq_table.csv", 'color': [233, 216, 166]},
    'population':{'label':'Population survey', 'path':"population_survey.csv", 'color': [233, 216, 166]}
}


def join_dataframe(file: str):
    path_to_city="C:/Users/Shannon.Nakamura/citychef/festival_of_data/city_A/"
    A_df = gpd.read_file(path_to_city+networks[file]['path'])
    A_df['city']='A'

    path_to_city="C:/Users/Shannon.Nakamura/citychef/festival_of_data/city_B/"
    B_df = gpd.read_file(path_to_city+networks[file]['path'])
    B_df['city']='B'

    df = A_df.append(B_df)
    if 'zone_id' in df.columns:
        df['zone_id']=df['zone_id'].astype(float)
    if 'area_id' in df.columns:
        df['area_id']=df['area_id'].astype(float)
        df['area_id']=df['area_id'].astype(int)
    
    return df

buildings_df=join_dataframe('buildings')
buildings_df['coordinates']=buildings_df['geometry'].apply(lambda p: [p.x, p.y])
color_dict={'households':[0, 109, 119], 'work':[131, 197, 190], 'leisure':[237, 246, 249], 'education':[255, 221, 210], 'health':[226, 149, 120], 'shopping':[252, 163, 17]}
buildings_df['color']=buildings_df['activity'].apply(lambda x: color_dict[x])

zones_df=join_dataframe('zones')
areas_df =join_dataframe('areas')

commuters_df = join_dataframe('commuters')
commuters_df = commuters_df.drop(['geometry', 'city'], axis =1)
commuter_zones_df = zones_df.merge(commuters_df, on='zone_id')

population_df = join_dataframe('population')

# st.write(commuters_df)
viewport = {
    'A':pdk.data_utils.compute_view(buildings_df.loc[buildings_df['city']=='A']['geometry'].apply(lambda p: [p.x, p.y])),
    'B':pdk.data_utils.compute_view(buildings_df.loc[buildings_df['city']=='B']['geometry'].apply(lambda p: [p.x, p.y])),
    'C':pdk.data_utils.compute_view(buildings_df['geometry'].apply(lambda p: [p.x, p.y]))
}

def get_line_dataframe(file:str):
    path_to_city="C:/Users/Shannon.Nakamura/citychef/festival_of_data/city_A/"
    A_df = gpd.read_file(path_to_city+networks[file]['path'])
    A_df['city']='A'

    path_to_city="C:/Users/Shannon.Nakamura/citychef/festival_of_data/city_B/"
    B_df = gpd.read_file(path_to_city+networks[file]['path'])
    B_df['city']='B'

    df = A_df.append(B_df)

    df['start']=df['geometry'].apply(lambda x: [x.coords[0][0], x.coords[0][1]])
    df['end']=df['geometry'].apply(lambda x: [x.coords[1][0], x.coords[1][1]])

    label_width = {'primary':8, 'secondary':6, 'tertiary':4, 'rail':6, 'residential':6}
    df['width']=df['label'].apply(lambda x: label_width[x])

    df['distance']=df['distance'].round()
    return df

def make_line_layer(df: pd.DataFrame, color: list):
    
    layer = pdk.Layer(
        "LineLayer",
        df,
        get_source_position='start',
        get_target_position='end',
        get_color=color,
        get_width='width',
        highlight_color=[176, 203, 156],
        picking_radius=10,
        auto_highlight=True,
        pickable=True,
        )
    return layer

def make_point_layer(df: pd.DataFrame):
    layers=[]
    activities=['households', 'work', 'leisure', 'education', 'health', 'shopping']
    for activity in activities:
        layer = pdk.Layer(
            'ScatterplotLayer',
            df.loc[df['activity']==activity],
            get_position='coordinates',
            auto_highlight=True,
            get_radius=10,
            get_fill_color='color',
            pickable=True
            )
        layers.append(layer)
    return layers

car_df = get_line_dataframe('car')
train_df = get_line_dataframe('train')
bus_df = get_line_dataframe('bus')

all_layers = [make_line_layer(car_df, networks['car']['color']), 
    make_line_layer(train_df, networks['train']['color']),
    make_line_layer(bus_df, networks['bus']['color'])
    ]   

def get_network_map(view:str, layer:list):
    network_map = pdk.Deck(layers=list(compress(all_layers, layer)), 
            initial_view_state=viewport[view], 
            map_style = 'mapbox://styles/mapbox/satellite-streets-v11',
            # map_provider = 'mapbox',
            tooltip = {
                "html": "<b>ID:</b> {id} <br/> <b>Label:</b> {label} <br/> <b>Free speed:</b> {freespeed} <br/> <b>Distance:</b> {distance}",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white"
                }
            }
        )

    st.pydeck_chart(network_map)

def get_scatterplot_map(view:str, layers:list, filters:list):
    network_map = pdk.Deck(layers=list(compress(layers, filters)), 
            initial_view_state=viewport[view], 
            map_style = 'mapbox://styles/mapbox/streets-v11',
            # map_provider = 'mapbox',
            tooltip = {
                "html": "<b>Activity:</b> {activity}",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white"
                }
            }
        )

    st.pydeck_chart(network_map)

def make_commuter_map(city: str, layer: pdk.Layer, df: pd.DataFrame):
    zones_layer = pdk.Layer(
        "GeoJsonLayer",
        df,
        opacity=0.2,
        stroked=False,
        filled=True,
        extruded=False,
        wireframe=True,
        pickable=True,
        get_fill_color="[freq*10, freq*10, 156]",
        get_line_color=[42, 154, 135]
        )

    zones_map = pdk.Deck(layers=[zones_layer, layer], 
        initial_view_state=viewport[city], 
        map_style = 'mapbox://styles/mapbox/streets-v11',
        # map_provider = 'mapbox',
        tooltip = {
            "html": "<b>Zone ID:</b> {zone_id} <br/> <b>Area ID:</b> {area_id} <br/> <b>Commuter Frequency:</b> {freq} <br/> <b>Main Facility Zone:</b> {main_facility_zone}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white"
            }
        }
    )

    st.pydeck_chart(zones_map)

def make_density_map(city: str, layer: pdk.Layer, df: pd.DataFrame):
    zones_layer = pdk.Layer(
        "GeoJsonLayer",
        df,
        opacity=0.2,
        stroked=False,
        filled=True,
        extruded=False,
        wireframe=True,
        pickable=True,
        get_fill_color="[density*1000000, density*100000, 156]",
        get_line_color=[42, 154, 135]
        )

    zones_map = pdk.Deck(layers=[zones_layer, layer], 
        initial_view_state=viewport[city], 
        map_style = 'mapbox://styles/mapbox/streets-v11',
        # map_provider = 'mapbox',
        tooltip = {
            "html": "<b>Zone ID:</b> {zone_id} <br/> <b>Area ID:</b> {area_id} <br/> <b>Density:</b> {density}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white"
            }
        }
    )

    st.pydeck_chart(zones_map)

st.sidebar.title('Festival of Data')
st.sidebar.write('#### *Created on Streamlit*')
st.sidebar.write('')
st.sidebar.markdown('The backend of this website is written in Python and hosted on Github. It leverages python packages such as Pydeck and Geopandas.')
st.sidebar.write('')
st.sidebar.write('Interactive platforms like Streamlit provide the opportunity for clients to engage with the data themselves. External collaborators can filter and manipulate the data for a deeper understanding of design considerations.')

col1, col2 = st.columns([8,1])
with col1:
    st.write("# Let's take a look at our cities")
    st.write('Each map below can be used to compare City A and City B. Users can scroll over points and polygons to get more details on the datapoint.')
    st.write('')
    st.write("## Activities and building locations")
with col2:
    logo_url = "https://upload.wikimedia.org/wikipedia/commons/3/3a/Arup_Red_RGB.png"
    st.image(logo_url, width=100)

col1, col2, col3 = st.columns([1,3,3])
with col1:
    st.write('')
    st.write('')
    st.write('**Activities:**')
    show_all = st.checkbox('All', False)
    st.write('')
    show_households = st.checkbox('Households', True)
    show_work = st.checkbox('Work', False)
    show_leisure = st.checkbox('Leisure', False)
    show_education = st.checkbox('Education', False)
    show_health = st.checkbox('Health', False)
    show_shopping = st.checkbox('Shopping', False)
    
    if show_all:
        filter = [True, True, True, True, True, True]
    else:
        filter = [show_households, show_work, show_leisure, show_education, show_health, show_shopping]
with col2:
    st.write('### *City A*')
    building_layer = make_point_layer(buildings_df)
    get_scatterplot_map('A', building_layer, filter)
with col3:
    st.write('### *City B*')
    get_scatterplot_map('B', building_layer, filter)

st.write('## **How do these activities and building locations compare to the population density?**')
st.write('Zones with the highest population density here are highlighted in pink. Scroll over each to get more info and the corresponding zone ID')
make_density_map('C', building_layer, zones_df)

st.write('## **What does transportation look like in each of the cities?**')
st.write('Select a mode of transportation to dive deeper into the networks located in each city.')
col1, col2 = st.columns([1,3])
with col1:
    st.write('##### Filter your analysis')
    st.write('Filter by city:')
    show_A = st.checkbox('City A', True, 'A')
    show_B = st.checkbox('City B', True, 'B')
    if show_A and show_B:
        view='C'
    elif show_A:
        view='A'
    else:
        view='B'
    
    st.write('Filter by mode:')
    show_car = st.checkbox('Car Network', True)
    show_train = st.checkbox('Train Network', False)
    show_bus = st.checkbox('Bus Network', False)
    layer = [show_car, show_train, show_bus]
with col2:
    get_network_map(view, layer)

st.write('')
st.write('')
st.write("## Where are commuters located?")
st.write('Compare commuter frequency to the modes of transportation available for each of the geographies.')

col1, col2, col3 = st.columns([1,3,3])
with col1:
    st.write('')
    mode = st.radio('Select mode:', ['Car','Train','Bus'])
    if mode == 'Car':
        layer = make_line_layer(car_df, networks['car']['color'])
    elif mode == 'Train':
        layer = make_line_layer(train_df, networks['train']['color'])
    elif mode == 'Bus':
        layer = make_line_layer(bus_df, networks['bus']['color'])
with col2:
    st.write('#### City A')
    make_commuter_map('A', layer, commuter_zones_df)
with col3:
    st.write('#### City B')
    make_commuter_map('B', layer, commuter_zones_df)

population_df.drop(['geometry','hh_index', 'field_1','main_activity_id', 'main_facility_area', 'main_facility_zone','mode', 'p_hh_index'], axis=1, inplace=True)

data_expander = st.expander('View more details with the population survey data', True)
with data_expander:
    st.write('#### *Who lives in our cities?*')
    show_columns = ['area_id', 'zone_id', 
        # 'hh_count', 'hh_children', 'hh_people_in_work', 'hh_in_work', 'hh_income', 'hh_cars',
        'adult', 'gender', 'age', 'employment', 'occupation', 'main_activity', 'hh_income_bin', 'age_bin' 
        ]
    st.write('#### City A')
    st.write(population_df.loc[population_df['city']=='A'][show_columns])
    st.write('#### City B')
    st.write(population_df.loc[population_df['city']=='B'][show_columns])