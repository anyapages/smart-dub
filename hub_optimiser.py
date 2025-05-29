#!/usr/bin/env python3
"""
MobiFlow Hub Optimiser - Data Pipeline
Step 1: Data Collection and Processing for Dublin Mobility Hub Optimisation
Hackathon Implementation - Dublin Tech Week 2025
"""

import requests
import pandas as pd
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import os
from dataclasses import dataclass
import sqlite3
from geopy.distance import geodesic
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MobilityStation:
    """Data class for mobility station information"""
    id: str
    name: str
    latitude: float
    longitude: float
    available_bikes: int
    available_stands: int
    total_capacity: int
    status: str
    last_update: datetime

@dataclass
class BusStop:
    """Data class for bus stop information"""
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    routes: List[str]

class MobilityDataCollector:
    """
    Comprehensive data collector for Dublin mobility ecosystem
    Handles multiple data sources with error handling and caching
    """

    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'MobiFlow-Hackathon/1.0'})
        self.cache_db = self._setup_cache_database()

    def _load_default_config(self) -> Dict:
        """Load default configuration"""
        return {
            'jcdecaux_api_key': os.getenv('JCDECAUX_API_KEY', 'demo_key'),
            'cache_duration': 300,  # 5 minutes
            'request_timeout': 10,
            'max_retries': 3,
            'dublin_bounds': {
                'north': 53.4,
                'south': 53.2,
                'east': -6.1,
                'west': -6.4
            }
        }

    def _setup_cache_database(self) -> sqlite3.Connection:
        """Setup SQLite cache database"""
        conn = sqlite3.connect(':memory:')  # In-memory for hackathon

        # Create tables
        conn.execute('''
                     CREATE TABLE dublin_bikes (
                                                   id INTEGER PRIMARY KEY,
                                                   name TEXT,
                                                   latitude REAL,
                                                   longitude REAL,
                                                   available_bikes INTEGER,
                                                   available_stands INTEGER,
                                                   total_capacity INTEGER,
                                                   status TEXT,
                                                   timestamp DATETIME
                     )
                     ''')

        conn.execute('''
                     CREATE TABLE bus_stops (
                                                stop_id TEXT PRIMARY KEY,
                                                stop_name TEXT,
                                                latitude REAL,
                                                longitude REAL,
                                                routes TEXT,
                                                timestamp DATETIME
                     )
                     ''')

        conn.execute('''
                     CREATE TABLE hub_scores (
                                                 latitude REAL,
                                                 longitude REAL,
                                                 score REAL,
                                                 components TEXT,
                                                 timestamp DATETIME
                     )
                     ''')

        conn.commit()
        return conn

    def get_dublin_bikes_data(self) -> pd.DataFrame:
        """
        Fetch real-time Dublin Bikes data from JCDecaux API
        With fallback to sample data for demo purposes
        """
        logger.info("Fetching Dublin Bikes data...")

        try:
            # Try real API first
            url = f"https://api.jcdecaux.com/vls/v1/stations?contract=dublin&apiKey={self.config['jcdecaux_api_key']}"

            response = self.session.get(url, timeout=self.config['request_timeout'])

            if response.status_code == 200:
                data = response.json()
                df = self._process_dublin_bikes_data(data)
                logger.info(f"Successfully fetched {len(df)} Dublin Bikes stations")
                return df
            else:
                logger.warning(f"API returned status {response.status_code}, using sample data")
                return self._get_sample_dublin_bikes_data()

        except Exception as e:
            logger.error(f"Error fetching Dublin Bikes data: {e}")
            logger.info("Using sample data for demo")
            return self._get_sample_dublin_bikes_data()

    def _process_dublin_bikes_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Process raw Dublin Bikes API data"""
        processed_data = []

        for station in raw_data:
            processed_data.append({
                'station_id': station['number'],
                'name': station['name'],
                'latitude': station['position']['lat'],
                'longitude': station['position']['lng'],
                'available_bikes': station['available_bikes'],
                'available_stands': station['available_bike_stands'],
                'total_capacity': station['bike_stands'],
                'status': station['status'],
                'last_update': datetime.fromtimestamp(station['last_update'] / 1000),
                'banking': station.get('banking', False),
                'bonus': station.get('bonus', False)
            })

        df = pd.DataFrame(processed_data)

        # Calculate derived metrics
        df['utilization_rate'] = df['available_bikes'] / df['total_capacity']
        df['availability_score'] = df['available_bikes'] + df['available_stands']
        df['demand_indicator'] = np.where(df['utilization_rate'] > 0.8, 'High',
                                          np.where(df['utilization_rate'] > 0.5, 'Medium', 'Low'))

        return df

    def _get_sample_dublin_bikes_data(self) -> pd.DataFrame:
        """
        Comprehensive sample data for demo purposes
        Based on real Dublin Bikes station locations
        """
        sample_stations = [
            # City Centre Stations
            {"station_id": 1, "name": "Heuston Station", "lat": 53.3464, "lng": -6.2921, "bikes": 5, "stands": 10, "capacity": 20},
            {"station_id": 2, "name": "Smithfield", "lat": 53.3475, "lng": -6.2785, "bikes": 2, "stands": 8, "capacity": 15},
            {"station_id": 3, "name": "Merrion Square East", "lat": 53.3379, "lng": -6.2537, "bikes": 7, "stands": 5, "capacity": 20},
            {"station_id": 4, "name": "Trinity College", "lat": 53.3439, "lng": -6.2546, "bikes": 12, "stands": 8, "capacity": 25},
            {"station_id": 5, "name": "Dame Street", "lat": 53.3434, "lng": -6.2674, "bikes": 3, "stands": 17, "capacity": 20},

            # Docklands Area
            {"station_id": 6, "name": "IFSC", "lat": 53.3498, "lng": -6.2398, "bikes": 8, "stands": 12, "capacity": 20},
            {"station_id": 7, "name": "Grand Canal Dock", "lat": 53.3391, "lng": -6.2351, "bikes": 15, "stands": 5, "capacity": 25},

            # South Dublin
            {"station_id": 8, "name": "St. Stephen's Green", "lat": 53.3387, "lng": -6.2613, "bikes": 6, "stands": 14, "capacity": 20},
            {"station_id": 9, "name": "Rathmines", "lat": 53.3250, "lng": -6.2642, "bikes": 4, "stands": 11, "capacity": 15},

            # North Dublin
            {"station_id": 10, "name": "Parnell Square", "lat": 53.3527, "lng": -6.2648, "bikes": 9, "stands": 11, "capacity": 20},
            {"station_id": 11, "name": "Drumcondra", "lat": 53.3712, "lng": -6.2573, "bikes": 7, "stands": 8, "capacity": 15}
        ]

        # Convert to DataFrame with realistic variations
        data = []
        current_time = datetime.now()

        for station in sample_stations:
            # Add some realistic variation to bike availability
            hour = current_time.hour
            if 7 <= hour <= 9:  # Morning rush - fewer bikes in residential areas
                bikes_factor = 0.7 if 'Rathmines' in station['name'] or 'Drumcondra' in station['name'] else 1.2
            elif 17 <= hour <= 19:  # Evening rush - fewer bikes in city centre
                bikes_factor = 0.6 if 'Dame' in station['name'] or 'IFSC' in station['name'] else 1.1
            else:
                bikes_factor = 1.0

            adjusted_bikes = max(0, min(station['capacity'], int(station['bikes'] * bikes_factor)))
            adjusted_stands = station['capacity'] - adjusted_bikes

            data.append({
                'station_id': station['station_id'],
                'name': station['name'],
                'latitude': station['lat'],
                'longitude': station['lng'],
                'available_bikes': adjusted_bikes,
                'available_stands': adjusted_stands,
                'total_capacity': station['capacity'],
                'status': 'OPEN' if adjusted_bikes > 0 or adjusted_stands > 0 else 'CLOSED',
                'last_update': current_time,
                'banking': True,
                'bonus': False
            })

        df = pd.DataFrame(data)

        # Calculate derived metrics
        df['utilization_rate'] = df['available_bikes'] / df['total_capacity']
        df['availability_score'] = df['available_bikes'] + df['available_stands']
        df['demand_indicator'] = np.where(df['utilization_rate'] > 0.8, 'High',
                                          np.where(df['utilization_rate'] > 0.5, 'Medium', 'Low'))

        return df

    def get_bus_stops_data(self) -> pd.DataFrame:
        """
        Get Dublin bus stops data
        Using sample data representative of Dublin Bus network
        """
        logger.info("Fetching Dublin bus stops data...")

        # Sample bus stops near key locations
        bus_stops = [
            {"stop_id": "1001", "name": "Heuston Station", "lat": 53.3468, "lng": -6.2928, "routes": ["25", "26", "67", "69"]},
            {"stop_id": "1002", "name": "Smithfield", "lat": 53.3478, "lng": -6.2792, "routes": ["37", "39", "70"]},
            {"stop_id": "1003", "name": "Trinity College", "lat": 53.3442, "lng": -6.2540, "routes": ["7", "8", "15", "46"]},
            {"stop_id": "1004", "name": "Merrion Square", "lat": 53.3382, "lng": -6.2534, "routes": ["7", "8", "10"]},
            {"stop_id": "1005", "name": "Dame Street", "lat": 53.3437, "lng": -6.2671, "routes": ["15", "16", "49", "54"]},
            {"stop_id": "1006", "name": "IFSC", "lat": 53.3501, "lng": -6.2395, "routes": ["90", "92"]},
            {"stop_id": "1007", "name": "Grand Canal Dock", "lat": 53.3394, "lng": -6.2348, "routes": ["1", "47", "56"]},
            {"stop_id": "1008", "name": "St. Stephen's Green", "lat": 53.3390, "lng": -6.2610, "routes": ["11", "14", "15", "20"]},
            {"stop_id": "1009", "name": "Rathmines", "lat": 53.3253, "lng": -6.2639, "routes": ["14", "15", "83"]},
            {"stop_id": "1010", "name": "Parnell Square", "lat": 53.3530, "lng": -6.2645, "routes": ["1", "7", "11", "13"]},
            {"stop_id": "1011", "name": "Drumcondra", "lat": 53.3715, "lng": -6.2570, "routes": ["1", "7", "11"]}
        ]

        data = []
        for stop in bus_stops:
            data.append({
                'stop_id': stop['stop_id'],
                'stop_name': stop['name'],
                'latitude': stop['lat'],
                'longitude': stop['lng'],
                'routes': ','.join(stop['routes']),
                'route_count': len(stop['routes']),
                'major_hub': len(stop['routes']) >= 4
            })

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} bus stops")
        return df

    def get_luas_stations_data(self) -> pd.DataFrame:
        """Get Luas stations data"""
        logger.info("Fetching Luas stations data...")

        luas_stations = [
            # Green Line
            {"name": "St. Stephen's Green", "lat": 53.3387, "lng": -6.2613, "line": "Green"},
            {"name": "Trinity", "lat": 53.3447, "lng": -6.2589, "line": "Green"},
            {"name": "Westmoreland", "lat": 53.3450, "lng": -6.2589, "line": "Green"},
            {"name": "Abbey Street", "lat": 53.3484, "lng": -6.2589, "line": "Green"},

            # Red Line
            {"name": "Heuston", "lat": 53.3467, "lng": -6.2929, "line": "Red"},
            {"name": "Museum", "lat": 53.3474, "lng": -6.2867, "line": "Red"},
            {"name": "Smithfield", "lat": 53.3475, "lng": -6.2785, "line": "Red"},
            {"name": "Four Courts", "lat": 53.3467, "lng": -6.2743, "line": "Red"}
        ]

        data = []
        for station in luas_stations:
            data.append({
                'station_name': station['name'],
                'latitude': station['lat'],
                'longitude': station['lng'],
                'line': station['line'],
                'is_interchange': station['name'] in ['Abbey Street', 'Westmoreland']
            })

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} Luas stations")
        return df

    def calculate_distance_to_transport(self, lat: float, lng: float, transport_df: pd.DataFrame) -> Dict:
        """Calculate distances to nearest transport nodes"""
        min_distance = float('inf')
        nearest_transport = None

        for _, transport in transport_df.iterrows():
            distance = geodesic((lat, lng), (transport['latitude'], transport['longitude'])).meters
            if distance < min_distance:
                min_distance = distance
                nearest_transport = transport

        return {
            'distance_meters': min_distance,
            'nearest_station': nearest_transport['name'] if 'name' in nearest_transport else nearest_transport.get('station_name', 'Unknown'),
            'within_500m': min_distance <= 500,
            'within_200m': min_distance <= 200
        }

class HubScoreCalculator:
    """
    Calculate optimal mobility hub scores based on multiple factors
    """

    def __init__(self, bikes_df: pd.DataFrame, bus_df: pd.DataFrame, luas_df: pd.DataFrame):
        self.bikes_df = bikes_df
        self.bus_df = bus_df
        self.luas_df = luas_df
        self.collector = MobilityDataCollector()

    def calculate_hub_score(self, lat: float, lng: float) -> Dict:
        """
        Calculate comprehensive hub score for a given location
        Score components: Transport connectivity, bike demand, accessibility, population
        """

        # 1. Transport Connectivity Score (35% weight)
        bus_proximity = self.collector.calculate_distance_to_transport(lat, lng, self.bus_df)
        luas_proximity = self.collector.calculate_distance_to_transport(lat, lng, self.luas_df)

        transport_score = 0
        if bus_proximity['within_200m']:
            transport_score += 15
        elif bus_proximity['within_500m']:
            transport_score += 10
        else:
            transport_score += max(0, 10 - (bus_proximity['distance_meters'] - 500) / 100)

        if luas_proximity['within_500m']:
            transport_score += 20
        else:
            transport_score += max(0, 15 - (luas_proximity['distance_meters'] - 500) / 100)

        # 2. Bike Demand Score (25% weight)
        bike_demand = self._calculate_bike_demand(lat, lng)
        demand_score = min(bike_demand / 20 * 25, 25)

        # 3. Infrastructure Gap Score (20% weight)
        gap_score = self._calculate_infrastructure_gap(lat, lng) * 20

        # 4. Accessibility Score (15% weight)
        accessibility_score = self._calculate_accessibility_score(lat, lng) * 15

        # 5. Population Density Score (5% weight) - simplified
        population_score = 5  # Assume city centre areas

        total_score = transport_score + demand_score + gap_score + accessibility_score + population_score

        return {
            'total_score': round(total_score, 2),
            'transport_score': round(transport_score, 2),
            'demand_score': round(demand_score, 2),
            'gap_score': round(gap_score, 2),
            'accessibility_score': round(accessibility_score, 2),
            'population_score': round(population_score, 2),
            'components': {
                'nearest_bus': bus_proximity['nearest_station'],
                'bus_distance': bus_proximity['distance_meters'],
                'nearest_luas': luas_proximity['nearest_station'],
                'luas_distance': luas_proximity['distance_meters'],
                'bike_demand': bike_demand
            }
        }

    def _calculate_bike_demand(self, lat: float, lng: float) -> float:
        """Calculate bike demand based on nearby station utilization"""
        nearby_demand = 0
        station_count = 0

        for _, station in self.bikes_df.iterrows():
            distance = geodesic((lat, lng), (station['latitude'], station['longitude'])).meters
            if distance <= 1000:  # Within 1km
                weight = max(0, 1 - distance / 1000)  # Distance decay
                nearby_demand += station['availability_score'] * weight
                station_count += 1

        return nearby_demand / max(station_count, 1)

    def _calculate_infrastructure_gap(self, lat: float, lng: float) -> float:
        """Calculate infrastructure gap (higher score = bigger gap = more need)"""
        min_bike_distance = float('inf')
        min_bus_distance = float('inf')

        # Find nearest bike station
        for _, station in self.bikes_df.iterrows():
            distance = geodesic((lat, lng), (station['latitude'], station['longitude'])).meters
            min_bike_distance = min(min_bike_distance, distance)

        # Find nearest bus stop
        for _, stop in self.bus_df.iterrows():
            distance = geodesic((lat, lng), (stop['latitude'], stop['longitude'])).meters
            min_bus_distance = min(min_bus_distance, distance)

        # Higher gap = higher score (more need for new hub)
        bike_gap = min(1.0, min_bike_distance / 1000)  # Normalize to 0-1
        bus_gap = min(1.0, min_bus_distance / 500)     # Normalize to 0-1

        return (bike_gap + bus_gap) / 2

    def _calculate_accessibility_score(self, lat: float, lng: float) -> float:
        """Calculate accessibility score (simplified)"""
        # In a full implementation, this would consider:
        # - Wheelchair accessibility of nearby transport
        # - Gradient/topography
        # - Lighting and safety
        # - Proximity to healthcare, schools, etc.

        # For demo, use distance to key amenities
        key_locations = [
            (53.3498, -6.2603),  # City centre
            (53.3446, -6.2691),  # Temple Bar
            (53.3387, -6.2613),  # St. Stephen's Green
        ]

        min_distance_to_amenity = min([
            geodesic((lat, lng), loc).meters for loc in key_locations
        ])

        # Closer to amenities = higher accessibility
        return max(0, 1 - min_distance_to_amenity / 2000)

def generate_hub_recommendations(num_locations: int = 10) -> pd.DataFrame:
    """
    Generate top mobility hub location recommendations
    """
    logger.info("Generating mobility hub recommendations...")

    # Initialize data collector and get data
    collector = MobilityDataCollector()
    bikes_df = collector.get_dublin_bikes_data()
    bus_df = collector.get_bus_stops_data()
    luas_df = collector.get_luas_stations_data()

    # Initialize score calculator
    calculator = HubScoreCalculator(bikes_df, bus_df, luas_df)

    # Define candidate locations (grid search in Dublin area)
    dublin_bounds = {
        'north': 53.37,
        'south': 53.32,
        'east': -6.22,
        'west': -6.30
    }

    # Generate candidate locations
    candidate_locations = []
    lat_step = (dublin_bounds['north'] - dublin_bounds['south']) / 20
    lng_step = (dublin_bounds['east'] - dublin_bounds['west']) / 20

    for i in range(20):
        for j in range(20):
            lat = dublin_bounds['south'] + i * lat_step
            lng = dublin_bounds['west'] + j * lng_step
            candidate_locations.append((lat, lng))

    # Calculate scores for all candidates
    results = []
    for lat, lng in candidate_locations:
        score_data = calculator.calculate_hub_score(lat, lng)
        results.append({
            'latitude': lat,
            'longitude': lng,
            'hub_score': score_data['total_score'],
            'transport_score': score_data['transport_score'],
            'demand_score': score_data['demand_score'],
            'gap_score': score_data['gap_score'],
            'accessibility_score': score_data['accessibility_score'],
            'nearest_bus': score_data['components']['nearest_bus'],
            'nearest_luas': score_data['components']['nearest_luas'],
            'bike_demand': score_data['components']['bike_demand']
        })

    # Convert to DataFrame and get top recommendations
    recommendations_df = pd.DataFrame(results)
    recommendations_df = recommendations_df.sort_values('hub_score', ascending=False).head(num_locations)
    recommendations_df = recommendations_df.reset_index(drop=True)

    logger.info(f"Generated {len(recommendations_df)} hub recommendations")
    return recommendations_df

def main():
    """
    Main function to demonstrate the complete data pipeline
    """
    print("🚀 MobiFlow Hub Optimiser - Data Pipeline")
    print("=" * 50)

    try:
        # Step 1: Initialize data collection
        collector = MobilityDataCollector()

        # Step 2: Fetch all mobility data
        print("\n📊 Fetching mobility data...")
        bikes_df = collector.get_dublin_bikes_data()
        bus_df = collector.get_bus_stops_data()
        luas_df = collector.get_luas_stations_data()

        # Step 3: Display data summary
        print(f"\n✅ Data Summary:")
        print(f"   Dublin Bikes Stations: {len(bikes_df)}")
        print(f"   Bus Stops: {len(bus_df)}")
        print(f"   Luas Stations: {len(luas_df)}")

        # Step 4: Calculate sample hub scores
        calculator = HubScoreCalculator(bikes_df, bus_df, luas_df)

        # Sample locations for scoring
        sample_locations = [
            {"name": "Smithfield Square", "lat": 53.3475, "lng": -6.2785},
            {"name": "Docklands Central", "lat": 53.3495, "lng": -6.2400},
            {"name": "Phoenix Park Gate", "lat": 53.3550, "lng": -6.3000},
            {"name": "Ballsbridge", "lat": 53.3300, "lng": -6.2300},
            {"name": "Rathmines Centre", "lat": 53.3250, "lng": -6.2642}
        ]

        print(f"\n🎯 Sample Hub Scores:")
        for location in sample_locations:
            score_data = calculator.calculate_hub_score(location['lat'], location['lng'])
            print(f"   {location['name']}: {score_data['total_score']:.1f}/100")

        # Step 5: Generate full recommendations
        print(f"\n🏆 Generating top recommendations...")
        recommendations = generate_hub_recommendations(5)

        print(f"\n📍 Top 5 Recommended Hub Locations:")
        for idx, row in recommendations.iterrows():
            print(f"   {idx+1}. Score: {row['hub_score']:.1f} | "
                  f"Lat: {row['latitude']:.4f}, Lng: {row['longitude']:.4f} | "
                  f"Near: {row['nearest_bus']}")

        print(f"\n✨ Data pipeline completed successfully!")
        return recommendations, bikes_df, bus_df, luas_df

    except Exception as e:
        logger.error(f"Error in main pipeline: {e}")
        raise

if __name__ == "__main__":
    # Run the complete data pipeline
    recommendations, bikes_data, bus_data, luas_data = main()

    # Export data for next steps
    print(f"\n💾 Exporting data for visualization step...")
    recommendations.to_csv('mobility_hub_recommendations.csv', index=False)
    bikes_data.to_csv('dublin_bikes_data.csv', index=False)
    bus_data.to_csv('dublin_bus_stops.csv', index=False)
    luas_data.to_csv('dublin_luas_stations.csv', index=False)

    print(f"🎉 Step 1 Complete! Ready for visualisation and optimisation steps.")
