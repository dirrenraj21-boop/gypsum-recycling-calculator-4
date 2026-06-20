import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import requests
import json
import os
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

st.set_page_config(page_title="Gypsum Recycling Dashboard", layout="wide")

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

settings = load_settings()

if "pot_weight" not in settings:
    settings["pot_weight"] = 70.0

st.markdown("""
<style>
.stApp {
    background-color: #FFFFFF;
    color: #064d2f;
}

[data-testid="stSidebar"] {
    background-color: #4A5D23;
}

[data-testid="stSidebar"] * {
    color: white;
}

[data-testid="stSidebar"] input {
    background-color: white !important;
    color: black !important;
}

[data-testid="stNumberInput"] input {
    background-color: white !important;
    color: black !important;
}

h1, h2, h3 {
    color: #064d2f
}

div[data-testid="metric-container"] {
    background: #F5F5DC;
    border-radius: 18px;
    padding: 18px;
    border-left: 8px solid #6B8E23;
    box-shadow: 0 4px 15px rgba(0,0,0,0.12);
}

.intro-box {
    background: linear-gradient(135deg, #f4fff7, #e8f7ef);
    padding: 30px;
    border-radius: 20px;
    border: 1px solid #b7dfc4;
    text-align: center;
    margin-bottom: 30px;
}

.intro-title {
    font-size: 36px;
    font-weight: 800;
    color: #064d2f;
}

.intro-subtitle {
    font-size: 20px;
    font-style: italic;
    color: #0b6b45;
    margin-bottom: 20px;
}

.intro-text {
    font-size: 17px;
    color: #064d2f;
    max-width: 900px;
    margin: auto;
    line-height: 1.6;
}

.goal-box {
    background-color: #ffffff;
    border-left: 6px solid #2e8b57;
    padding: 15px;
    border-radius: 12px;
    margin: 25px auto;
    max-width: 850px;
    font-size: 16px;
    color: #064d2f;
}

.flow-container {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-top: 30px;
    flex-wrap: wrap;
}

.flow-card {
    flex: 1;
    min-width: 150px;
    background: white;
    border-radius: 16px;
    padding: 18px 12px;
    border: 1px solid #d8eadf;
    box-shadow: 0 3px 8px rgba(0,0,0,0.06);
}

.flow-number {
    background-color: #0b6b45;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    margin: auto;
    font-weight: bold;
    line-height: 28px;
}

.flow-icon {
    font-size: 36px;
    margin: 12px 0;
}

.flow-title {
    font-weight: 700;
    color: #064d2f;
    font-size: 15px;
}

.flow-desc {
    font-size: 13px;
    color: #333;
    margin-top: 8px;
}

.footer-line {
    margin-top: 30px;
    background-color: #e9f8ed;
    padding: 14px;
    border-radius: 12px;
    color: #064d2f;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="
background:#f4fff7;
padding:30px;
border-radius:20px;
text-align:center;
margin-bottom:30px;
">

<h1 style="color:#064d2f;">
♻️ Dental Gypsum Recycling Dashboard
</h1>

<h3 style="color:#0b6b45;">
Transforming Dental Waste into Sustainable Value
</h3>

<p style="
font-size:18px;
color:#064d2f;
max-width:850px;
margin:auto;
">

This app helps users plan gypsum waste collection from dental clinics.

It calculates:

✔️ Most efficient collection route

✔️ Fuel and transport cost

✔️ Revenue and profit

✔️ Carbon emission reduction

✔️ Sustainability impact

</p>

<h3 style="color:#064d2f;">
How It Works
</h3>

<p style="font-size:18px;color:#064d2f;">

🦷 Dental Gypsum Waste

⬇️

🚚 Collection from Clinics

⬇️

🗺️ Route Optimisation

⬇️

♻️ Recycling Process

⬇️

🏺 Recycled Products

⬇️

🌱 Carbon Reduction

</p>

</div>

""", unsafe_allow_html=True)


with st.sidebar:
    st.header("Input Parameters")

    processing_cost_perkg = st.number_input(
        "Processing cost (RM/kg)",
        min_value=0.0,
        value=10.0,
        step=0.5
    )

    pot_weight = st.number_input(
        "Pot weight (g)",
        min_value=1.0,
        value=float(settings["pot_weight"]),
        step=1.0
    )

    settings["pot_weight"] = pot_weight
    save_settings(settings)

    selling_price = st.number_input(
        "Selling price per pot (RM)",
        min_value=0.0,
        value=5.0,
        step=0.5
    )

    st.header("Transport Parameters")

    fuel_price = st.number_input(
        "Fuel Price (RM/L)",
        min_value=0.0,
        value=2.05,
        step=0.01
    )

    fuel_efficiency = st.number_input(
        "Vehicle Fuel Efficiency (km/L)",
        min_value=1.0,
        value=12.0,
        step=0.5
    )

    st.header("Carbon Emission Parameters")

    virgin_carbon_factor = st.number_input(
        "Virgin Gypsum Carbon Factor (kg CO₂e/kg)",
        min_value=0.0,
        value=0.30,
        step=0.01
    )

    reduction_percent = (
        st.number_input(
            "CO₂ Reduction Compared With Virgin Gypsum (%)",
            min_value=0,
            max_value=100,
            value=45
        ) / 100
    )

yield_rate = 0.8791

def get_osrm_table(points):
    coords = ";".join(f"{p['longitude']},{p['latitude']}" for p in points)

    url = (
        f"https://router.project-osrm.org/table/v1/driving/{coords}"
        "?annotations=distance,duration"
    )

    response = requests.get(url, timeout=20)
    data = response.json()

    if response.status_code == 200 and data.get("code") == "Ok":
        return data["distances"], data["durations"]

    return None, None

def solve_tsp(distance_matrix):
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return [], 0

    index = routing.Start(0)
    route = []
    total_distance = 0

    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)

    route.append(0)
    return route, total_distance

st.subheader("🏥 Clinic Collection Planner")

clinic_data = pd.DataFrame({
    "Include": [True, True, True, False, False, False, False, False, False, False],
    "Clinic": [
        "Klinik Pergigian Indera Mahkota",
        "Klinik Pergigian Bandar Kuantan",
        "UIA School of Dentistry",
        "Klinik Pergigian Beserah",
        "Klinik Pergigian Jaya Gading",
        "Klinik Pergigian Gambut",
        "Klinik Pergigian Kurnia",
        "Klinik Pergigian Balok",
        "Klinik Pergigian Gambang",
        "Klinik Pergigian Pekan"
    ],
    "latitude": [
        3.8160, 3.8077, 3.8155, 3.8147, 3.7865,
        3.8335, 3.8228, 3.9490, 3.7240, 3.4890
    ],
    "longitude": [
        103.2960, 103.3260, 103.3000, 103.3640, 103.2540,
        103.3170, 103.3310, 103.3730, 103.0830, 103.3890
    ],
    "Gypsum Available (kg)": [
        5.0, 4.0, 6.0, 3.0, 2.0,
        4.0, 3.0, 5.0, 4.0, 5.0
    ]
})

clinic_data = st.data_editor(
    clinic_data,
    column_config={
        "Include": st.column_config.CheckboxColumn("Include in route"),
        "Gypsum Available (kg)": st.column_config.NumberColumn(
            "Gypsum Available (kg)",
            min_value=0.0,
            step=0.5
        )
    },
    hide_index=True,
    use_container_width=True
)

selected_clinics = clinic_data[clinic_data["Include"] == True].copy()

start_point = {
    "Clinic": "Regent International School",
    "latitude": 3.8246,
    "longitude": 103.3280,
    "Gypsum Available (kg)": 0.0
}

route_coordinates = []
route_order = []
distance_km = 0
duration_min = 0
fuel_used = 0
transport_cost = 0

if len(selected_clinics) > 0:
    points = [start_point] + selected_clinics.to_dict("records")

    distance_matrix, duration_matrix = get_osrm_table(points)

    if distance_matrix:
        route_indices, total_meters = solve_tsp(distance_matrix)

        route_order = [points[i]["Clinic"] for i in route_indices]

        distance_km = total_meters / 1000
        fuel_used = distance_km / fuel_efficiency
        transport_cost = fuel_used * fuel_price

        duration_seconds = 0

        for i in range(len(route_indices) - 1):
            duration_seconds += duration_matrix[route_indices[i]][route_indices[i + 1]]

        ordered_points = [points[i] for i in route_indices]

        route_coords = ";".join(
            f"{p['longitude']},{p['latitude']}"
            for p in ordered_points
        )

        route_url = (
            f"https://router.project-osrm.org/route/v1/driving/{route_coords}"
            "?overview=full&geometries=geojson"
        )

        try:
            route_response = requests.get(route_url, timeout=20)
            route_data = route_response.json()

            if route_response.status_code == 200 and route_data.get("code") == "Ok":
                route_coordinates = [
                    [lat, lon]
                    for lon, lat in route_data["routes"][0]["geometry"]["coordinates"]
                ]

        except Exception as e:
            st.warning(f"OSRM route drawing error: {e}")

        duration_min = duration_seconds / 60

    else:
        st.error("OSRM could not calculate the distance matrix. Try again later.")

selected_route_df = selected_clinics.copy()

gypsum_kg = selected_route_df["Gypsum Available (kg)"].sum()
recovered_gypsum = gypsum_kg * yield_rate
pots = (recovered_gypsum * 1000) / pot_weight if pot_weight > 0 else 0
processing_cost = gypsum_kg * processing_cost_perkg
revenue = pots * selling_price
carbon_saved = recovered_gypsum * virgin_carbon_factor * reduction_percent
profit = revenue - processing_cost - transport_cost

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("♻️ Gypsum Collected", f"{gypsum_kg:.2f} kg")
col2.metric("♻️ Recovered Powder", f"{recovered_gypsum:.2f} kg")
col3.metric("🏺 Pots Produced", f"{pots:.0f}")
col4.metric("💰 Revenue", f"RM {revenue:.2f}")
col5.metric("📈 Profit", f"RM {profit:.2f}")
col6.metric("🌱 CO₂ Reduction", f"{carbon_saved:.2f} kg CO₂e")

st.caption("No Google API used. Route is optimised using free OSRM road distances and OR-Tools.")

st.divider()

colA, colB, colC, colD = st.columns(4)

colA.metric("🚚 Optimised Distance", f"{distance_km:.2f} km")
colB.metric("⛽ Fuel Used", f"{fuel_used:.2f} L")
colC.metric("⏱️ Driving Time", f"{duration_min:.0f} min")
colD.metric("💸 Transport Cost", f"RM {transport_cost:.2f}")

st.divider()

if profit > 0:
    st.success("✅ This optimised route is financially viable.")
else:
    st.error("❌ This optimised route is not financially viable.")

if route_order:
    st.subheader("🚚 Most Optimal Route Order")
    for i, stop in enumerate(route_order, start=1):
        st.write(f"{i}. {stop}")

st.divider()
st.subheader("📊 Cost Breakdown")

chart_data = pd.DataFrame({
    "Category": ["Revenue", "Processing Cost", "Transport Cost", "Profit"],
    "RM": [revenue, processing_cost, transport_cost, profit]
})

fig = px.bar(
    chart_data,
    x="Category",
    y="RM",
    text="RM",
    title="Cost and Revenue Breakdown"
)

fig.update_traces(texttemplate="RM %{y:.2f}", textposition="outside")
fig.update_layout(xaxis_title="", yaxis_title="RM", showlegend=False)

st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🗺️ Optimised Collection Map")

m = folium.Map(location=[3.812, 103.307], zoom_start=11, tiles="CartoDB positron")

folium.Marker(
    location=[start_point["latitude"], start_point["longitude"]],
    popup="<b>Regent International School</b><br>Start/End Point",
    tooltip="Regent International School",
    icon=folium.Icon(color="blue", icon="home", prefix="fa")
).add_to(m)

for _, row in selected_clinics.iterrows():
    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        popup=f"""
        <b>{row['Clinic']}</b><br>
        Gypsum available: {row['Gypsum Available (kg)']} kg
        """,
        tooltip=row["Clinic"],
        icon=folium.Icon(color="green", icon="leaf", prefix="fa")
    ).add_to(m)

if route_coordinates:
    folium.PolyLine(
        route_coordinates,
        color="blue",
        weight=5,
        opacity=0.8
    ).add_to(m)

st_folium(m, width=1000, height=500)
