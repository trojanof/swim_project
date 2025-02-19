from datetime import datetime
import pytz
import streamlit as st
import folium
from streamlit_folium import folium_static
import geopy.distance
import math
import pandas as pd
from settings import (METERS_SHEET_NAME, LOCATIONS_SHEET_NAME, INTRO_MESSAGE,
                      CLUB_URL, INFO_URL, DEFAULT_START_CAPTION,
                      DEFAULT_FINISH_CAPTION, START_DATE)
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


def calculate_initial_compass_bearing(start: tuple,
                                      end: tuple) -> float:
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


def location_at_dist(start: tuple,
                     end: tuple,
                     distance_travelled,
                     bearing: float | None = None) -> tuple[float, float]:
    '''
    Claculates point location between start and end point along straight
    line on a given distance
    '''
    if not bearing:
        bearing = calculate_initial_compass_bearing(start, end)
    point = geopy.distance.distance(
        kilometers=distance_travelled).destination(
        start,
        bearing=bearing
    )
    current_location = (point.latitude, point.longitude)
    return current_location


def get_points_list_along_path(start_point, finish_point, bearing=None):
    '''
    Creates a list of points with coordinates between
    start and finish points. To be used for polyline drawing
    '''
    route_array = []
    route_array.append(tuple(start_point))
    full_dist = distance_between(start_point, finish_point)
    for i in range(1, 100, 1):
        dist = full_dist * i / 100
        pt = location_at_dist(
            tuple(start_point),
            tuple(finish_point),
            dist,
            bearing
            )
        route_array.append(pt)
    route_array.append(tuple(finish_point))
    return route_array


def draw_marker(coord, caption=''):
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


def prepare_map(start_coord,
                finish_coord,
                start_caption,
                finish_caption,
                dist,
                distance_travelled):
    '''
    Creates a map with start/finish points markers, tarjectory line
    and a highlighted line of travelled distance
    '''
    if 'map' not in st.session_state or st.session_state.map is None:
        half_dist = distance_between(start_coord, finish_coord) / 2
        center_point = location_at_dist(tuple(start_coord),
                                        tuple(finish_coord),
                                        half_dist)

        world_map = folium.Map(
            location=center_point,
            zoom_start=10,
            tiles="OpenStreetMap",
            attributionControl=0
            )

        draw_marker(start_coord, start_caption).add_to(world_map)
        draw_marker(finish_coord, finish_caption).add_to(world_map)

        dist_on_map = distance_between(start_coord, finish_coord) * 1000
        portion_travelled = distance_travelled / dist
        graphical_distance = round(portion_travelled * dist_on_map)
        current_point = location_at_dist(
            tuple(start_coord),
            tuple(finish_coord),
            graphical_distance / 1000
            )
        current_point = tuple(round(i, 3) for i in current_point)
        bearing = calculate_initial_compass_bearing(start=tuple(start_coord),
                                                    end=tuple(finish_coord))
        if 0 <= bearing <= 180:
            icon_image = 'swimmer_right.png'
        else:
            icon_image = 'swimmer_left.png'

        icon = folium.CustomIcon(
            icon_image,
            icon_size=(50, 50)
            )
        remaining_dist = dist - distance_travelled
        folium.Marker(location=current_point,
                      icon=icon,
                      popup=folium.Popup(
                          f'Мы тут! До конца пролива {remaining_dist} м',
                          parse_html=True,
                          max_width=100)).add_to(world_map)

        curr_coords = get_points_list_along_path(start_coord, current_point)
        folium.PolyLine(
            locations=curr_coords,
            color="#FF0000",
            weight=4,
            tooltip=f"Проплыто {distance_travelled} м"
            ).add_to(world_map)

        route_array = get_points_list_along_path(start_coord, finish_coord)
        folium.PolyLine(
            locations=route_array,
            color="#008000",
            weight=2,
            tooltip=f"Траектория заплыва, длина {dist} м",
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

    today = datetime.now()
    tz = pytz.timezone('Asia/Yekaterinburg')
    today = tz.localize(today).date().strftime("%d.%m.%Y")
    st.session_state.map = None

    date_range = pd.date_range(START_DATE, today, freq='d').date
    sel_caption = ("Или вы можете выбрать день из спика ниже и "
                   "посмотреть где мы были в определнную дату")
    day = st.selectbox(
        sel_caption,
        date_range,
        index=len(date_range) - 1,
        )

    day = pd.to_datetime(day, dayfirst=True)
    overall_distance = get_distance_at_day(day)
    df, ind = get_location(overall_distance)
    if ind == df.index.min():
        current_dist = overall_distance
    else:
        current_dist = overall_distance - df.loc[ind-1, 'Cumul_dist'].values[0]

    start_coord = df.loc[ind, 'Start_point'].values[0].split(',')
    finish_coord = df.loc[ind, 'Finish_point'].values[0].split(',')
    start_coord = [float(i) for i in start_coord]
    finish_coord = [float(i) for i in finish_coord]

    dist = int(df.loc[ind, 'Distance'].values[0])

    start_caption = df.loc[ind, 'Start_caption'].values[0]
    finish_caption = df.loc[ind, 'Finish_caption'].values[0]
    if start_caption:
        start_caption = DEFAULT_START_CAPTION + ': ' + start_caption
    else:
        start_caption = DEFAULT_START_CAPTION
    if finish_caption:
        finish_caption = DEFAULT_FINISH_CAPTION + ': ' + finish_caption
    else:
        finish_caption = DEFAULT_FINISH_CAPTION
    description = df.loc[ind, 'Description'].values[0]
    st.write(description)
    map = prepare_map(start_coord,
                      finish_coord,
                      start_caption,
                      finish_caption,
                      dist,
                      distance_travelled=current_dist)
    folium_static(map, width=600)


if __name__ == "__main__":
    main()
