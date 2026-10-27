from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import httpx

from database import engine, get_db
import models, schemas, auth

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advanced Weather API",
    description="A real-time Weather API with JWT Authentication, MySQL Database, 24-Hour Forecast & Predictions.",
    version="2.2.0"
)

def get_weather_condition(code: int, is_day: bool = True):
    if code == 0:
        return "Clear Sky", ("sunny" if is_day else "night")
    elif code in [1, 2]:
        return "Partly Cloudy", ("cloudy" if is_day else "night")
    elif code == 3:
        return "Overcast", "cloudy"
    elif code in [45, 48]:
        return "Foggy", "cloudy"
    elif code in [51, 53, 55, 56, 57]:
        return "Drizzle", "rainy"
    elif code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return "Rain", "rainy"
    elif code in [71, 73, 75, 77, 85, 86]:
        return "Snow", "snow"
    elif code in [95, 96, 99]:
        return "Thunderstorm", "thunder"
    return "Moderate", ("sunny" if is_day else "night")

def generate_prediction(hourly_items: list):
    if not hourly_items:
        return {
            "peak_temp": None,
            "low_temp": None,
            "rain_expected": False,
            "rain_summary": "No data available",
            "advisory": "Weather conditions are stable."
        }
    
    valid_items = [item for item in hourly_items if item["temperature"] is not None]
    if not valid_items:
        return {
            "peak_temp": None,
            "low_temp": None,
            "rain_expected": False,
            "rain_summary": "No temperature data available",
            "advisory": "Weather conditions are stable."
        }

    peak_item = max(valid_items, key=lambda x: x["temperature"])
    low_item = min(valid_items, key=lambda x: x["temperature"])
    
    rain_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    rain_items = [item for item in hourly_items if item["weather_code"] in rain_codes]
    rain_expected = len(rain_items) > 0
    
    if rain_expected:
        first_rain = rain_items[0]["time"]
        rain_summary = f"Precipitation expected around {first_rain}."
        advisory_rain = "Rain showers predicted in upcoming hours. Carrying an umbrella is advised."
    else:
        rain_summary = "Zero precipitation expected in the next 24 hours."
        advisory_rain = "Dry and clear weather expected ahead."
        
    if peak_item["temperature"] >= 34:
        advisory_temp = f"High heat warning: Temperatures will peak at {peak_item['temperature']}°C around {peak_item['time']}."
    elif low_item["temperature"] <= 12:
        advisory_temp = f"Chilly conditions: Low of {low_item['temperature']}°C expected around {low_item['time']}."
    else:
        advisory_temp = f"Temperatures will fluctuate smoothly between {low_item['temperature']}°C and {peak_item['temperature']}°C."
        
    return {
        "peak_temp": {"temperature": peak_item["temperature"], "time": peak_item["time"]},
        "low_temp": {"temperature": low_item["temperature"], "time": low_item["time"]},
        "rain_expected": rain_expected,
        "rain_summary": rain_summary,
        "advisory": f"{advisory_rain} {advisory_temp}"
    }

async def fetch_weather_bundle(city: str):
    geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    async with httpx.AsyncClient() as client:
        geo_response = await client.get(geocode_url)
        geo_data = geo_response.json()
        
        if not geo_data.get("results"):
            raise HTTPException(status_code=404, detail=f"City '{city}' not found.")
            
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        city_name = location["name"]
        country = location.get("country", "Unknown")
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,weathercode,relative_humidity_2m,windspeed_10m,surface_pressure,cloudcover,apparent_temperature&forecast_days=2&timezone=auto"
        weather_response = await client.get(weather_url)
        weather_data = weather_response.json()
        
        current_weather = weather_data.get("current_weather", {})
        current_code = current_weather.get("weathercode", 0)
        is_day = bool(current_weather.get("is_day", 1))
        condition_text, theme_type = get_weather_condition(current_code, is_day)
        
        hourly_raw = weather_data.get("hourly", {})
        times = hourly_raw.get("time", [])
        temps = hourly_raw.get("temperature_2m", [])
        codes = hourly_raw.get("weathercode", [])
        humidities = hourly_raw.get("relative_humidity_2m", [])
        winds = hourly_raw.get("windspeed_10m", [])
        apparent_temps = hourly_raw.get("apparent_temperature", [])
        pressures = hourly_raw.get("surface_pressure", [])
        clouds = hourly_raw.get("cloudcover", [])
        
        current_time_str = current_weather.get("time", "")
        start_idx = 0
        for idx, t in enumerate(times):
            if current_time_str and t.startswith(current_time_str[:13]):
                start_idx = idx
                break
                
        next_24_hours = []
        end_idx = min(start_idx + 24, len(times))
        for i in range(start_idx, end_idx):
            raw_time = times[i]
            display_time = raw_time.split("T")[1] if "T" in raw_time else raw_time
            h_code = codes[i] if i < len(codes) else 0
            h_cond, h_theme = get_weather_condition(h_code, True)
            next_24_hours.append({
                "time": display_time,
                "full_time": raw_time,
                "temperature": temps[i] if i < len(temps) else None,
                "weather_code": h_code,
                "condition": h_cond,
                "theme_type": h_theme,
                "humidity": humidities[i] if i < len(humidities) else None,
                "windspeed": winds[i] if i < len(winds) else None
            })
            
        prediction_data = generate_prediction(next_24_hours)
        
        feels_like = apparent_temps[start_idx] if start_idx < len(apparent_temps) else current_weather.get("temperature")
        humidity = humidities[start_idx] if start_idx < len(humidities) else 50
        pressure = pressures[start_idx] if start_idx < len(pressures) else 1013
        cloud_cover = clouds[start_idx] if start_idx < len(clouds) else 0
        wind_direction = current_weather.get("winddirection", 0)
        
        curr_temp = current_weather.get("temperature", 20)
        if curr_temp < 15:
            clothing_advice = "Heavy jacket or sweater recommended."
        elif curr_temp < 23:
            clothing_advice = "Light cardigan or hoodie is ideal."
        elif curr_temp > 30:
            clothing_advice = "Light cotton wear & sunglasses recommended."
        else:
            clothing_advice = "Comfortable everyday attire."
            
        if prediction_data["rain_expected"]:
            outdoor_advice = "Outdoor workouts discouraged due to predicted precipitation."
        elif current_weather.get("windspeed", 0) > 25:
            outdoor_advice = "Breezy conditions, exercise caution with outdoor sports."
        else:
            outdoor_advice = "Ideal atmospheric conditions for outdoor activities."
            
        metrics_data = {
            "feels_like": feels_like,
            "humidity": humidity,
            "pressure": pressure,
            "cloud_cover": cloud_cover,
            "wind_direction": wind_direction,
            "clothing_advice": clothing_advice,
            "outdoor_advice": outdoor_advice
        }
        
        return {
            "city": city_name,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "temperature_celsius": current_weather.get("temperature"),
            "windspeed_kmh": current_weather.get("windspeed"),
            "is_day": is_day,
            "weather_code": current_code,
            "condition": condition_text,
            "theme_type": theme_type,
            "metrics": metrics_data,
            "hourly_forecast": next_24_hours,
            "prediction": prediction_data
        }

@app.get("/", response_class=HTMLResponse)
def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/weather/{city}")
async def get_weather(city: str, current_user: models.User = Depends(auth.get_current_user)):
    data = await fetch_weather_bundle(city)
    data["requested_by"] = current_user.username
    return data

@app.get("/weather/{city}/forecast")
async def get_weather_forecast(city: str, current_user: models.User = Depends(auth.get_current_user)):
    data = await fetch_weather_bundle(city)
    return {
        "city": data["city"],
        "country": data["country"],
        "hourly_forecast": data["hourly_forecast"],
        "prediction": data["prediction"],
        "metrics": data["metrics"],
        "requested_by": current_user.username
    }

@app.post("/favorites", response_model=schemas.FavoriteCityResponse)
def add_favorite(favorite: schemas.FavoriteCityCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    new_favorite = models.FavoriteCity(user_id=current_user.id, city_name=favorite.city_name)
    db.add(new_favorite)
    db.commit()
    db.refresh(new_favorite)
    return new_favorite

@app.get("/favorites")
def get_favorites(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    favorites = db.query(models.FavoriteCity).filter(models.FavoriteCity.user_id == current_user.id).all()
    return [{"id": f.id, "city_name": f.city_name} for f in favorites]
