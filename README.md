# 🌤️ Advanced Weather API (Secured Backend)

A production-ready, highly scalable RESTful API built with **FastAPI** and **Python**. This project provides real-time weather data by integrating with the Open-Meteo API, while offering robust user authentication and database management.

## 🚀 Key Features
- **User Authentication (JWT):** Secure user registration and login using JSON Web Tokens (OAuth2 Password Flow) and Bcrypt password hashing.
- **Secured Endpoints:** Weather data and user preferences are protected and only accessible to authenticated users.
- **Real-Time Weather & Geocoding:** Automatically converts any global city name to precise latitude/longitude coordinates and fetches live weather data (temperature, windspeed, day/night status).
- **Favorites System:** Users can save their favorite cities to a persistent SQLite database, establishing a seamless relation between the User and their data.
- **Asynchronous Execution:** Utilizes `async/await` and `httpx` for non-blocking, lightning-fast external API calls.
- **Interactive Documentation:** Auto-generated Swagger UI (`/docs`) for easy frontend integration and testing.

## 🛠️ Tech Stack
- **Framework:** FastAPI
- **Language:** Python 3
- **Database:** SQLite & SQLAlchemy (ORM)
- **Security & Auth:** JWT (`python-jose`), Password Hashing (`passlib`, `bcrypt`)
- **HTTP Client:** `httpx` (Asynchronous requests)
- **Server:** Uvicorn (ASGI)

## ⚙️ How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd weather-api
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows:
   .\venv\Scripts\activate
   
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Test the API:**
   Open your browser and navigate to the interactive Swagger UI:
   👉 **`http://127.0.0.1:8000/docs`**

## 🧪 Testing Flow
1. Go to `/register` to create a new user.
2. Click the green **Authorize** button at the top of Swagger UI to log in and receive your JWT token.
3. Access `/weather/{city}` to fetch real-time data securely.
4. Save cities to your profile using `POST /favorites` and view them using `GET /favorites`.

