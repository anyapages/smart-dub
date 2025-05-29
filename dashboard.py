# pip install streamlit plotly pandas

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# Sample data for Dublin Bikes stations
sample_bikes_data = [
    {"station_id": 1, "name": "Heuston Station", "lat": 53.3464, "lng": -6.2921, "bikes": 5, "stands": 10, "capacity": 20},
    {"station_id": 2, "name": "Smithfield", "lat": 53.3475, "lng": -6.2785, "bikes": 2, "stands": 8, "capacity": 15},
    {"station_id": 3, "name": "Merrion Square East", "lat": 53.3379, "lng": -6.2537, "bikes": 7, "stands": 5, "capacity": 20},
    {"station_id": 4, "name": "Trinity College", "lat": 53.3439, "lng": -6.2546, "bikes": 12, "stands": 8, "capacity": 25},
    {"station_id": 5, "name": "Dame Street", "lat": 53.3434, "lng": -6.2674, "bikes": 3, "stands": 17, "capacity": 20},
    {"station_id": 6, "name": "IFSC", "lat": 53.3498, "lng": -6.2398, "bikes": 8, "stands": 12, "capacity": 20},
    {"station_id": 7, "name": "Grand Canal Dock", "lat": 53.3391, "lng": -6.2351, "bikes": 15, "stands": 5, "capacity": 25},
    {"station_id": 8, "name": "St. Stephen's Green", "lat": 53.3387, "lng": -6.2613, "bikes": 6, "stands": 14, "capacity": 20},
    {"station_id": 9, "name": "Rathmines", "lat": 53.3250, "lng": -6.2642, "bikes": 4, "stands": 11, "capacity": 15},
    {"station_id": 10, "name": "Parnell Square", "lat": 53.3527, "lng": -6.2648, "bikes": 9, "stands": 11, "capacity": 20},
    {"station_id": 11, "name": "Drumcondra", "lat": 53.3712, "lng": -6.2573, "bikes": 7, "stands": 8, "capacity": 15}
]

# Sample hub recommendations
sample_recommendations = [
    {"lat": 53.3525, "lng": -6.2600, "score": 74.0, "location": "Near Parnell Square"},
    {"lat": 53.3350, "lng": -6.2600, "score": 73.2, "location": "Temple Bar Area"},
    {"lat": 53.3375, "lng": -6.2560, "score": 72.7, "location": "Trinity College Area"},
    {"lat": 53.3400, "lng": -6.2600, "score": 72.2, "location": "Dame Street Corridor"},
    {"lat": 53.3425, "lng": -6.2600, "score": 72.1, "location": "City Centre North"}
]

# Convert to DataFrames
bikes_df = pd.DataFrame(sample_bikes_data)
recommendations_df = pd.DataFrame(sample_recommendations)

def generate_recommendations():
    """Simulate recommendation generation"""
    time.sleep(1)  # Simulate processing time
    return recommendations_df

def create_main_map():
    """Create interactive map visualisation - FIXED colourbar positioning"""
    fig = go.Figure()

    # Add Dublin Bikes stations with FIXED colorbar
    fig.add_trace(go.Scattermapbox(
        lat=bikes_df['lat'],
        lon=bikes_df['lng'],
        mode='markers',
        marker=dict(
            size=bikes_df['capacity'] * 1.5,
            color=bikes_df['bikes']/bikes_df['capacity'],
            colorscale='RdYlGn_r',
            sizemode='diameter',
            sizeref=2,
            colorbar=dict(
                title="Bike Utilisation Rate",
                titleside="right",
                x=1.02,  # Move colorbar to the right
                y=0.8,   # Position it higher up
                len=0.6, # Make it shorter
                thickness=15,  # Make it thinner
                xanchor="left",
                yanchor="top"
            ),
            opacity=0.8
        ),
        text=bikes_df['name'],
        hovertemplate='<b>%{text}</b><br>🚲 Available: %{customdata[0]}<br>📍 Stands: %{customdata[1]}<extra></extra>',
        customdata=bikes_df[['bikes', 'stands']],
        name='Dublin Bikes Stations'
    ))

    # Add recommended hubs
    fig.add_trace(go.Scattermapbox(
        lat=recommendations_df['lat'],
        lon=recommendations_df['lng'],
        mode='markers',
        marker=dict(
            size=recommendations_df['score'] * 0.8,
            color='gold',
            symbol='star',
            sizeref=3,
            opacity=0.9
        ),
        text=recommendations_df['location'],
        hovertemplate='<b>🌟 %{text}</b><br>Score: %{customdata:.1f}/100<extra></extra>',
        customdata=recommendations_df['score'],
        name='Recommended Hubs'
    ))

    # Update layout with proper margins
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center={"lat": 53.3498, "lon": -6.2603},
        mapbox_zoom=12,
        height=600,
        margin={"r":120,"t":40,"l":20,"b":20},  # More right margin for colorbar
        title="Dublin Mobility Hub"
    )

    return fig

def create_score_breakdown():
    """Create horizontal bar chart of scores"""
    fig = px.bar(
        recommendations_df.sort_values('score', ascending=False).head(5),
        x='score',
        y='location',
        orientation='h',
        color='score',
        color_continuous_scale='Viridis',
        title='🏆 Top Locations'
    )
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title='Hub Score (0-100)',
        yaxis_title='Location',
        height=400
    )
    return fig

def main():
    """Main Streamlit app"""
    st.set_page_config(page_title="MobiFlow Hub Optimiser", layout="wide")

    # Sidebar Controls
    st.sidebar.subheader("🎯 Methodology")
    st.sidebar.write("Algorithm considers:")
    st.sidebar.write("• Transport connectivity (35%)")
    st.sidebar.write("• Bike demand patterns (25%)")
    st.sidebar.write("• Infrastructure gaps (20%)")
    st.sidebar.write("• Accessibility factors (20%)")

    min_score = st.sidebar.slider("Minimum Hub Score", 60, 80, 70)
    transport_types = st.sidebar.multiselect(
        "Transport Integration",
        ["Bus", "Luas", "DART", "Cycling"],
        default=["Bus", "Luas"]
    )

    st.title("🚲 MobiFlow")

    # Loading Indicator
    with st.spinner('Calculating optimal hub locations...'):
        recommendations = generate_recommendations()

    # Map Section
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(create_main_map(), use_container_width=True)

    with col2:
        st.plotly_chart(create_score_breakdown(), use_container_width=True)

    # Metrics Section
    st.subheader("📊 Key Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Top Recommended Location", "Parnell Square", "74/100")
    with col2:
        st.metric("Estimated CO₂ Reduction", "156 tonnes/year", "+24% vs baseline")
    with col3:
        st.metric("Projected Users", "45,000/year", "First 12 months")

    # Export Section
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Download Report"):
            st.success("Report generation started! (Demo mode)")
    with col2:
        if st.button("📍 Export Locations"):
            st.success("CSV export started! (Demo mode)")

if __name__ == "__main__":
    main()