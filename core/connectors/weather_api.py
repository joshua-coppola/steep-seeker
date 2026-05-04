from typing import Dict, List, Tuple
from datetime import datetime
import requests
import time

class Weather:
    """Fetches and processes historical weather data for ski season analysis."""
    
    # Class constants
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    WINTER_MONTHS = [11, 12, 1, 2, 3, 4]  # Nov - April
    FREEZE_THRESHOLD_HIGH = 34  # °F
    FREEZE_THRESHOLD_LOW = 32   # °F
    
    def __init__(self, num_seasons: int = 5, timezone: str = "America/New_York"):
        """
        Initialize Weather API client.
        
        Args:
            num_seasons: Number of past seasons to analyze (default: 5)
            timezone: Timezone for the location (default: America/New_York)
        """
        self.num_seasons = num_seasons
        self.timezone = timezone
    
    def _get_date_range(self) -> Tuple[str, str]:
        """Calculate dynamic date range based on current date and num_seasons."""
        end_date = datetime.now()
        
        # If we're past April, use this year's April 30, else use last year's
        if end_date.month > self.WINTER_MONTHS[-1]:
            end_date = datetime(end_date.year, self.WINTER_MONTHS[-1], 30)
        else:
            end_date = datetime(end_date.year - 1, self.WINTER_MONTHS[-1], 30)
        
        # Start date is num_seasons years before, November 1
        start_date = datetime(end_date.year - self.num_seasons, 11, 1)
        
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    
    def get(self, lat: float, lon: float) -> Dict[str, float]:
        """
        Fetch and process historical weather data for a location.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Dictionary with averaged winter weather metrics:
                - icy_days: Average freeze-thaw days per season
                - rain: Average rain total per season (inches)
                - snow: Average snowfall per season (inches)
        """
        start_date, end_date = self._get_date_range()
        
        params = {
            'latitude': lat,
            'longitude': lon,
            'start_date': start_date,
            'end_date': end_date,
            'daily': 'temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum',
            'timezone': self.timezone,
            'temperature_unit': 'fahrenheit',
            'precipitation_unit': 'inch'
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()['daily']
            return self._process_weather(data)
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                if "Daily API request limit exceeded" in response.text:
                    raise ValueError(
                        "Daily API request limit exceeded. Please try again tomorrow."
                    )
                
                print("Rate limited. Waiting 60 seconds before retry...")
                time.sleep(60)
                return self.get(lat, lon)
            else:
                raise ValueError(
                    f"Weather API call failed with code: {response.status_code}\n{response.text}"
                )
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Weather API request failed: {str(e)}")
    
    def _process_weather(self, data: Dict) -> Dict[str, float]:
        """
        Process daily weather data into seasonal averages.
        
        Args:
            data: Dict of daily weather records
            
        Returns:
            Dictionary with averaged metrics
        """
        # Reshape dict to list
        weather_list = []
        for i in range(len(data['time'])):
            row = {key: data[key][i] for key in data.keys()}
            weather_list.append(row)

        # Filter to winter months only and remove incomplete data
        winter_list = self._filter_winter_data(weather_list)
        
        if not winter_list:
            return {'icy_days': 0, 'rain': 0, 'snow': 0}
        
        # Calculate metrics
        freeze_thaw_days = self._count_freeze_thaw_days(winter_list)
        rain_total = sum(row['rain_sum'] for row in winter_list)
        snow_total = sum(row['snowfall_sum'] for row in winter_list)
        
        # Average over seasons
        return {
            'icy_days': round(freeze_thaw_days / self.num_seasons, 2),
            'rain': round(rain_total / self.num_seasons, 2),
            'snow': round(snow_total / self.num_seasons, 2)
        }
    
    def _filter_winter_data(self, weather_list: List[Dict]) -> List[Dict]:
        """
        Filter data to winter months only and remove incomplete records.
        
        Args:
            weather_list: List of daily weather records
            
        Returns:
            Filtered list of winter records
        """
        winter_list = []
        
        for row in weather_list:
            # Parse month from date string (YYYY-MM-DD)
            month = int(row['time'].split('-')[1])
            
            # Only include winter months
            if month not in self.WINTER_MONTHS:
                continue
            
            # Skip rows with any None values
            if any(value is None for value in row.values()):
                continue
            
            winter_list.append(row)
        
        return winter_list
    
    def _count_freeze_thaw_days(self, winter_list: List[Dict]) -> int:
        """
        Count days with freeze-thaw cycles.
        
        A freeze-thaw day has:
        - Max temp above freezing (>34°F)
        - Min temp at/below freezing (≤32°F)
        
        Args:
            winter_list: List of winter weather records
            
        Returns:
            Number of freeze-thaw days
        """
        freeze_thaw = 0
        
        for row in winter_list:
            temp_max = float(row['temperature_2m_max'])
            temp_min = float(row['temperature_2m_min'])
            
            if temp_max > self.FREEZE_THRESHOLD_HIGH and temp_min <= self.FREEZE_THRESHOLD_LOW:
                freeze_thaw += 1
        
        return freeze_thaw
