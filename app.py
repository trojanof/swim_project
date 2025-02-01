import streamlit as st
import folium
from streamlit_folium import folium_static
import geopy.distance
import math
import pandas as pd
from datetime import datetime
from settings import METERS_SHEET_NAME, LOCATIONS_SHEET_NAME, INTRO_MESSAGE, \
    CLUB_URL, INFO_URL
from parse_sheets import get_df_from_google_sheet

APP_TITLE = ("Виртуальные заплывы клуба [SwimOcean](%s)" % CLUB_URL)


def get_distance_at_day(day):
    '''
    Get distance value from table on requested day
    Distance in meters
    '''
    df = get_df_from_google_sheet(METERS_SHEET_NAME)
    df['Cumulative_sum'] = df['Cumulative_sum'].ffill()
    df['Cumulative_sum'] = df['Cumulative_sum'].astype(int)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    dist = df[df['Date'] == day]['Cumulative_sum'].values[0]
    return dist


def get_location(dist):
    '''
    Get location table and an index corresponding to the
    next destination location, i.e. returns df, ind, such that
    df[ind] is a row describing next destination
    '''
    df = get_df_from_google_sheet(LOCATIONS_SHEET_NAME)
    df['Cumul_dist'] = df['Cumul_dist'].astype(int)
    next_df = df[df['Cumul_dist'] > dist]
    ind = next_df[next_df['Cumul_dist'] == next_df['Cumul_dist'].min()].index
    return df, ind


def calculate_initial_compass_bearing(start, end):
    '''
    Calculates compass bearing (angle) fro start to end point
    '''
    if not isinstance(start, tuple) or not isinstance(end, tuple):
        raise TypeError("Only tuples are supported as arguments")
    lat1 = math.radians(start[0])
    lat2 = math.radians(end[0])
    diffLong = math.radians(end[1] - start[1])
    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
            math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))
    initial_bearing = math.atan2(x, y)
    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing


def distance_between(start, end):
    return geopy.distance.distance(start, end).km


def location_at_dist(start,
                     end,
                     distance_travelled) -> tuple[float, float]:
    '''
    Claculates point location between start and end point along straight
    line on a given distance
    '''
    bearing = calculate_initial_compass_bearing(start, end)
    point = geopy.distance.distance(
        kilometers=distance_travelled).destination(
        start,
        bearing=bearing
    )
    current_location = (point.latitude, point.longitude)
    return current_location


def get_points_list_along_path(start_point, finish_point):
    '''
    Creates a list of points with coordinates between
    start and finish points. To be used for polyline drawing
    '''
    route_array = []
    route_array.append(tuple(start_point))
    full_dist = distance_between(start_point, finish_point)
    for i in range(10, 100, 10):
        dist = full_dist * i / 100
        pt = location_at_dist(
            tuple(start_point),
            tuple(finish_point),
            dist
            )
        route_array.append(pt)
    route_array.append(tuple(finish_point))
    return route_array


def draw_marker(coord, caption):
    '''
    Creates a marker with caption. To be added to the map
    '''
    marker = folium.CircleMarker(
        location=coord,
        radius=7,
        fill=True,
        popup=folium.Popup(caption),
        color='red'
        )
    return marker


def draw_map(start_coord,
             finish_coord,
             start_caption,
             finish_caption,
             distance_travelled,
             remaining_dist):
    '''
    Creates a map with start/finish points markers, tarjectory line
    and a highlighted line of travelled distance
    '''
    if 'map' not in st.session_state or st.session_state.map is None:
        world_map = folium.Map(
            location=start_coord,
            zoom_start=10,
            tiles="OpenStreetMap",
            attributionControl=0
            )

        draw_marker(start_coord, start_caption).add_to(world_map)
        draw_marker(finish_coord, finish_caption).add_to(world_map)

        current_point = location_at_dist(
            tuple(start_coord),
            tuple(finish_coord),
            distance_travelled / 1000
            )

        icon_image = 'swimmer.png'
        icon = folium.CustomIcon(
            icon_image,
            icon_size=(50, 50)
            )

        folium.Marker(
            location=current_point,
            icon=icon,
            popup=folium.Popup(
                f'Мы тут! До конца пролива {remaining_dist} м',
                parse_html=True,
                max_width=100)
            ).add_to(world_map)

        curr_coords = [start_coord, current_point]

        folium.PolyLine(
            locations=curr_coords,
            color="#FF0000",
            weight=4,
            tooltip=f"Проплыто {distance_travelled} м"
            ).add_to(world_map)

        route_array = get_points_list_along_path(start_coord, finish_coord)

        length = distance_travelled + remaining_dist
        folium.PolyLine(
            locations=route_array,
            color="#008000",
            weight=2,
            tooltip=f"Траектория заплыва, длина {length} м",
            dash_array='5',
            opacity=0.3
            ).add_to(world_map)

        st.session_state.map = world_map
    return st.session_state.map


def main():
    st.title(APP_TITLE)
    st.write(INTRO_MESSAGE)
    st.markdown("Сейчас мы выбрали плыть [7 проливов](%s)" % INFO_URL)
    st.markdown("*Посмотрите где мы находимся :blue-background[сегодня]:*")

    today = datetime.now().date().strftime("%d.%m.%Y")
    today = pd.to_datetime(today, dayfirst=True)
    st.session_state.map = None
    overall_distance = get_distance_at_day(today)
    df, ind = get_location(overall_distance)
    current_distance = overall_distance - df.loc[ind-1, 'Cumul_dist'].values[0]
    remaining_dist = df.loc[ind, 'Cumul_dist'].values[0] - overall_distance
    start_coord = df.loc[ind, 'Start_point'].values[0].split(',')
    finish_coord = df.loc[ind, 'Finish_point'].values[0].split(',')
    start_coord = [float(i) for i in start_coord]
    finish_coord = [float(i) for i in finish_coord]
    start_caption = df.loc[ind, 'Start_caption'].values[0]
    finish_caption = df.loc[ind, 'Finish_caption'].values[0]
    description = df.loc[ind, 'Description'].values[0]
    st.write(description)
    m = draw_map(start_coord,
                 finish_coord,
                 start_caption,
                 finish_caption,
                 distance_travelled=current_distance,
                 remaining_dist=remaining_dist)
    folium_static(m, width=600)


if __name__ == "__main__":
    main()
