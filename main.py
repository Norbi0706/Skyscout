import os
from fastapi import FastAPI, HTTPException
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SkyScout API")

amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID"),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
)

@app.get("/")
def read_root():
    return {"message": "SkyScout Engine is running!"}

@app.get("/search-flights")
def search_flights(origin: str, destination: str, departure_date: str):
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=1,
            max=5
        )
        results = []
        for offer in response.data:
            price = offer['price']['total']
            currency = offer['price']['currency']
            airline = offer['itineraries'][0]['segments'][0]['carrierCode']
            results.append({
                "price": f"{price} {currency}",
                "airline": airline,
                "numberOfBookableSeats": offer['numberOfBookableSeats']
            })
        return {"status": "success", "data": results}
    except ResponseError as error:
        raise HTTPException(status_code=400, detail=str(error))
