from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import httpx

from database import engine, get_db
import models, schemas, auth

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advanced Weather API",
    description="A real-time Weather API with JWT Authentication, SQLite Database, and User Favorites.",
    version="2.0.0"
)

@app.get("/")
def home():
    return {"message": "Welcome to the Advanced Weather API. Visit /docs to test."}

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
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = await client.get(weather_url)
        weather_data = weather_response.json()
        
        current_weather = weather_data.get("current_weather", {})
        
        return {
            "city": city_name,
            "country": country,
            "temperature_celsius": current_weather.get("temperature"),
            "windspeed_kmh": current_weather.get("windspeed"),
            "is_day": bool(current_weather.get("is_day")),
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
